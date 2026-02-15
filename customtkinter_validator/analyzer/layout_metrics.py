"""Layout metrics analyser: computes spatial relationships between widgets.

Detects overlapping widgets, insufficient padding, alignment inconsistencies,
symmetry issues, and undersized touch targets. All measurements use actual
geometry data obtained via Tkinter introspection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from customtkinter_validator.core.config import ValidatorConfig


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box for a widget.

    Attributes:
        test_id: The widget's deterministic test_id.
        x: Absolute x-coordinate of the left edge.
        y: Absolute y-coordinate of the top edge.
        width: Widget width in pixels.
        height: Widget height in pixels.
    """

    test_id: str
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Return the x-coordinate of the right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Return the y-coordinate of the bottom edge."""
        return self.y + self.height

    @property
    def center_x(self) -> float:
        """Return the x-coordinate of the centre."""
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        """Return the y-coordinate of the centre."""
        return self.y + self.height / 2.0

    def overlaps(self, other: BoundingBox, tolerance: int = 0) -> bool:
        """Check whether this box overlaps *other* beyond *tolerance* pixels.

        Args:
            other: The other bounding box.
            tolerance: Pixel overlap that is still acceptable.

        Returns:
            ``True`` if the boxes overlap by more than *tolerance*.
        """
        overlap_x = max(0, min(self.right, other.right) - max(self.x, other.x))
        overlap_y = max(0, min(self.bottom, other.bottom) - max(self.y, other.y))
        return overlap_x > tolerance and overlap_y > tolerance

    def distance_to(self, other: BoundingBox) -> int:
        """Compute the minimum edge-to-edge distance to *other*.

        Returns zero if the boxes overlap.

        Args:
            other: The other bounding box.

        Returns:
            Distance in pixels (non-negative).
        """
        dx = max(0, max(self.x - other.right, other.x - self.right))
        dy = max(0, max(self.y - other.bottom, other.y - self.bottom))
        return max(dx, dy)


@dataclass(frozen=True)
class LayoutViolation:
    """A detected layout issue.

    Attributes:
        rule_id: Machine-readable rule identifier.
        severity: One of ``"critical"``, ``"high"``, ``"medium"``, ``"low"``.
        widget_id: Primary widget involved.
        related_widget_id: Secondary widget involved (if any).
        description: Human-readable explanation of the issue.
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
        """Serialise to a plain dictionary.

        Returns:
            JSON-safe dictionary.
        """
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


class LayoutMetrics:
    """Computes spatial metrics and detects layout issues across the widget tree.

    Operates on the flat widget-tree dictionary produced by ``TreeExtractor``.
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        """Initialise the layout analyser.

        Args:
            config: Optional configuration overrides.
        """
        self._config = config or ValidatorConfig()

    def analyse(self, widget_tree: dict[str, Any]) -> list[LayoutViolation]:
        """Run all layout checks on the extracted widget tree.

        Args:
            widget_tree: The nested widget-tree dictionary from ``TreeExtractor``.

        Returns:
            List of all detected layout violations.
        """
        flat = self._flatten(widget_tree)

        violations: list[LayoutViolation] = []
        violations.extend(self._check_overlaps(flat))
        violations.extend(self._check_spacing(flat))
        violations.extend(self._check_touch_targets(flat))
        violations.extend(self._check_alignment(flat))
        violations.extend(self._check_symmetry(flat))
        violations.extend(self._check_widget_outside_bounds(flat))
        violations.extend(self._check_content_truncation_risk(flat))
        return violations

    def compute_spacing(self, widget_tree: dict[str, Any]) -> list[dict[str, Any]]:
        """Compute pairwise spacing distances between sibling widgets.

        Args:
            widget_tree: The nested widget tree.

        Returns:
            List of spacing records.
        """
        records: list[dict[str, Any]] = []
        self._compute_sibling_spacing(widget_tree, records)
        return records

    def _flatten(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten a nested widget tree into a list of nodes.

        Args:
            node: Root of the tree or subtree.

        Returns:
            Flat list of all widget nodes.
        """
        result: list[dict[str, Any]] = []
        if not node:
            return result
        node_copy = {k: v for k, v in node.items() if k != "children"}
        result.append(node_copy)
        for child in node.get("children", []):
            result.extend(self._flatten(child))
        return result

    @staticmethod
    def _to_box(node: dict[str, Any]) -> BoundingBox:
        """Convert a flat widget node to a ``BoundingBox``.

        Args:
            node: The widget metadata dictionary.

        Returns:
            A bounding box.
        """
        return BoundingBox(
            test_id=node.get("test_id", "unknown"),
            x=node.get("abs_x", 0),
            y=node.get("abs_y", 0),
            width=node.get("width", 0),
            height=node.get("height", 0),
        )

    def _check_overlaps(self, flat: list[dict[str, Any]]) -> list[LayoutViolation]:
        """Detect overlapping widget bounding boxes among sibling widgets.

        Only checks overlap between widgets that share the same parent,
        preventing false positives from parent-child containment.

        Args:
            flat: Flat list of all widget nodes.

        Returns:
            Overlap violations.
        """
        violations: list[LayoutViolation] = []
        tolerance = self._config.overlap_tolerance_px

        groups: dict[str | None, list[dict[str, Any]]] = {}
        for node in flat:
            if not node.get("visibility", True):
                continue
            parent = node.get("parent_id")
            groups.setdefault(parent, []).append(node)

        for siblings in groups.values():
            if len(siblings) < 2:
                continue
            boxes = [self._to_box(s) for s in siblings]
            for i, a in enumerate(boxes):
                if a.width == 0 or a.height == 0:
                    continue
                for b in boxes[i + 1 :]:
                    if b.width == 0 or b.height == 0:
                        continue
                    if a.overlaps(b, tolerance):
                        overlap_x = max(
                            0, min(a.right, b.right) - max(a.x, b.x)
                        )
                        overlap_y = max(
                            0, min(a.bottom, b.bottom) - max(a.y, b.y)
                        )
                        violations.append(
                            LayoutViolation(
                                rule_id="overlap_detection",
                                severity="high",
                                widget_id=a.test_id,
                                related_widget_id=b.test_id,
                                description=(
                                    f"'{a.test_id}' overlaps '{b.test_id}' "
                                    f"by {overlap_x}x{overlap_y}px"
                                ),
                                recommended_fix=(
                                    f"Increase spacing between '{a.test_id}' and "
                                    f"'{b.test_id}' or adjust their positions"
                                ),
                                measured_value=float(max(overlap_x, overlap_y)),
                                threshold=float(tolerance),
                            )
                        )
        return violations

    def _check_spacing(self, flat: list[dict[str, Any]]) -> list[LayoutViolation]:
        """Detect insufficient padding between sibling widgets.

        Groups widgets by their ``parent_id`` and checks the distances
        between same-parent siblings.

        Args:
            flat: Flat list of widget nodes.

        Returns:
            Spacing violations.
        """
        violations: list[LayoutViolation] = []
        groups: dict[str | None, list[dict[str, Any]]] = {}
        for node in flat:
            if not node.get("visibility", True):
                continue
            parent = node.get("parent_id")
            groups.setdefault(parent, []).append(node)

        min_pad = self._config.min_padding_px
        for siblings in groups.values():
            if len(siblings) < 2:
                continue
            boxes = [self._to_box(s) for s in siblings]
            for i, a in enumerate(boxes):
                if a.width == 0 or a.height == 0:
                    continue
                for b in boxes[i + 1 :]:
                    if b.width == 0 or b.height == 0:
                        continue
                    dist = a.distance_to(b)
                    if 0 < dist < min_pad:
                        violations.append(
                            LayoutViolation(
                                rule_id="insufficient_padding",
                                severity="medium",
                                widget_id=a.test_id,
                                related_widget_id=b.test_id,
                                description=(
                                    f"Spacing between '{a.test_id}' and "
                                    f"'{b.test_id}' is {dist}px (minimum: {min_pad}px)"
                                ),
                                recommended_fix=(
                                    f"Add at least {min_pad - dist}px more padding "
                                    f"between '{a.test_id}' and '{b.test_id}'"
                                ),
                                measured_value=float(dist),
                                threshold=float(min_pad),
                            )
                        )
        return violations

    def _check_touch_targets(self, flat: list[dict[str, Any]]) -> list[LayoutViolation]:
        """Detect interactive widgets smaller than the minimum touch target.

        Args:
            flat: Flat list of widget nodes.

        Returns:
            Touch-target violations.
        """
        violations: list[LayoutViolation] = []
        interactive_types = {
            "CTkButton", "CTkEntry", "CTkCheckBox", "CTkSwitch",
            "CTkRadioButton", "CTkSlider", "CTkOptionMenu", "CTkComboBox",
            "CTkSegmentedButton", "CTkTextbox",
            "TButton", "TEntry", "TCheckBox", "TSwitch",
            "TRadioButton", "TSlider", "TOptionMenu", "TComboBox", "TTextbox",
            "Button", "Entry", "Checkbutton", "Radiobutton", "Scale",
            "Spinbox", "Combobox",
        }
        min_size = self._config.min_touch_target_px
        for node in flat:
            wtype = node.get("widget_type", "")
            if wtype not in interactive_types:
                continue
            if not node.get("visibility", True):
                continue
            w = node.get("width", 0)
            h = node.get("height", 0)
            if w > 0 and h > 0 and (w < min_size or h < min_size):
                violations.append(
                    LayoutViolation(
                        rule_id="small_touch_target",
                        severity="medium",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"'{node.get('test_id')}' is {w}x{h}px, below "
                            f"the minimum touch target of {min_size}px"
                        ),
                        recommended_fix=(
                            f"Increase the size of '{node.get('test_id')}' to "
                            f"at least {min_size}x{min_size}px"
                        ),
                        measured_value=float(min(w, h)),
                        threshold=float(min_size),
                    )
                )
        return violations

    def _check_alignment(self, flat: list[dict[str, Any]]) -> list[LayoutViolation]:
        """Detect alignment inconsistencies among sibling widgets.

        Groups siblings by parent and checks whether their left edges are
        consistently aligned. For grid-managed containers, alignment is
        checked within each grid column separately so that multi-column
        layouts are not penalised.

        Args:
            flat: Flat list of widget nodes.

        Returns:
            Alignment violations.
        """
        violations: list[LayoutViolation] = []
        groups: dict[str | None, list[dict[str, Any]]] = {}
        for node in flat:
            if not node.get("visibility", True):
                continue
            parent = node.get("parent_id")
            groups.setdefault(parent, []).append(node)

        tolerance = self._config.alignment_tolerance_px
        for siblings in groups.values():
            if len(siblings) < 3:
                continue

            # Determine if siblings are grid-managed
            grid_managed = any(
                node.get("layout_manager") == "grid" for node in siblings
            )

            if grid_managed:
                # Group by grid column and check alignment within each column.
                # Grid manages alignment via cell structure; small pixel
                # differences arise from sticky settings and internal padding,
                # so we use a more lenient tolerance.
                grid_tolerance = max(tolerance * 3, 10)
                col_groups: dict[int, list[dict[str, Any]]] = {}
                for s in siblings:
                    detail: dict[str, Any] = s.get("layout_detail") or {}
                    col_val: Any = detail.get("col", detail.get("column", 0))
                    try:
                        col_idx = int(col_val)
                    except (ValueError, TypeError):
                        col_idx = 0
                    col_groups.setdefault(col_idx, []).append(s)
                for col_siblings in col_groups.values():
                    self._check_alignment_group(col_siblings, grid_tolerance, violations)
            else:
                self._check_alignment_group(siblings, tolerance, violations)

        return violations

    def _check_alignment_group(
        self,
        siblings: list[dict[str, Any]],
        tolerance: int,
        violations: list[LayoutViolation],
    ) -> None:
        """Check left-edge alignment for a group of sibling widgets."""
        if len(siblings) < 3:
            return
        left_edges = [s.get("abs_x", 0) for s in siblings if s.get("width", 0) > 0]
        if len(left_edges) < 3:
            return
        most_common_x = max(set(left_edges), key=left_edges.count)
        for s in siblings:
            sx = s.get("abs_x", 0)
            if s.get("width", 0) == 0:
                continue
            diff = abs(sx - most_common_x)
            if 0 < diff > tolerance:
                violations.append(
                    LayoutViolation(
                        rule_id="alignment_inconsistency",
                        severity="low",
                        widget_id=s.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"'{s.get('test_id')}' left edge at x={sx} deviates "
                            f"{diff}px from the common alignment at x={most_common_x}"
                        ),
                        recommended_fix=(
                            f"Align '{s.get('test_id')}' with its siblings at "
                            f"x={most_common_x}"
                        ),
                        measured_value=float(diff),
                        threshold=float(tolerance),
                    )
                )

    def _check_symmetry(self, flat: list[dict[str, Any]]) -> list[LayoutViolation]:
        """Basic symmetry detection within containers.

        Checks whether widgets within a container are approximately symmetrical
        about the container's horizontal centre.

        Grid-managed containers are skipped because multi-column grids are
        intentionally asymmetric (e.g. label – entry pairs).

        Args:
            flat: Flat list of widget nodes.

        Returns:
            Symmetry violations.
        """
        violations: list[LayoutViolation] = []
        tolerance = self._config.symmetry_tolerance_px

        node_map = {n.get("test_id"): n for n in flat}
        container_types = self._config.container_widget_types

        groups: dict[str | None, list[dict[str, Any]]] = {}
        for node in flat:
            if not node.get("visibility", True):
                continue
            parent = node.get("parent_id")
            groups.setdefault(parent, []).append(node)

        for parent_id, children in groups.items():
            if parent_id is None:
                continue
            parent_node = node_map.get(parent_id)
            if parent_node is None:
                continue
            if parent_node.get("widget_type") not in container_types:
                continue
            parent_width = parent_node.get("width", 0)
            if parent_width <= 0 or len(children) < 2:
                continue

            # Skip grid-managed containers — they are intentionally asymmetric
            if any(c.get("layout_manager") == "grid" for c in children):
                continue

            parent_abs_x = parent_node.get("abs_x", 0)
            center_x = parent_abs_x + parent_width / 2.0

            for child in children:
                cw = child.get("width", 0)
                if cw <= 0:
                    continue
                child_center = child.get("abs_x", 0) + cw / 2.0
                _ = abs(child_center - center_x)  # centre offset for diagnostics
                left_space = child.get("abs_x", 0) - parent_abs_x
                right_space = (parent_abs_x + parent_width) - (child.get("abs_x", 0) + cw)
                space_diff = abs(left_space - right_space)
                if space_diff > tolerance and left_space > 0 and right_space > 0:
                    if space_diff > parent_width * 0.3:
                        violations.append(
                            LayoutViolation(
                                rule_id="symmetry_deviation",
                                severity="low",
                                widget_id=child.get("test_id", "unknown"),
                                related_widget_id=parent_id,
                                description=(
                                    f"'{child.get('test_id')}' has asymmetric placement "
                                    f"within '{parent_id}': left space={left_space}px, "
                                    f"right space={right_space}px"
                                ),
                                recommended_fix=(
                                    f"Centre '{child.get('test_id')}' within '{parent_id}' "
                                    f"or use consistent margins"
                                ),
                                measured_value=float(space_diff),
                                threshold=float(tolerance),
                            )
                        )
        return violations

    def _check_widget_outside_bounds(
        self, flat: list[dict[str, Any]]
    ) -> list[LayoutViolation]:
        """Detect child widgets extending beyond their parent's bounding box.

        Invisible widgets (e.g. inactive ``CTkTabview`` tab content) are
        excluded.

        Args:
            flat: Flat list of widget nodes.

        Returns:
            Out-of-bounds violations.
        """
        violations: list[LayoutViolation] = []
        tolerance = self._config.widget_outside_bounds_tolerance_px

        node_map = {n.get("test_id"): n for n in flat}

        for node in flat:
            if not node.get("visibility", True):
                continue
            parent_id = node.get("parent_id")
            if parent_id is None:
                continue
            parent = node_map.get(parent_id)
            if parent is None:
                continue
            pw = parent.get("width", 0)
            ph = parent.get("height", 0)
            if pw <= 0 or ph <= 0:
                continue

            w = node.get("width", 0)
            h = node.get("height", 0)
            if w <= 0 or h <= 0:
                continue

            child_right = node.get("abs_x", 0) + w
            child_bottom = node.get("abs_y", 0) + h
            parent_right = parent.get("abs_x", 0) + pw
            parent_bottom = parent.get("abs_y", 0) + ph

            overflow_right = child_right - parent_right
            overflow_bottom = child_bottom - parent_bottom
            overflow_left = parent.get("abs_x", 0) - node.get("abs_x", 0)
            overflow_top = parent.get("abs_y", 0) - node.get("abs_y", 0)

            max_overflow = max(overflow_right, overflow_bottom, overflow_left, overflow_top)
            if max_overflow > tolerance:
                violations.append(
                    LayoutViolation(
                        rule_id="widget_outside_bounds",
                        severity="medium",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=parent_id,
                        description=(
                            f"Widget '{node.get('test_id')}' extends "
                            f"{max_overflow}px beyond its parent "
                            f"'{parent_id}' bounds"
                        ),
                        recommended_fix=(
                            f"Resize or reposition '{node.get('test_id')}' to "
                            f"fit within '{parent_id}', or expand the parent"
                        ),
                        measured_value=float(max_overflow),
                        threshold=float(tolerance),
                    )
                )
        return violations

    def _check_content_truncation_risk(
        self, flat: list[dict[str, Any]]
    ) -> list[LayoutViolation]:
        """Flag text widgets whose text length suggests possible truncation.

        Uses a rough estimate: if text characters × 8px exceeds the widget
        width, the text may be clipped. Invisible widgets are skipped.

        Args:
            flat: Flat list of widget nodes.

        Returns:
            Truncation-risk violations.
        """
        violations: list[LayoutViolation] = []
        label_types = {"CTkLabel", "TLabel", "Label", "CTkButton", "TButton", "Button"}

        for node in flat:
            wtype = node.get("widget_type", "")
            if wtype not in label_types:
                continue
            if not node.get("visibility", True):
                continue
            text = node.get("text") or ""
            if not text or len(text) < 5:
                continue
            w = node.get("width", 0)
            if w <= 0:
                continue
            # Rough per-character width: 8px average for typical font size
            font_size = node.get("font_size")
            char_width = 8
            if font_size:
                try:
                    char_width = max(5, abs(int(font_size)) * 0.6)
                except (ValueError, TypeError):
                    pass
            estimated_text_width = len(text) * char_width
            # Add some padding for widget internal padding
            available = w - 16  # 8px padding on each side
            if available > 0 and estimated_text_width > available * 1.2:
                violations.append(
                    LayoutViolation(
                        rule_id="content_truncation_risk",
                        severity="low",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Widget '{node.get('test_id')}' text "
                            f"('{text[:30]}{'...' if len(text) > 30 else ''}') "
                            f"may be truncated: estimated width ~{estimated_text_width:.0f}px "
                            f"vs available ~{available:.0f}px"
                        ),
                        recommended_fix=(
                            f"Increase the width of '{node.get('test_id')}' or "
                            f"shorten its text to prevent truncation"
                        ),
                        measured_value=float(estimated_text_width),
                        threshold=float(available),
                    )
                )
        return violations

    def _compute_sibling_spacing(
        self, node: dict[str, Any], records: list[dict[str, Any]]
    ) -> None:
        """Recursively compute spacing between sibling widgets.

        Args:
            node: Current widget tree node.
            records: Accumulator for spacing records.
        """
        children = node.get("children", [])
        if len(children) >= 2:
            boxes = [self._to_box(c) for c in children]
            for i, a in enumerate(boxes):
                for b in boxes[i + 1 :]:
                    dist = a.distance_to(b)
                    records.append(
                        {
                            "widget_a": a.test_id,
                            "widget_b": b.test_id,
                            "distance_px": dist,
                            "parent_id": node.get("test_id"),
                        }
                    )
        for child in children:
            self._compute_sibling_spacing(child, records)
