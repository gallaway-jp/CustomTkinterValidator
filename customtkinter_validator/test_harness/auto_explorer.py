"""Automatic GUI explorer: discovers and exercises all interactive widgets.

The ``AutoExplorer`` traverses the live widget tree, identifies every
interactive element, and systematically interacts with each one.  It
handles ``CTkTabview`` tab-switching so that widgets on every tab are
discovered and analysed.  No pre-written interaction script is required.

Exploration strategy:
1. Switch to each ``CTkTabview`` tab so hidden content becomes visible.
2. Type sample text into entry / textbox widgets.
3. Hover over buttons (buttons are not clicked to avoid triggering
   blocking callbacks such as file dialogs or network requests).
4. Toggle checkboxes and switches.
5. Select radio buttons.
6. Move sliders.
7. Walk the focus chain via Tab key.

After all interactions the caller can re-run analysis to capture issues
exposed by the state changes.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

from customtkinter_validator.test_harness.event_simulator import EventSimulator
from customtkinter_validator.test_harness.widget_registry import WidgetRegistry


# Widget type sets --------------------------------------------------------

_BUTTON_TYPES: set[str] = {"CTkButton", "TButton", "Button"}
_ENTRY_TYPES: set[str] = {"CTkEntry", "TEntry", "Entry"}
_TEXTBOX_TYPES: set[str] = {"CTkTextbox", "TTextbox", "Text"}
_CHECKBOX_TYPES: set[str] = {"CTkCheckBox", "TCheckBox", "Checkbutton"}
_SWITCH_TYPES: set[str] = {"CTkSwitch", "TSwitch"}
_RADIO_TYPES: set[str] = {"CTkRadioButton", "TRadioButton", "Radiobutton"}
_SLIDER_TYPES: set[str] = {"CTkSlider", "TSlider", "Scale"}
_OPTIONMENU_TYPES: set[str] = {"CTkOptionMenu", "TOptionMenu", "OptionMenu"}
_COMBOBOX_TYPES: set[str] = {"CTkComboBox", "TComboBox", "Combobox"}
_TABVIEW_TYPES: set[str] = {"CTkTabview"}

# Sample input used for entry/textbox exploration.
_SAMPLE_TEXT: str = "Test Input 123"


class AutoExplorer:
    """Automatically explores a live GUI by interacting with every widget.

    Usage::

        explorer = AutoExplorer(registry, simulator)
        explorer.explore(root)
        # explorer.results holds all interaction outcomes
    """

    def __init__(
        self,
        registry: WidgetRegistry,
        simulator: EventSimulator,
    ) -> None:
        self._registry = registry
        self._simulator = simulator
        self._visited_tabs: set[str] = set()
        self._interacted: set[str] = set()

    @property
    def results(self) -> list[dict[str, Any]]:
        """Return all interaction results from exploration."""
        return [r.to_dict() for r in self._simulator.results]

    def explore(self, root: tk.Misc) -> list[dict[str, Any]]:
        """Run the full auto-exploration sequence.

        Args:
            root: The application root window.

        Returns:
            List of interaction result dictionaries.
        """
        self._visited_tabs.clear()
        self._interacted.clear()
        self._simulator.clear_results()

        root.update_idletasks()

        # Phase 1: discover and switch all CTkTabview tabs so every tab's
        # content becomes visible (and re-injected if needed).
        self._explore_tabviews(root)

        # Phase 2: interact with every registered widget.
        self._interact_with_all()

        # Phase 3: walk the focus chain to test tab-order navigation.
        self._walk_focus_chain(root)

        return self.results

    # ------------------------------------------------------------------
    # Phase 1 — Tabview exploration
    # ------------------------------------------------------------------

    def _explore_tabviews(self, root: tk.Misc) -> None:
        """Find all CTkTabview widgets and click through every tab.

        After switching tabs, ``update_idletasks`` is called so that newly
        revealed widgets get their geometry computed.

        Args:
            root: The root window.
        """
        tabviews = self._find_widgets_by_type(root, _TABVIEW_TYPES)
        for tv in tabviews:
            self._switch_all_tabs(tv, root)

    @staticmethod
    def _find_widgets_by_type(
        root: tk.Misc,
        target_types: set[str],
    ) -> list[tk.Misc]:
        """Recursively find all widgets whose class name matches *target_types*."""
        found: list[tk.Misc] = []

        def _walk(widget: tk.Misc) -> None:
            if type(widget).__name__ in target_types:
                found.append(widget)
            try:
                for child in widget.winfo_children():
                    _walk(child)
            except tk.TclError:
                pass

        _walk(root)
        return found

    def _switch_all_tabs(self, tabview: tk.Misc, root: tk.Misc) -> None:
        """Click through every tab in a ``CTkTabview``.

        Uses the ``CTkTabview`` public API (``_segmented_button``, ``set``)
        to switch tabs reliably.

        Args:
            tabview: The CTkTabview widget.
            root: The root window (for ``update_idletasks``).
        """
        # CTkTabview stores tab names internally
        tab_names: list[str] | None = None

        # Try the public _tab_dict first (CTkTabview internal attribute)
        tab_dict = getattr(tabview, "_tab_dict", None)
        if tab_dict and isinstance(tab_dict, dict):
            tab_names = list(tab_dict.keys())

        # Fallback: try _name_list
        if not tab_names:
            name_list = getattr(tabview, "_name_list", None)
            if name_list and isinstance(name_list, (list, tuple)):
                tab_names = list(name_list)

        if not tab_names:
            return

        tv_id = self._registry.get_id(tabview) or "unknown_tabview"

        # Remember original tab so we can restore it
        original_tab: str | None = None
        get_method = getattr(tabview, "get", None)
        if callable(get_method):
            try:
                    original_tab = str(get_method())
            except Exception:
                pass

        for tab_name in tab_names:
            tab_key = f"{tv_id}::{tab_name}"
            if tab_key in self._visited_tabs:
                continue
            self._visited_tabs.add(tab_key)

            try:
                set_method = getattr(tabview, "set", None)
                if callable(set_method):
                    set_method(tab_name)
                    root.update_idletasks()

                    from customtkinter_validator.test_harness.event_simulator import (
                        InteractionResult,
                    )

                    self._simulator.add_result(
                        InteractionResult(
                            action="switch_tab",
                            widget_id=tv_id,
                            success=True,
                            detail=f"Switched '{tv_id}' to tab '{tab_name}'",
                        )
                    )
            except Exception:
                pass

        # Restore original tab
        if original_tab and original_tab in tab_names:
            try:
                set_method = getattr(tabview, "set", None)
                if callable(set_method):
                    set_method(original_tab)
                    root.update_idletasks()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Phase 2 — Interact with all registered widgets
    # ------------------------------------------------------------------

    def _interact_with_all(self) -> None:
        """Iterate over every registered widget and interact appropriately."""
        for test_id, widget in self._registry.all_widgets():
            if test_id in self._interacted:
                continue
            self._interact(test_id, widget)

    def _interact(self, test_id: str, widget: tk.Misc) -> None:
        """Interact with a single widget based on its type.

        Args:
            test_id: The widget's test_id.
            widget: The live widget.
        """
        self._interacted.add(test_id)
        wtype = type(widget).__name__

        try:
            state = self._get_state(widget)
            if state == "disabled":
                return
        except Exception:
            pass

        if wtype in _ENTRY_TYPES:
            self._explore_entry(test_id, widget)
        elif wtype in _TEXTBOX_TYPES:
            self._explore_textbox(test_id, widget)
        elif wtype in _BUTTON_TYPES:
            self._explore_button(test_id, widget)
        elif wtype in _CHECKBOX_TYPES:
            self._explore_checkbox(test_id, widget)
        elif wtype in _SWITCH_TYPES:
            self._explore_switch(test_id, widget)
        elif wtype in _RADIO_TYPES:
            self._explore_radio(test_id, widget)
        elif wtype in _SLIDER_TYPES:
            self._explore_slider(test_id, widget)
        elif wtype in _OPTIONMENU_TYPES:
            self._explore_optionmenu(test_id, widget)
        elif wtype in _COMBOBOX_TYPES:
            self._explore_combobox(test_id, widget)

    def _explore_entry(self, test_id: str, widget: tk.Misc) -> None:
        """Focus and type sample text into an entry."""
        self._simulator.focus(test_id)
        self._simulator.type_text(test_id, _SAMPLE_TEXT)

    def _explore_textbox(self, test_id: str, widget: tk.Misc) -> None:
        """Focus and type sample text into a textbox."""
        self._simulator.focus(test_id)
        self._simulator.type_text(test_id, _SAMPLE_TEXT)

    def _explore_button(self, test_id: str, widget: tk.Misc) -> None:
        """Focus and hover over a button without clicking.

        Buttons are not clicked during auto-exploration because their
        callbacks can trigger blocking operations (file dialogs, network
        requests, long computations) that would hang the explorer.
        Hovering still exercises hover-state styling and tooltip display.
        """
        self._simulator.hover(test_id)

    def _explore_checkbox(self, test_id: str, widget: tk.Misc) -> None:
        """Toggle a checkbox on and then off."""
        self._simulator.click(test_id)

    def _explore_switch(self, test_id: str, widget: tk.Misc) -> None:
        """Toggle a switch."""
        self._simulator.click(test_id)

    def _explore_radio(self, test_id: str, widget: tk.Misc) -> None:
        """Select a radio button."""
        self._simulator.click(test_id)

    def _explore_slider(self, test_id: str, widget: tk.Misc) -> None:
        """Move a slider to its midpoint."""
        self._simulator.hover(test_id)
        # Try setting the slider value to 50% of its range
        try:
            from_ = float(getattr(widget, "_from_", 0))
            to = float(getattr(widget, "_to", 1))
            mid = (from_ + to) / 2
            set_method = getattr(widget, "set", None)
            if callable(set_method):
                set_method(mid)
                widget.update_idletasks()
        except Exception:
            pass

    def _explore_optionmenu(self, test_id: str, widget: tk.Misc) -> None:
        """Select the first available option if there are values."""
        values = getattr(widget, "_values", None)
        if values and isinstance(values, (list, tuple)) and len(values) > 0:
            set_method = getattr(widget, "set", None)
            if callable(set_method):
                try:
                    set_method(values[0])
                    widget.update_idletasks()
                except Exception:
                    pass

    def _explore_combobox(self, test_id: str, widget: tk.Misc) -> None:
        """Select the first option and also type into the entry."""
        values = getattr(widget, "_values", None)
        if values and isinstance(values, (list, tuple)) and len(values) > 0:
            set_method = getattr(widget, "set", None)
            if callable(set_method):
                try:
                    set_method(values[0])
                    widget.update_idletasks()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Phase 3 — Focus chain walk
    # ------------------------------------------------------------------

    def _walk_focus_chain(self, root: tk.Misc, max_steps: int = 50) -> None:
        """Walk the focus chain by pressing Tab repeatedly.

        Stops after *max_steps* tabs or when focus cycles back to a
        previously visited widget.

        Args:
            root: The root window.
            max_steps: Maximum number of Tab presses.
        """
        try:
            # Focus the first focusable widget
            first_focusable = self._find_first_focusable(root)
            if first_focusable is None:
                return

            first_id = self._registry.get_id(first_focusable)
            if first_id:
                self._simulator.focus(first_id)

            visited_widgets: set[int] = set()
            current = root.focus_get()
            if current is not None:
                visited_widgets.add(id(current))

            for _ in range(max_steps):
                self._simulator.tab()
                current = root.focus_get()
                if current is None:
                    break
                wid = id(current)
                if wid in visited_widgets:
                    break  # Cycle detected — stop
                visited_widgets.add(wid)
        except tk.TclError:
            pass

    def _find_first_focusable(self, root: tk.Misc) -> tk.Misc | None:
        """Find the first focusable interactive widget in the tree.

        Args:
            root: The root window.

        Returns:
            The first focusable widget, or ``None``.
        """
        interactive_types = (
            _ENTRY_TYPES | _TEXTBOX_TYPES | _BUTTON_TYPES
            | _CHECKBOX_TYPES | _SWITCH_TYPES | _RADIO_TYPES
        )
        for _test_id, widget in self._registry.all_widgets():
            wtype = type(widget).__name__
            if wtype in interactive_types:
                state = self._get_state(widget)
                if state != "disabled":
                    return widget
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_state(widget: tk.Misc) -> str:
        """Return the widget state as a lowercase string."""
        try:
            raw = widget.cget("state")  # type: ignore[arg-type]
            if isinstance(raw, str):
                return raw.lower()
            return str(raw).lower()
        except (tk.TclError, AttributeError, ValueError):
            return "normal"

    @staticmethod
    def _get_text(widget: tk.Misc) -> str:
        """Return the text content of a widget, or empty string."""
        for attr in ("_text", "cget"):
            if attr == "cget":
                try:
                    return str(widget.cget("text"))  # type: ignore[arg-type]
                except (tk.TclError, AttributeError):
                    pass
            else:
                val = getattr(widget, attr, None)
                if isinstance(val, str):
                    return val
        return ""
