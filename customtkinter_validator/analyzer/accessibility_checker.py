"""Accessibility analyser: checks focus chains, missing labels, disabled
primary actions, and unreachable focusable widgets.

All checks operate on introspected widget metadata — no screenshots or
coordinate-based testing.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Any

from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.test_harness.widget_registry import WidgetRegistry


@dataclass(frozen=True)
class AccessibilityIssue:
    """A detected accessibility problem.

    Attributes:
        rule_id: Machine-readable rule identifier.
        severity: ``"critical"``, ``"high"``, ``"medium"``, or ``"low"``.
        widget_id: The widget with the issue.
        description: Human-readable explanation.
        recommended_fix: Suggested resolution.
    """

    rule_id: str
    severity: str
    widget_id: str
    description: str
    recommended_fix: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dictionary.

        Returns:
            Plain dictionary.
        """
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "widget_id": self.widget_id,
            "description": self.description,
            "recommended_fix": self.recommended_fix,
        }


class AccessibilityChecker:
    """Evaluates the widget tree against accessibility heuristics.

    Checks include:
    - Missing labels for input widgets
    - Disabled primary action buttons
    - Unreachable focusable widgets (takefocus=False on interactive elements)
    - Focus/tab-order validation
    """

    ENTRY_TYPES: set[str] = {
        "CTkEntry", "CTkTextbox", "CTkComboBox",
        "TEntry", "TTextbox", "TComboBox",
        "Entry", "Text", "Combobox", "Spinbox",
    }

    BUTTON_TYPES: set[str] = {
        "CTkButton", "TButton", "Button",
    }

    INTERACTIVE_TYPES: set[str] = ENTRY_TYPES | BUTTON_TYPES | {
        "CTkCheckBox", "CTkSwitch", "CTkRadioButton", "CTkSlider",
        "CTkOptionMenu", "CTkSegmentedButton",
        "TCheckBox", "TSwitch", "TRadioButton", "TSlider", "TOptionMenu",
        "Checkbutton", "Radiobutton", "Scale",
    }

    def __init__(
        self,
        registry: WidgetRegistry,
        config: ValidatorConfig | None = None,
    ) -> None:
        """Initialise the accessibility checker.

        Args:
            registry: The widget registry for live widget access.
            config: Optional configuration overrides.
        """
        self._registry = registry
        self._config = config or ValidatorConfig()

    def check(self, widget_tree: dict[str, Any]) -> list[AccessibilityIssue]:
        """Run all accessibility checks.

        Args:
            widget_tree: Nested widget tree from ``TreeExtractor``.

        Returns:
            List of detected accessibility issues.
        """
        flat = self._flatten(widget_tree)
        issues: list[AccessibilityIssue] = []
        issues.extend(self._check_missing_labels(flat))
        issues.extend(self._check_disabled_primary_actions(flat))
        issues.extend(self._check_unreachable_focusables(flat))
        issues.extend(self._check_focus_chain())
        return issues

    def compute_tab_order(self) -> list[str]:
        """Compute the Tab traversal order.

        First tries Tk's native ``tk_focusNext()`` chain. If that yields no
        registered widgets, falls back to a geometry-based order (top-to-bottom,
        left-to-right) of all interactive, visible, enabled widgets.

        Returns:
            Ordered list of ``test_id`` values in tab order.
        """
        order = self._compute_tk_tab_order()
        if order:
            return order
        return self._compute_geometry_tab_order()

    def _compute_tk_tab_order(self) -> list[str]:
        """Attempt to compute the tab order using tk_focusNext().

        Returns:
            Ordered list of test_ids, or empty list on failure.
        """
        root = self._find_root()
        if root is None:
            return []

        try:
            root.update_idletasks()
        except tk.TclError:
            pass

        visited: list[str] = []
        visited_ids: set[int] = set()

        first = self._first_focusable(root)
        if first is None:
            return []

        current = first
        while current is not None:  # type: ignore[redundant-expr]
            wid = id(current)
            if wid in visited_ids:
                break
            visited_ids.add(wid)
            test_id = self._registry.get_id(current)
            if test_id is not None:
                visited.append(test_id)
            try:
                nxt = current.tk_focusNext()
                if nxt is current or nxt is None:
                    break
                current = nxt
            except tk.TclError:
                break
        return visited

    def _compute_geometry_tab_order(self) -> list[str]:
        """Compute tab order from widget geometry: top-to-bottom, left-to-right.

        Returns:
            Ordered list of test_ids for interactive widgets.
        """
        interactive_widgets: list[tuple[int, int, str]] = []
        for test_id, widget in self._registry.all_widgets():
            wtype = type(widget).__name__
            if wtype not in self.INTERACTIVE_TYPES:
                continue
            try:
                if not widget.winfo_viewable():
                    continue
                abs_y = widget.winfo_rooty()
                abs_x = widget.winfo_rootx()
                interactive_widgets.append((abs_y, abs_x, test_id))
            except tk.TclError:
                continue
        interactive_widgets.sort()
        return [tid for _, _, tid in interactive_widgets]

    def _check_missing_labels(self, flat: list[dict[str, Any]]) -> list[AccessibilityIssue]:
        """Detect entry widgets without an associated label.

        An entry is considered labelled if a label widget shares the same
        parent container **and** can be paired 1-to-1 with that entry.
        When there are more entry widgets than labels in a container, the
        excess entries are flagged.  If there are zero labels the entry is
        always flagged.

        Args:
            flat: Flat list of widget metadata.

        Returns:
            List of missing-label issues.
        """
        issues: list[AccessibilityIssue] = []

        # Group labels and entries by parent
        labels_by_parent: dict[str | None, list[dict[str, Any]]] = {}
        entries_by_parent: dict[str | None, list[dict[str, Any]]] = {}

        for node in flat:
            wtype = node.get("widget_type", "")
            parent = node.get("parent_id")
            if "Label" in wtype and node.get("text"):
                labels_by_parent.setdefault(parent, []).append(node)
            if wtype in self.ENTRY_TYPES:
                entries_by_parent.setdefault(parent, []).append(node)

        for parent, entries in entries_by_parent.items():
            labels = labels_by_parent.get(parent, [])
            if len(labels) >= len(entries):
                # Enough labels for every entry — assume all are labelled
                continue
            # Not enough labels — flag the unmatched entries.
            # Pair by tree order: first N entries are considered labelled.
            unmatched = entries[len(labels):]
            for entry_node in unmatched:
                issues.append(
                    AccessibilityIssue(
                        rule_id="missing_label",
                        severity="high",
                        widget_id=entry_node.get("test_id", "unknown"),
                        description=(
                            f"Entry widget '{entry_node.get('test_id')}' has no "
                            f"associated label in the same parent container "
                            f"({len(labels)} label(s) for {len(entries)} entry/entries)"
                        ),
                        recommended_fix=(
                            f"Add a descriptive label widget as a sibling of "
                            f"'{entry_node.get('test_id')}' in its parent container"
                        ),
                    )
                )
        return issues

    def _check_disabled_primary_actions(
        self, flat: list[dict[str, Any]]
    ) -> list[AccessibilityIssue]:
        """Detect buttons that appear to be primary actions but are disabled.

        A button is considered a primary action if its text contains common
        action verbs (submit, save, confirm, login, sign in, ok, send).

        Args:
            flat: Flat list of widget metadata.

        Returns:
            List of disabled-primary-action issues.
        """
        issues: list[AccessibilityIssue] = []
        primary_keywords = {
            "submit", "save", "confirm", "login", "sign in",
            "register", "ok", "send", "apply", "continue",
            "reset", "delete", "remove", "cancel",
        }

        for node in flat:
            wtype = node.get("widget_type", "")
            if wtype not in self.BUTTON_TYPES:
                continue
            if node.get("enabled", True):
                continue
            text = (node.get("text") or "").lower().strip()
            if any(keyword in text for keyword in primary_keywords):
                issues.append(
                    AccessibilityIssue(
                        rule_id="disabled_primary_action",
                        severity="medium",
                        widget_id=node.get("test_id", "unknown"),
                        description=(
                            f"Primary action button '{node.get('test_id')}' "
                            f"(text: '{node.get('text')}') is disabled"
                        ),
                        recommended_fix=(
                            f"Ensure '{node.get('test_id')}' is enabled when the "
                            f"user can reasonably invoke the action, or provide "
                            f"inline guidance explaining what is needed"
                        ),
                    )
                )
        return issues

    def _check_unreachable_focusables(
        self, flat: list[dict[str, Any]]
    ) -> list[AccessibilityIssue]:
        """Detect interactive widgets that cannot receive keyboard focus.

        Checks the live ``takefocus`` property of each interactive widget.

        Args:
            flat: Flat list of widget metadata.

        Returns:
            List of unreachable-widget issues.
        """
        issues: list[AccessibilityIssue] = []
        tab_order = set(self.compute_tab_order())

        for node in flat:
            wtype = node.get("widget_type", "")
            if wtype not in self.INTERACTIVE_TYPES:
                continue
            if not node.get("visibility", True):
                continue
            test_id = node.get("test_id", "unknown")
            widget = self._registry.get(test_id)
            if widget is None:
                continue

            takefocus = self._get_takefocus(widget)
            if takefocus is False or (takefocus == 0):
                issues.append(
                    AccessibilityIssue(
                        rule_id="unreachable_focusable",
                        severity="high",
                        widget_id=test_id,
                        description=(
                            f"Interactive widget '{test_id}' has takefocus disabled "
                            f"and cannot be reached via keyboard navigation"
                        ),
                        recommended_fix=(
                            f"Set takefocus=True on '{test_id}' or provide an "
                            f"alternative keyboard-accessible way to interact with it"
                        ),
                    )
                )
            elif test_id not in tab_order and node.get("enabled", True):
                issues.append(
                    AccessibilityIssue(
                        rule_id="unreachable_focusable",
                        severity="medium",
                        widget_id=test_id,
                        description=(
                            f"Interactive widget '{test_id}' is not reachable in "
                            f"the computed tab order"
                        ),
                        recommended_fix=(
                            f"Review the focus chain to ensure '{test_id}' is "
                            f"included in the keyboard navigation order"
                        ),
                    )
                )
        return issues

    def _check_focus_chain(self) -> list[AccessibilityIssue]:
        """Validate the focus chain for logical ordering.

        Currently checks that the focus chain is non-empty and that all
        interactive widgets are represented.

        Returns:
            List of focus-chain issues.
        """
        issues: list[AccessibilityIssue] = []
        tab_order = self.compute_tab_order()

        if not tab_order:
            issues.append(
                AccessibilityIssue(
                    rule_id="empty_focus_chain",
                    severity="critical",
                    widget_id="<root>",
                    description="No focus chain could be computed for the application",
                    recommended_fix=(
                        "Ensure at least one interactive widget exists and is "
                        "focusable via keyboard"
                    ),
                )
            )
        return issues

    def _find_root(self) -> tk.Misc | None:
        """Locate the root window via the registry.

        Returns:
            The root (toplevel) widget, or ``None``.
        """
        for _, widget in self._registry.all_widgets():
            try:
                return widget.winfo_toplevel()
            except tk.TclError:
                continue
        return None

    def _first_focusable(self, root: tk.Misc) -> tk.Misc | None:
        """Find the first focusable widget starting from *root*.

        Args:
            root: The root widget.

        Returns:
            The first focusable widget, or ``None``.
        """
        try:
            return root.tk_focusNext()
        except tk.TclError:
            return None

    @staticmethod
    def _get_takefocus(widget: tk.Misc) -> Any:
        """Read the ``takefocus`` property of a widget.

        Args:
            widget: The widget to inspect.

        Returns:
            The takefocus value (bool-like or callable), or ``True`` as default.
        """
        try:
            val = widget.cget("takefocus")  # type: ignore[arg-type]
            if isinstance(val, str):
                if val.lower() in ("0", "false", "no"):
                    return False
                if val.lower() in ("1", "true", "yes", ""):
                    return True
            return val
        except (tk.TclError, AttributeError, ValueError):
            # CTk widgets don't expose takefocus via cget; check the
            # underlying Tk canvas instead.
            canvas = getattr(widget, "_canvas", None)
            if canvas is not None:
                try:
                    val = canvas.cget("takefocus")
                    if isinstance(val, str) and val.lower() in ("0", "false", "no"):
                        return False
                except (tk.TclError, AttributeError):
                    pass
            return True

    def _flatten(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten a nested widget tree.

        Args:
            node: Tree root.

        Returns:
            Flat list.
        """
        result: list[dict[str, Any]] = []
        if not node:
            return result
        result.append({k: v for k, v in node.items() if k != "children"})
        for child in node.get("children", []):
            result.extend(self._flatten(child))
        return result
