"""Deterministic event simulation for CustomTkinter widgets.

All interactions use ``event_generate`` or direct widget methods to guarantee
deterministic, replayable behaviour. No coordinate-based clicking, no
``time.sleep``, no OS-level automation.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

from customtkinter_validator.test_harness.widget_registry import WidgetRegistry


class InteractionResult:
    """Captures the outcome of a simulated interaction.

    Attributes:
        action: The action name (e.g. ``"click"``, ``"type_text"``).
        widget_id: The test_id of the target widget.
        success: Whether the interaction completed without error.
        detail: Human-readable description of what happened.
        error: Error message if the interaction failed.
    """

    __slots__ = ("action", "widget_id", "success", "detail", "error")

    def __init__(
        self,
        action: str,
        widget_id: str,
        success: bool,
        detail: str,
        error: str | None = None,
    ) -> None:
        self.action = action
        self.widget_id = widget_id
        self.success = success
        self.detail = detail
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary.

        Returns:
            Dictionary representation suitable for JSON encoding.
        """
        result: dict[str, Any] = {
            "action": self.action,
            "widget_id": self.widget_id,
            "success": self.success,
            "detail": self.detail,
        }
        if self.error is not None:
            result["error"] = self.error
        return result


class EventSimulator:
    """Simulates user interactions against registered widgets.

    Every method resolves widgets by ``test_id`` through the registry and uses
    Tkinter's ``event_generate`` or equivalent deterministic widget methods.
    """

    def __init__(self, registry: WidgetRegistry) -> None:
        """Initialise the simulator.

        Args:
            registry: The widget registry for resolving test_ids.
        """
        self._registry = registry
        self._results: list[InteractionResult] = []

    @property
    def results(self) -> list[InteractionResult]:
        """Return all interaction results collected so far."""
        return list(self._results)

    def clear_results(self) -> None:
        """Discard all collected interaction results."""
        self._results.clear()

    def click(self, widget_id: str) -> InteractionResult:
        """Simulate a mouse click on the widget identified by *widget_id*.

        For CustomTkinter buttons this invokes the command directly via the
        internal canvas event bindings. For other widgets, ``<Button-1>`` and
        ``<ButtonRelease-1>`` events are generated.

        Args:
            widget_id: The test_id of the target widget.

        Returns:
            An ``InteractionResult`` describing the outcome.
        """
        widget = self._resolve(widget_id)
        if widget is None:
            return self._fail("click", widget_id, f"Widget '{widget_id}' not found in registry")

        try:
            state = self._get_state(widget)
            if state == "disabled":
                result = InteractionResult(
                    action="click",
                    widget_id=widget_id,
                    success=True,
                    detail=f"Click on '{widget_id}' ignored: widget is disabled",
                )
                self._results.append(result)
                return result

            target = self._get_event_target(widget)
            target.event_generate("<Enter>")
            target.event_generate("<Button-1>", x=5, y=5)
            target.event_generate("<ButtonRelease-1>", x=5, y=5)
            widget.update_idletasks()

            result = InteractionResult(
                action="click",
                widget_id=widget_id,
                success=True,
                detail=f"Clicked '{widget_id}' ({type(widget).__name__})",
            )
        except tk.TclError as exc:
            result = self._fail("click", widget_id, str(exc))

        self._results.append(result)
        return result

    def focus(self, widget_id: str) -> InteractionResult:
        """Move keyboard focus to the specified widget.

        Args:
            widget_id: The test_id of the target widget.

        Returns:
            An ``InteractionResult`` describing the outcome.
        """
        widget = self._resolve(widget_id)
        if widget is None:
            return self._fail("focus", widget_id, f"Widget '{widget_id}' not found in registry")

        try:
            target = self._get_event_target(widget)
            target.focus_set()
            widget.update_idletasks()
            result = InteractionResult(
                action="focus",
                widget_id=widget_id,
                success=True,
                detail=f"Focused '{widget_id}'",
            )
        except tk.TclError as exc:
            result = self._fail("focus", widget_id, str(exc))

        self._results.append(result)
        return result

    def type_text(self, widget_id: str, text: str) -> InteractionResult:
        """Type text into an entry or textbox widget.

        Focuses the widget first, then generates ``<Key>`` events for each
        character.

        Args:
            widget_id: The test_id of the target widget.
            text: The string to type.

        Returns:
            An ``InteractionResult`` describing the outcome.
        """
        widget = self._resolve(widget_id)
        if widget is None:
            return self._fail(
                "type_text", widget_id, f"Widget '{widget_id}' not found in registry"
            )

        try:
            state = self._get_state(widget)
            if state == "disabled":
                result = InteractionResult(
                    action="type_text",
                    widget_id=widget_id,
                    success=True,
                    detail=f"type_text on '{widget_id}' ignored: widget is disabled",
                )
                self._results.append(result)
                return result

            target = self._get_event_target(widget)
            target.focus_set()
            widget.update_idletasks()

            entry_widget = self._find_entry_child(widget)
            if entry_widget is not None:
                entry_widget.focus_set()
                for char in text:
                    entry_widget.event_generate("<Key>", keysym=char)
                entry_widget.insert(tk.END, text)
                widget.update_idletasks()
            else:
                for char in text:
                    target.event_generate("<Key>", keysym=char)
                if hasattr(widget, "insert"):
                    getattr(widget, "insert")(tk.END, text)
                widget.update_idletasks()

            result = InteractionResult(
                action="type_text",
                widget_id=widget_id,
                success=True,
                detail=f"Typed '{text}' into '{widget_id}'",
            )
        except tk.TclError as exc:
            result = self._fail("type_text", widget_id, str(exc))

        self._results.append(result)
        return result

    def tab(self, from_widget_id: str | None = None) -> InteractionResult:
        """Simulate a Tab key press to move focus to the next widget.

        If *from_widget_id* is provided, focus is moved from that widget.
        Otherwise, the currently focused widget is used.

        Args:
            from_widget_id: Optional test_id of the widget to tab away from.

        Returns:
            An ``InteractionResult`` describing the outcome.
        """
        source_id = from_widget_id or "<current_focus>"
        try:
            if from_widget_id:
                widget = self._resolve(from_widget_id)
                if widget is None:
                    return self._fail(
                        "tab", source_id, f"Widget '{from_widget_id}' not found"
                    )
                target = self._get_event_target(widget)
                target.focus_set()
                widget.update_idletasks()

            root = self._find_root()
            if root is None:
                return self._fail("tab", source_id, "Cannot determine root window")

            focused = root.focus_get()
            if focused is None:
                return self._fail("tab", source_id, "No widget currently has focus")

            focused.event_generate("<Tab>")
            root.update_idletasks()

            new_focused = root.focus_get()
            new_id = self._registry.get_id(new_focused) if new_focused else None

            result = InteractionResult(
                action="tab",
                widget_id=source_id,
                success=True,
                detail=f"Tabbed from '{source_id}' to '{new_id or 'unknown'}'",
            )
        except tk.TclError as exc:
            result = self._fail("tab", source_id, str(exc))

        self._results.append(result)
        return result

    def hover(self, widget_id: str) -> InteractionResult:
        """Simulate a mouse hover (Enter event) on a widget.

        Args:
            widget_id: The test_id of the target widget.

        Returns:
            An ``InteractionResult`` describing the outcome.
        """
        widget = self._resolve(widget_id)
        if widget is None:
            return self._fail("hover", widget_id, f"Widget '{widget_id}' not found in registry")

        try:
            target = self._get_event_target(widget)
            target.event_generate("<Enter>")
            widget.update_idletasks()
            result = InteractionResult(
                action="hover",
                widget_id=widget_id,
                success=True,
                detail=f"Hovered over '{widget_id}'",
            )
        except tk.TclError as exc:
            result = self._fail("hover", widget_id, str(exc))

        self._results.append(result)
        return result

    def _resolve(self, widget_id: str) -> tk.Misc | None:
        """Look up a widget by test_id.

        Args:
            widget_id: The test_id to look up.

        Returns:
            The widget or ``None``.
        """
        return self._registry.get(widget_id)

    def _fail(self, action: str, widget_id: str, error: str) -> InteractionResult:
        """Create a failed interaction result (does NOT auto-record).

        The caller is responsible for appending the result to ``_results``.

        Args:
            action: The action name.
            widget_id: The test_id of the target widget.
            error: The error description.

        Returns:
            The failure result.
        """
        return InteractionResult(
            action=action,
            widget_id=widget_id,
            success=False,
            detail=f"{action} on '{widget_id}' failed",
            error=error,
        )

    @staticmethod
    def _get_event_target(widget: tk.Misc) -> tk.Misc:
        """Return the inner widget that should receive low-level events.

        CustomTkinter widgets delegate rendering to an internal canvas. Events
        must target this canvas for bindings to fire.

        Args:
            widget: The outer widget.

        Returns:
            The canvas or the widget itself.
        """
        canvas = getattr(widget, "_canvas", None)
        if canvas is not None and isinstance(canvas, tk.BaseWidget):
            return canvas
        return widget

    @staticmethod
    def _find_entry_child(widget: tk.Misc) -> tk.Entry | None:
        """Find a Tk Entry child inside a CTk composite entry widget.

        Args:
            widget: The CTk entry widget.

        Returns:
            The internal ``tk.Entry`` or ``None``.
        """
        entry = getattr(widget, "_entry", None)
        if entry is not None and isinstance(entry, tk.Entry):
            return entry
        return None

    @staticmethod
    def _get_state(widget: tk.Misc) -> str:
        """Return the state of a widget as a lowercase string.

        Args:
            widget: The widget to inspect.

        Returns:
            ``"normal"``, ``"disabled"``, or ``"readonly"``.
        """
        try:
            raw = widget.cget("state")  # type: ignore[arg-type]
            if isinstance(raw, str):
                return raw.lower()
            return str(raw).lower()
        except (tk.TclError, AttributeError, ValueError):
            return "normal"

    def _find_root(self) -> tk.Misc | None:
        """Return the root window from the registry.

        Returns:
            The root widget, or ``None`` if the registry is empty.
        """
        for _, widget in self._registry.all_widgets():
            try:
                return widget.winfo_toplevel()
            except tk.TclError:
                continue
        return None
