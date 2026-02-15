"""Injector: walks a live CustomTkinter widget tree, assigns deterministic
test_ids, and populates the widget registry.

The injector is designed to hook into a running application without modifying
its source code. It performs a depth-first traversal starting from the root
window and registers every meaningful widget it finds.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.test_harness.widget_registry import WidgetRegistry


class Injector:
    """Injects into a live CustomTkinter application and catalogues all widgets.

    The injector traverses the widget tree, assigns deterministic ``test_id``
    values to any widget that does not already have one (via the ``TestableWidget``
    mixin), and registers every widget in the supplied ``WidgetRegistry``.
    """

    def __init__(self, registry: WidgetRegistry, config: ValidatorConfig | None = None) -> None:
        """Initialise the injector.

        Args:
            registry: The widget registry to populate.
            config: Optional configuration (uses defaults if ``None``).
        """
        self._registry = registry
        self._config = config or ValidatorConfig()
        self._auto_id_counters: dict[str, int] = {}

    def inject(self, root: tk.Misc) -> int:
        """Traverse the widget tree rooted at *root* and register all widgets.

        Call ``root.update_idletasks()`` before injection to ensure geometry
        is computed.

        Args:
            root: The root window (typically a ``customtkinter.CTk`` instance).

        Returns:
            The total number of widgets registered.
        """
        root.update_idletasks()
        self._auto_id_counters.clear()
        self._registry.clear()
        self._walk(root, depth=0)
        return len(self._registry)

    def _walk(self, widget: tk.Misc, depth: int) -> None:
        """Recursively walk the widget tree and register each widget.

        Only recurses into container widgets (frames, windows). Leaf widgets
        (buttons, labels, entries) are registered but their internal CTk
        sub-widgets (canvases, labels) are not traversed.

        Args:
            widget: Current widget being visited.
            depth: Current recursion depth (for safety limit).
        """
        if depth > self._config.max_tree_depth:
            return

        if not self._is_alive(widget):
            return

        test_id = self._resolve_test_id(widget)
        self._registry.register(test_id, widget)

        if self._is_container(widget):
            children = self._get_user_children(widget)
            for child in children:
                self._walk(child, depth + 1)

    def _resolve_test_id(self, widget: tk.Misc) -> str:
        """Return the test_id for a widget.

        Uses the explicit ``_test_id`` attribute if the widget is a
        ``TestableWidget``; otherwise generates a deterministic id based on
        the widget class name and its position among same-type siblings.

        Args:
            widget: The widget to identify.

        Returns:
            A stable, unique string identifier.
        """
        explicit_id: str | None = getattr(widget, "_test_id", None)
        if explicit_id:
            return explicit_id
        return self._generate_test_id(widget)

    def _generate_test_id(self, widget: tk.Misc) -> str:
        """Generate a deterministic test_id from the widget's tree position.

        The id is built by walking from the widget up to the root and encoding
        the class name plus the sibling index at each level.

        Args:
            widget: The widget to generate an id for.

        Returns:
            A hierarchical, dot-separated identifier.
        """
        parts: list[str] = []
        current: tk.Misc | None = widget
        while current is not None:
            class_name = type(current).__name__
            parent: Any = getattr(current, "master", None)
            if parent is None:
                parts.append(f"{class_name}_root")
                break
            idx = self._sibling_index(current, parent)
            parts.append(f"{class_name}_{idx}")
            current = parent
        parts.reverse()
        return ".".join(parts)

    @staticmethod
    def _sibling_index(widget: tk.Misc, parent: tk.Misc) -> int:
        """Return the index of *widget* among same-type siblings in *parent*.

        Args:
            widget: The child widget.
            parent: The parent widget.

        Returns:
            Zero-based index among siblings of the same class.
        """
        try:
            siblings = parent.winfo_children()
        except tk.TclError:
            return 0
        class_name = type(widget).__name__
        same_type = [s for s in siblings if type(s).__name__ == class_name]
        try:
            return same_type.index(widget)
        except ValueError:
            return 0

    def _get_user_children(self, widget: tk.Misc) -> list[tk.Misc]:
        """Return the user-added children of *widget*, excluding CTk internals.

        CustomTkinter composite widgets contain internal Tkinter primitives
        (canvases, labels, entries) that are implementation details. This method
        filters them out by checking against known internal attribute names.

        Args:
            widget: The parent widget.

        Returns:
            Filtered list of child widgets.
        """
        try:
            all_children = widget.winfo_children()
        except tk.TclError:
            return []

        internal_ids = self._collect_internal_widget_ids(widget)

        result: list[tk.Misc] = []
        for child in all_children:
            if id(child) in internal_ids:
                continue
            if not self._is_alive(child):
                continue
            result.append(child)
        return result

    def _collect_internal_widget_ids(self, widget: tk.Misc) -> set[int]:
        """Collect python id()s of widgets that are internal CTk implementation.

        Args:
            widget: The parent widget to inspect.

        Returns:
            Set of ``id()`` values for internal widgets.
        """
        internal: set[int] = set()
        for attr_name in self._config.internal_attr_names:
            obj = getattr(widget, attr_name, None)
            if obj is not None and isinstance(obj, tk.Misc):
                internal.add(id(obj))
        return internal

    @staticmethod
    def _is_alive(widget: tk.Misc) -> bool:
        """Check whether a widget still exists and has not been destroyed.

        Args:
            widget: The widget to check.

        Returns:
            ``True`` if the widget is alive.
        """
        try:
            return bool(widget.winfo_exists())
        except tk.TclError:
            return False

    def _is_container(self, widget: tk.Misc) -> bool:
        """Determine whether a widget is a container that holds user children.

        Only container widgets have their children recursively traversed.
        Leaf widgets (buttons, labels, entries) are registered but their
        internal CTk sub-widgets are not.

        Checks the widget's class name and all its base classes to support
        custom classes that inherit from container types.

        Args:
            widget: The widget to check.

        Returns:
            ``True`` if the widget is a container.
        """
        # Check the widget's class and all its base classes
        for cls in type(widget).__mro__:
            if cls.__name__ in self._config.container_widget_types:
                return True
        return False
