"""Visual consistency checker: detects inconsistentwidget styling and sizing.

Compares sibling widgets of the same type and flags deviations in dimensions,
fonts, colours, padding, and border styles. All checks operate on the
serialised widget-tree metadata.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from customtkinter_validator.core.config import ValidatorConfig


@dataclass(frozen=True)
class ConsistencyIssue:
    """A detected visual consistency violation.

    Attributes:
        rule_id: Machine-readable rule identifier.
        severity: ``"critical"``, ``"high"``, ``"medium"``, or ``"low"``.
        widget_id: Primary widget involved.
        related_widget_id: Secondary widget involved (if any).
        description: Human-readable explanation.
        recommended_fix: Suggested resolution.
        measured_value: The measured metric value.
        threshold: The threshold that was violated.
    """

    rule_id: str
    severity: str
    widget_id: str
    related_widget_id: str | None
    description: str
    recommended_fix: str
    measured_value: float | None = None
    threshold: float | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "widget_id": self.widget_id,
            "description": self.description,
            "recommended_fix": self.recommended_fix,
        }
        if self.related_widget_id is not None:
            result["related_widget_id"] = self.related_widget_id
        if self.measured_value is not None:
            result["measured_value"] = self.measured_value
        if self.threshold is not None:
            result["threshold"] = self.threshold
        return result


_BUTTON_TYPES: set[str] = {"CTkButton", "TButton", "Button"}
_ENTRY_TYPES: set[str] = {
    "CTkEntry", "CTkTextbox", "CTkComboBox",
    "TEntry", "TTextbox", "TComboBox",
    "Entry", "Text", "Combobox", "Spinbox",
}
_CONTAINER_TYPES: set[str] = {
    "CTk", "CTkToplevel", "CTkFrame", "CTkScrollableFrame", "CTkTabview",
    "TFrame", "Frame", "LabelFrame", "Toplevel", "Tk",
}


class ConsistencyChecker:
    """Checks visual consistency among sibling widgets of the same type.

    Detects:
    - Inconsistent button sizes
    - Inconsistent entry widths
    - Inconsistent font usage
    - Inconsistent padding within a container
    - Inconsistent corner radius / border styles
    - Mixed layout managers among siblings
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        self._config = config or ValidatorConfig()

    def check(self, widget_tree: dict[str, Any]) -> list[ConsistencyIssue]:
        """Run all consistency checks.

        Args:
            widget_tree: Nested widget tree from ``TreeExtractor``.

        Returns:
            List of detected consistency issues.
        """
        flat = self._flatten(widget_tree)
        issues: list[ConsistencyIssue] = []
        issues.extend(self._check_inconsistent_button_sizes(flat))
        issues.extend(self._check_inconsistent_entry_widths(flat))
        issues.extend(self._check_inconsistent_fonts(flat))
        issues.extend(self._check_inconsistent_padding(widget_tree))
        issues.extend(self._check_inconsistent_corner_radius(flat))
        issues.extend(self._check_mixed_layout_managers(widget_tree))
        issues.extend(self._check_inconsistent_spacing(flat))
        return issues

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_inconsistent_button_sizes(
        self, flat: list[dict[str, Any]]
    ) -> list[ConsistencyIssue]:
        """Flag sibling buttons with significantly different sizes."""
        return self._check_sibling_size_consistency(
            flat, _BUTTON_TYPES, "inconsistent_button_size", "button"
        )

    def _check_inconsistent_entry_widths(
        self, flat: list[dict[str, Any]]
    ) -> list[ConsistencyIssue]:
        """Flag sibling entries with significantly different widths."""
        return self._check_sibling_size_consistency(
            flat, _ENTRY_TYPES, "inconsistent_entry_width", "entry"
        )

    def _check_sibling_size_consistency(
        self,
        flat: list[dict[str, Any]],
        target_types: set[str],
        rule_id: str,
        type_label: str,
    ) -> list[ConsistencyIssue]:
        """Generic size consistency check for types grouped by parent."""
        issues: list[ConsistencyIssue] = []
        tolerance_pct = self._config.inconsistent_size_tolerance_pct

        groups: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
        for node in flat:
            if node.get("widget_type", "") in target_types:
                if node.get("width", 0) > 0:
                    groups[node.get("parent_id")].append(node)

        for siblings in groups.values():
            if len(siblings) < 2:
                continue
            widths = [s.get("width", 0) for s in siblings]
            heights = [s.get("height", 0) for s in siblings]
            avg_w = sum(widths) / len(widths)
            avg_h = sum(heights) / len(heights)
            if avg_w == 0 and avg_h == 0:
                continue

            for node in siblings:
                w = node.get("width", 0)
                h = node.get("height", 0)
                w_dev = abs(w - avg_w) / avg_w * 100 if avg_w > 0 else 0
                h_dev = abs(h - avg_h) / avg_h * 100 if avg_h > 0 else 0
                max_dev = max(w_dev, h_dev)
                if max_dev > tolerance_pct:
                    issues.append(
                        ConsistencyIssue(
                            rule_id=rule_id,
                            severity="low",
                            widget_id=node.get("test_id", "unknown"),
                            related_widget_id=None,
                            description=(
                                f"{type_label.title()} '{node.get('test_id')}' "
                                f"({w}x{h}px) deviates {max_dev:.0f}% from "
                                f"sibling average ({avg_w:.0f}x{avg_h:.0f}px)."
                            ),
                            recommended_fix=(
                                f"Standardise the size of '{node.get('test_id')}' "
                                f"to match its sibling {type_label}s for visual "
                                f"consistency."
                            ),
                            measured_value=max_dev,
                            threshold=tolerance_pct,
                        )
                    )
        return issues

    def _check_inconsistent_fonts(
        self, flat: list[dict[str, Any]]
    ) -> list[ConsistencyIssue]:
        """Flag sibling widgets of the same type using different fonts."""
        issues: list[ConsistencyIssue] = []
        comparable_types = _BUTTON_TYPES | _ENTRY_TYPES | {
            "CTkLabel", "TLabel", "Label",
            "CTkCheckBox", "TCheckBox", "Checkbutton",
        }

        # Group by (parent_id, widget_type)
        groups: dict[tuple[str | None, str], list[dict[str, Any]]] = defaultdict(list)
        for node in flat:
            wtype = node.get("widget_type", "")
            if wtype in comparable_types and node.get("font_family"):
                groups[(node.get("parent_id"), wtype)].append(node)

        for (_, wtype), siblings in groups.items():
            if len(siblings) < 2:
                continue
            fonts = set()
            for s in siblings:
                font_key = (
                    s.get("font_family", ""),
                    s.get("font_size", ""),
                    s.get("font_weight", ""),
                )
                fonts.add(font_key)

            if len(fonts) > 1:
                ids = [s.get("test_id", "?") for s in siblings]
                issues.append(
                    ConsistencyIssue(
                        rule_id="inconsistent_font",
                        severity="low",
                        widget_id=ids[0],
                        related_widget_id=ids[1] if len(ids) > 1 else None,
                        description=(
                            f"Sibling {wtype} widgets use {len(fonts)} different "
                            f"font styles: {', '.join(ids[:4])}. "
                            f"This creates visual inconsistency."
                        ),
                        recommended_fix=(
                            f"Use a consistent font for all {wtype} widgets "
                            f"within the same container."
                        ),
                    )
                )
        return issues

    def _check_inconsistent_padding(
        self, tree: dict[str, Any]
    ) -> list[ConsistencyIssue]:
        """Flag containers where children have widely varying padding."""
        issues: list[ConsistencyIssue] = []

        def _walk(node: dict[str, Any]) -> None:
            children = node.get("children", [])
            if len(children) < 3:
                for child in children:
                    _walk(child)
                return

            paddings_x: list[int] = []
            paddings_y: list[int] = []
            for child in children:
                pad = child.get("padding", {})
                paddings_x.append(pad.get("padx", 0))
                paddings_y.append(pad.get("pady", 0))

            if paddings_x:
                unique_px = set(paddings_x)
                if len(unique_px) > 2 and max(paddings_x) > 0:
                    issues.append(
                        ConsistencyIssue(
                            rule_id="inconsistent_padding",
                            severity="low",
                            widget_id=node.get("test_id", "unknown"),
                            related_widget_id=None,
                            description=(
                                f"Container '{node.get('test_id')}' has children "
                                f"with {len(unique_px)} different padx values: "
                                f"{sorted(unique_px)}. Use consistent padding."
                            ),
                            recommended_fix=(
                                f"Standardise padding-x for all children of "
                                f"'{node.get('test_id')}' to a single value."
                            ),
                        )
                    )

            for child in children:
                _walk(child)

        _walk(tree)
        return issues

    def _check_inconsistent_corner_radius(
        self, flat: list[dict[str, Any]]
    ) -> list[ConsistencyIssue]:
        """Flag sibling interactive widgets with different corner radii."""
        issues: list[ConsistencyIssue] = []
        target_types = _BUTTON_TYPES | _ENTRY_TYPES

        groups: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
        for node in flat:
            if node.get("widget_type", "") in target_types:
                if node.get("corner_radius") is not None:
                    groups[node.get("parent_id")].append(node)

        for siblings in groups.values():
            if len(siblings) < 2:
                continue
            radii = set(s.get("corner_radius") for s in siblings)
            if len(radii) > 1:
                ids = [s.get("test_id", "?") for s in siblings]
                issues.append(
                    ConsistencyIssue(
                        rule_id="inconsistent_corner_radius",
                        severity="low",
                        widget_id=ids[0],
                        related_widget_id=ids[1] if len(ids) > 1 else None,
                        description=(
                            f"Sibling interactive widgets use {len(radii)} "
                            f"different corner radii ({sorted(radii)}): "
                            f"{', '.join(ids[:4])}."
                        ),
                        recommended_fix=(
                            f"Use a consistent corner_radius for sibling "
                            f"interactive widgets."
                        ),
                    )
                )
        return issues

    def _check_mixed_layout_managers(
        self, tree: dict[str, Any]
    ) -> list[ConsistencyIssue]:
        """Flag containers whose children use different layout managers.

        Mixing pack() and grid() among siblings is a Tkinter error; mixing
        pack and place is legal but usually unintentional.
        """
        issues: list[ConsistencyIssue] = []

        def _walk(node: dict[str, Any]) -> None:
            children = node.get("children", [])
            if len(children) < 2:
                for child in children:
                    _walk(child)
                return

            managers: set[str | None] = set()
            for child in children:
                mgr = child.get("layout_manager")
                if mgr:
                    managers.add(mgr)

            # Mixing pack+grid is a Tkinter error; pack+place or grid+place is suspicious
            if len(managers) > 1:
                mgr_list = sorted(managers)
                severity = "high" if {"pack", "grid"} <= managers else "medium"
                issues.append(
                    ConsistencyIssue(
                        rule_id="mixed_layout_managers",
                        severity=severity,
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Container '{node.get('test_id')}' mixes layout "
                            f"managers ({', '.join(mgr_list)}) among its children. "
                            f"{'Mixing pack and grid will cause a Tkinter error.' if severity == 'high' else 'This may cause unexpected layout behaviour.'}"
                        ),
                        recommended_fix=(
                            f"Use a single layout manager for all children of "
                            f"'{node.get('test_id')}'."
                        ),
                    )
                )

            for child in children:
                _walk(child)

        _walk(tree)
        return issues

    def _check_inconsistent_spacing(
        self, flat: list[dict[str, Any]]
    ) -> list[ConsistencyIssue]:
        """Flag varying gaps between adjacent siblings in the same container.

        Checks that the spacing between consecutive siblings (sorted by
        position) is reasonably uniform.
        """
        issues: list[ConsistencyIssue] = []

        groups: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
        for node in flat:
            if node.get("width", 0) > 0 and node.get("height", 0) > 0:
                groups[node.get("parent_id")].append(node)

        for parent_id, siblings in groups.items():
            if len(siblings) < 3:
                continue

            # Sort by vertical then horizontal position
            siblings_sorted = sorted(
                siblings, key=lambda n: (n.get("abs_y", 0), n.get("abs_x", 0))
            )

            gaps: list[int] = []
            for i in range(len(siblings_sorted) - 1):
                a = siblings_sorted[i]
                b = siblings_sorted[i + 1]
                # Vertical gap
                gap = b.get("abs_y", 0) - (a.get("abs_y", 0) + a.get("height", 0))
                if gap <= 0:
                    # Horizontal gap
                    gap = b.get("abs_x", 0) - (a.get("abs_x", 0) + a.get("width", 0))
                if gap > 0:
                    gaps.append(gap)

            if len(gaps) >= 2:
                avg_gap = sum(gaps) / len(gaps)
                if avg_gap > 0:
                    max_dev = max(abs(g - avg_gap) for g in gaps)
                    if max_dev > avg_gap * 0.8 and max_dev > 10:
                        issues.append(
                            ConsistencyIssue(
                                rule_id="inconsistent_spacing",
                                severity="low",
                                widget_id=parent_id or "unknown",
                                related_widget_id=None,
                                description=(
                                    f"Container '{parent_id}' has inconsistent "
                                    f"spacing between children: gaps range from "
                                    f"{min(gaps)}px to {max(gaps)}px "
                                    f"(average: {avg_gap:.0f}px)."
                                ),
                                recommended_fix=(
                                    f"Use uniform padding/spacing for children "
                                    f"of '{parent_id}' to create a more polished "
                                    f"layout."
                                ),
                                measured_value=float(max_dev),
                                threshold=float(avg_gap * 0.8),
                            )
                        )
        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _flatten(node: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if not node:
            return result
        result.append({k: v for k, v in node.items() if k != "children"})
        for child in node.get("children", []):
            result.extend(ConsistencyChecker._flatten(child))
        return result
