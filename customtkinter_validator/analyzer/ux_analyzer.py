"""UX heuristics analyser: detects common usability anti-patterns.

Checks cover cognitive complexity, labelling quality, widget relationships,
text conventions, and interactive-element design. All checks operate on the
serialised widget-tree metadata — no live widgets or screenshots required.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from customtkinter_validator.core.config import ValidatorConfig


@dataclass(frozen=True)
class UXIssue:
    """A detected UX heuristic violation.

    Attributes:
        rule_id: Machine-readable rule identifier.
        severity: ``"critical"``, ``"high"``, ``"medium"``, or ``"low"``.
        widget_id: Primary widget involved.
        related_widget_id: Secondary widget involved (if any).
        description: Human-readable explanation.
        recommended_fix: Suggested resolution.
    """

    rule_id: str
    severity: str
    widget_id: str
    related_widget_id: str | None
    description: str
    recommended_fix: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dictionary."""
        result: dict[str, Any] = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "widget_id": self.widget_id,
            "description": self.description,
            "recommended_fix": self.recommended_fix,
        }
        if self.related_widget_id is not None:
            result["related_widget_id"] = self.related_widget_id
        return result


# Type sets used across multiple checks
_ENTRY_TYPES: set[str] = {
    "CTkEntry", "CTkTextbox", "CTkComboBox",
    "TEntry", "TTextbox", "TComboBox",
    "Entry", "Text", "Combobox", "Spinbox",
}

_BUTTON_TYPES: set[str] = {
    "CTkButton", "TButton", "Button",
}

_LABEL_TYPES: set[str] = {
    "CTkLabel", "TLabel", "Label",
}

_INTERACTIVE_TYPES: set[str] = _ENTRY_TYPES | _BUTTON_TYPES | {
    "CTkCheckBox", "CTkSwitch", "CTkRadioButton", "CTkSlider",
    "CTkOptionMenu", "CTkSegmentedButton",
    "TCheckBox", "TSwitch", "TRadioButton", "TSlider", "TOptionMenu",
    "Checkbutton", "Radiobutton", "Scale",
}

_CONTAINER_TYPES: set[str] = {
    "CTk", "CTkToplevel", "CTkFrame", "CTkScrollableFrame", "CTkTabview",
    "TFrame", "Frame", "LabelFrame", "Toplevel", "Tk",
}


class UXAnalyzer:
    """Evaluates the widget tree against UX usability heuristics.

    Checks include:
    - Cognitive overload (too many widgets in a container)
    - Duplicate button labels
    - Long button text
    - Inconsistent text casing across buttons
    - Missing placeholder text on entries
    - Orphaned labels (labels not near an input)
    - Single-child containers (unnecessary nesting)
    - Missing window title
    - Non-interactive labels that look like they should be buttons
    - Empty option menu / combobox
    - Radio buttons not grouped together
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        self._config = config or ValidatorConfig()

    def analyse(self, widget_tree: dict[str, Any]) -> list[UXIssue]:
        """Run all UX heuristic checks.

        Args:
            widget_tree: Nested widget tree from ``TreeExtractor``.

        Returns:
            List of detected UX issues.
        """
        flat = self._flatten(widget_tree)
        issues: list[UXIssue] = []
        issues.extend(self._check_cognitive_overload(widget_tree))
        issues.extend(self._check_duplicate_button_labels(flat))
        issues.extend(self._check_long_button_text(flat))
        issues.extend(self._check_inconsistent_button_casing(flat))
        issues.extend(self._check_missing_placeholder(flat))
        issues.extend(self._check_orphaned_labels(flat))
        issues.extend(self._check_single_child_containers(widget_tree))
        issues.extend(self._check_missing_window_title(widget_tree))
        issues.extend(self._check_empty_selection_widget(flat))
        issues.extend(self._check_ungrouped_radio_buttons(flat))
        issues.extend(self._check_no_primary_action(flat))
        issues.extend(self._check_button_without_command(flat))
        issues.extend(self._check_deep_single_nesting(widget_tree))
        return issues

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_cognitive_overload(self, tree: dict[str, Any]) -> list[UXIssue]:
        """Flag containers with too many direct children.

        More than ``max_widgets_per_container`` children in a single
        container suggests the layout should be reorganised.
        """
        issues: list[UXIssue] = []
        max_w = self._config.max_widgets_per_container

        def _walk(node: dict[str, Any]) -> None:
            children = node.get("children", [])
            wtype = node.get("widget_type", "")
            # Only count user-visible children (not internal CTk widgets)
            visible_children = [
                c for c in children
                if c.get("visibility", True) and c.get("width", 0) > 0
            ]
            if len(visible_children) > max_w and wtype in _CONTAINER_TYPES:
                issues.append(
                    UXIssue(
                        rule_id="cognitive_overload",
                        severity="medium",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Container '{node.get('test_id')}' has "
                            f"{len(visible_children)} visible children "
                            f"(recommended max: {max_w}). This may overwhelm "
                            f"users — consider grouping into sub-sections."
                        ),
                        recommended_fix=(
                            f"Split the content of '{node.get('test_id')}' into "
                            f"logical groups using sub-frames, tabs, or collapsible "
                            f"sections."
                        ),
                    )
                )
            for child in children:
                _walk(child)

        _walk(tree)
        return issues

    def _check_duplicate_button_labels(self, flat: list[dict[str, Any]]) -> list[UXIssue]:
        """Flag multiple buttons sharing the same text label.

        Duplicate labels make it hard for users (and AI agents) to
        distinguish between actions.
        """
        issues: list[UXIssue] = []
        buttons: list[dict[str, Any]] = []
        for node in flat:
            if node.get("widget_type", "") in _BUTTON_TYPES:
                text = (node.get("text") or "").strip()
                if text:
                    buttons.append(node)

        text_groups: dict[str, list[str]] = {}
        for btn in buttons:
            key = (btn.get("text") or "").strip().lower()
            text_groups.setdefault(key, []).append(btn.get("test_id", "unknown"))

        for text_lower, ids in text_groups.items():
            if len(ids) > 1:
                issues.append(
                    UXIssue(
                        rule_id="duplicate_button_label",
                        severity="medium",
                        widget_id=ids[0],
                        related_widget_id=ids[1],
                        description=(
                            f"Multiple buttons share the label "
                            f"'{text_lower}': {', '.join(ids)}. "
                            f"Users cannot distinguish their purpose."
                        ),
                        recommended_fix=(
                            f"Give each button a unique, descriptive label "
                            f"that clarifies its specific action."
                        ),
                    )
                )
        return issues

    def _check_long_button_text(self, flat: list[dict[str, Any]]) -> list[UXIssue]:
        """Flag buttons with excessively long text labels."""
        issues: list[UXIssue] = []
        max_len = self._config.max_button_text_length
        for node in flat:
            if node.get("widget_type", "") not in _BUTTON_TYPES:
                continue
            text = (node.get("text") or "").strip()
            if len(text) > max_len:
                issues.append(
                    UXIssue(
                        rule_id="long_button_text",
                        severity="low",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Button '{node.get('test_id')}' has a "
                            f"{len(text)}-character label (max recommended: "
                            f"{max_len}). Long labels reduce scannability."
                        ),
                        recommended_fix=(
                            f"Shorten the button text to a concise action verb "
                            f"or short phrase (e.g. 'Save', 'Submit', 'Export Data')."
                        ),
                    )
                )
        return issues

    def _check_inconsistent_button_casing(
        self, flat: list[dict[str, Any]]
    ) -> list[UXIssue]:
        """Flag inconsistent text casing across buttons.

        Detects a mix of Title Case, UPPERCASE, lowercase, and Sentence case
        among button labels in the same application.
        """
        issues: list[UXIssue] = []
        casings: dict[str, list[str]] = {}

        for node in flat:
            if node.get("widget_type", "") not in _BUTTON_TYPES:
                continue
            text = (node.get("text") or "").strip()
            if not text or len(text) < 2:
                continue
            casing = self._classify_casing(text)
            casings.setdefault(casing, []).append(node.get("test_id", "unknown"))

        if len(casings) > 1:
            detail_parts = [
                f"{style}: {', '.join(ids[:3])}"
                for style, ids in casings.items()
            ]
            majority_style = max(casings, key=lambda k: len(casings[k]))
            minority_ids = [
                tid
                for style, ids in casings.items()
                if style != majority_style
                for tid in ids
            ]
            if minority_ids:
                issues.append(
                    UXIssue(
                        rule_id="inconsistent_button_casing",
                        severity="low",
                        widget_id=minority_ids[0],
                        related_widget_id=None,
                        description=(
                            f"Button labels use mixed text casing styles: "
                            f"{'; '.join(detail_parts)}. "
                            f"This creates visual inconsistency."
                        ),
                        recommended_fix=(
                            f"Standardise all button labels to '{majority_style}' "
                            f"casing for visual consistency."
                        ),
                    )
                )
        return issues

    def _check_missing_placeholder(self, flat: list[dict[str, Any]]) -> list[UXIssue]:
        """Flag entry widgets without placeholder or hint text.

        Entries without placeholders leave users guessing about expected input.
        """
        issues: list[UXIssue] = []
        for node in flat:
            wtype = node.get("widget_type", "")
            if wtype not in _ENTRY_TYPES:
                continue
            # Skip textboxes (large multi-line widgets typically don't need placeholders)
            if "Textbox" in wtype or "Text" == wtype:
                continue
            placeholder = node.get("placeholder_text")
            text = node.get("text")
            if not placeholder and not text:
                issues.append(
                    UXIssue(
                        rule_id="missing_placeholder",
                        severity="low",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Entry '{node.get('test_id')}' has no placeholder "
                            f"text. Users may not understand what input is expected."
                        ),
                        recommended_fix=(
                            f"Add placeholder_text to '{node.get('test_id')}' "
                            f"describing the expected input format or content."
                        ),
                    )
                )
        return issues

    def _check_orphaned_labels(self, flat: list[dict[str, Any]]) -> list[UXIssue]:
        """Flag labels in containers that have no nearby input widget.

        An orphaned label has text but shares no parent with any entry or
        interactive widget, suggesting it may be misplaced.
        """
        issues: list[UXIssue] = []
        # Group by parent
        inputs_by_parent: dict[str | None, int] = {}
        labels_by_parent: dict[str | None, list[dict[str, Any]]] = {}

        for node in flat:
            wtype = node.get("widget_type", "")
            parent = node.get("parent_id")
            if wtype in _INTERACTIVE_TYPES:
                inputs_by_parent[parent] = inputs_by_parent.get(parent, 0) + 1
            if wtype in _LABEL_TYPES:
                text = (node.get("text") or "").strip()
                # Only check labels that end with ':' (i.e. look like field labels)
                if text and text.endswith(":"):
                    labels_by_parent.setdefault(parent, []).append(node)

        for parent, labels in labels_by_parent.items():
            if inputs_by_parent.get(parent, 0) == 0:
                for label_node in labels:
                    issues.append(
                        UXIssue(
                            rule_id="orphaned_label",
                            severity="low",
                            widget_id=label_node.get("test_id", "unknown"),
                            related_widget_id=None,
                            description=(
                                f"Label '{label_node.get('test_id')}' (text: "
                                f"'{label_node.get('text')}') appears to be a "
                                f"field label but has no input widget in the "
                                f"same container."
                            ),
                            recommended_fix=(
                                f"Move '{label_node.get('test_id')}' to the same "
                                f"container as its associated input widget, or "
                                f"remove it if unnecessary."
                            ),
                        )
                    )
        return issues

    def _check_single_child_containers(
        self, tree: dict[str, Any]
    ) -> list[UXIssue]:
        """Flag containers with exactly one child (unnecessary nesting).

        Single-child frames add complexity without benefit. This excludes
        root windows and scrollable containers.
        """
        issues: list[UXIssue] = []

        def _walk(node: dict[str, Any], is_root: bool = False) -> None:
            children = node.get("children", [])
            wtype = node.get("widget_type", "")
            if (
                not is_root
                and wtype in _CONTAINER_TYPES
                and wtype not in ("CTk", "Tk", "Toplevel", "CTkToplevel",
                                  "CTkScrollableFrame", "CTkTabview")
                and len(children) == 1
            ):
                child = children[0]
                # Only flag if the single child is also a container
                if child.get("widget_type", "") in _CONTAINER_TYPES:
                    issues.append(
                        UXIssue(
                            rule_id="single_child_container",
                            severity="low",
                            widget_id=node.get("test_id", "unknown"),
                            related_widget_id=child.get("test_id"),
                            description=(
                                f"Container '{node.get('test_id')}' has only one "
                                f"child ('{child.get('test_id')}'), which is also "
                                f"a container. This may be unnecessary nesting."
                            ),
                            recommended_fix=(
                                f"Consider merging '{node.get('test_id')}' and "
                                f"'{child.get('test_id')}' into a single container "
                                f"to simplify the widget hierarchy."
                            ),
                        )
                    )
            for child in children:
                _walk(child)

        _walk(tree, is_root=True)
        return issues

    def _check_missing_window_title(
        self, tree: dict[str, Any]
    ) -> list[UXIssue]:
        """Flag root windows without a meaningful title."""
        issues: list[UXIssue] = []
        wtype = tree.get("widget_type", "")
        if wtype in ("CTk", "Tk", "Toplevel", "CTkToplevel"):
            text = (tree.get("text") or "").strip()
            # CTk windows don't expose title via text — this is best-effort
            if not text or text in ("tk", "ctk", ""):
                issues.append(
                    UXIssue(
                        rule_id="missing_window_title",
                        severity="medium",
                        widget_id=tree.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Application window '{tree.get('test_id')}' has no "
                            f"meaningful title. Window titles help users identify "
                            f"the application."
                        ),
                        recommended_fix=(
                            f"Set a descriptive window title using "
                            f"app.title('My Application')."
                        ),
                    )
                )
        return issues

    def _check_empty_selection_widget(
        self, flat: list[dict[str, Any]]
    ) -> list[UXIssue]:
        """Flag option menus or combo boxes with no selectable values."""
        issues: list[UXIssue] = []
        selection_types = {
            "CTkOptionMenu", "CTkComboBox",
            "TOptionMenu", "TComboBox",
            "OptionMenu", "Combobox",
        }
        for node in flat:
            wtype = node.get("widget_type", "")
            if wtype not in selection_types:
                continue
            values = node.get("values")
            if not values or len(values) == 0:
                issues.append(
                    UXIssue(
                        rule_id="empty_selection_widget",
                        severity="medium",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Selection widget '{node.get('test_id')}' "
                            f"({wtype}) has no selectable values."
                        ),
                        recommended_fix=(
                            f"Provide a list of values to "
                            f"'{node.get('test_id')}' so users can make a selection."
                        ),
                    )
                )
        return issues

    def _check_ungrouped_radio_buttons(
        self, flat: list[dict[str, Any]]
    ) -> list[UXIssue]:
        """Flag radio buttons not grouped with their peers in the same frame.

        Radio buttons for the same logical choice should be co-located.
        """
        issues: list[UXIssue] = []
        radio_types = {"CTkRadioButton", "TRadioButton", "Radiobutton"}
        parents: dict[str | None, list[dict[str, Any]]] = {}

        for node in flat:
            if node.get("widget_type", "") in radio_types:
                parent = node.get("parent_id")
                parents.setdefault(parent, []).append(node)

        for parent, radios in parents.items():
            if len(radios) == 1:
                node = radios[0]
                issues.append(
                    UXIssue(
                        rule_id="ungrouped_radio_button",
                        severity="medium",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Radio button '{node.get('test_id')}' is alone in "
                            f"its container. Radio buttons should be grouped "
                            f"with at least one peer."
                        ),
                        recommended_fix=(
                            f"Group '{node.get('test_id')}' with related radio "
                            f"buttons in the same frame, or convert to a checkbox "
                            f"if only one option exists."
                        ),
                    )
                )
        return issues

    def _check_no_primary_action(self, flat: list[dict[str, Any]]) -> list[UXIssue]:
        """Flag forms that have inputs but no visible submit/save button.

        A form without a clear primary action leaves users unsure how to proceed.
        """
        issues: list[UXIssue] = []
        has_entry = any(
            n.get("widget_type", "") in _ENTRY_TYPES for n in flat
        )
        if not has_entry:
            return issues

        primary_keywords = {
            "submit", "save", "confirm", "ok", "send", "apply",
            "continue", "login", "sign in", "register", "search",
            "create", "add", "update",
        }
        has_primary_btn = False
        for node in flat:
            if node.get("widget_type", "") not in _BUTTON_TYPES:
                continue
            text = (node.get("text") or "").lower().strip()
            if any(kw in text for kw in primary_keywords):
                has_primary_btn = True
                break

        if not has_primary_btn:
            issues.append(
                UXIssue(
                    rule_id="no_primary_action",
                    severity="high",
                    widget_id="<root>",
                    related_widget_id=None,
                    description=(
                        "The form contains input fields but no recognisable "
                        "primary action button (e.g. Submit, Save, OK). "
                        "Users may not know how to complete the form."
                    ),
                    recommended_fix=(
                        "Add a clearly labelled primary action button such as "
                        "'Submit', 'Save', or 'OK'."
                    ),
                )
            )
        return issues

    def _check_button_without_command(
        self, flat: list[dict[str, Any]]
    ) -> list[UXIssue]:
        """Flag buttons that have no command/callback bound.

        A button without a command does nothing when clicked.
        """
        issues: list[UXIssue] = []
        for node in flat:
            if node.get("widget_type", "") not in _BUTTON_TYPES:
                continue
            if not node.get("has_command", False):
                issues.append(
                    UXIssue(
                        rule_id="button_no_command",
                        severity="high",
                        widget_id=node.get("test_id", "unknown"),
                        related_widget_id=None,
                        description=(
                            f"Button '{node.get('test_id')}' has no command "
                            f"callback bound. Clicking it does nothing."
                        ),
                        recommended_fix=(
                            f"Bind a command callback to '{node.get('test_id')}' "
                            f"using the 'command' parameter."
                        ),
                    )
                )
        return issues

    def _check_deep_single_nesting(
        self, tree: dict[str, Any]
    ) -> list[UXIssue]:
        """Flag chains of single-child containers deeper than 2 levels.

        A→B→C where each has exactly one child is needless complexity.
        """
        issues: list[UXIssue] = []

        def _walk(node: dict[str, Any], single_depth: int, chain_start: str | None) -> None:
            children = node.get("children", [])
            wtype = node.get("widget_type", "")
            is_single_container = (
                wtype in _CONTAINER_TYPES
                and len(children) == 1
                and wtype not in ("CTk", "Tk", "Toplevel", "CTkToplevel",
                                  "CTkScrollableFrame", "CTkTabview")
            )
            if is_single_container:
                new_depth = single_depth + 1
                start = chain_start or node.get("test_id", "unknown")
                if new_depth >= 3:
                    issues.append(
                        UXIssue(
                            rule_id="deep_single_nesting",
                            severity="low",
                            widget_id=node.get("test_id", "unknown"),
                            related_widget_id=start,
                            description=(
                                f"Container '{node.get('test_id')}' is part of a "
                                f"chain of {new_depth} nested single-child containers "
                                f"starting from '{start}'. This adds complexity "
                                f"without benefit."
                            ),
                            recommended_fix=(
                                f"Flatten the container hierarchy by merging "
                                f"single-child containers in the chain starting "
                                f"from '{start}'."
                            ),
                        )
                    )
                for child in children:
                    _walk(child, new_depth, start)
            else:
                for child in children:
                    _walk(child, 0, None)

        _walk(tree, 0, None)
        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_casing(text: str) -> str:
        """Classify a text string's casing style.

        Returns one of: ``'Title Case'``, ``'UPPERCASE'``, ``'lowercase'``,
        ``'Sentence case'``, ``'Mixed'``.
        """
        if text.isupper():
            return "UPPERCASE"
        if text.islower():
            return "lowercase"
        if text == text.title():
            return "Title Case"
        words = text.split()
        if len(words) >= 1 and words[0][0].isupper() and all(
            w[0].islower() for w in words[1:] if w
        ):
            return "Sentence case"
        return "Mixed"

    @staticmethod
    def _flatten(node: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten a nested widget tree into a list of nodes."""
        result: list[dict[str, Any]] = []
        if not node:
            return result
        result.append({k: v for k, v in node.items() if k != "children"})
        for child in node.get("children", []):
            result.extend(UXAnalyzer._flatten(child))
        return result
