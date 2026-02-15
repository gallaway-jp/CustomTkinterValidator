"""Widget registry: a deterministic, id-keyed store of live widget references.

The registry maps ``test_id`` strings to widget references and provides fast
lookup in both directions. It is the single source of truth for widget identity
during a test run.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Iterator


class WidgetRegistry:
    """Thread-safe, id-keyed registry for all discovered widgets.

    The registry enforces uniqueness of ``test_id`` values and provides O(1)
    lookups by id. It also supports reverse lookup (widget → id) via an
    identity-keyed secondary index.
    """

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._id_to_widget: dict[str, tk.Misc] = {}
        self._widget_id_to_test_id: dict[int, str] = {}

    def register(self, test_id: str, widget: tk.Misc) -> None:
        """Register a widget under a unique test_id.

        Args:
            test_id: Deterministic identifier for the widget.
            widget: The Tkinter or CustomTkinter widget instance.

        Raises:
            ValueError: If ``test_id`` is already registered to a different widget.
        """
        existing = self._id_to_widget.get(test_id)
        if existing is not None and existing is not widget:
            raise ValueError(
                f"Duplicate test_id '{test_id}': already registered to "
                f"{type(existing).__name__}"
            )
        self._id_to_widget[test_id] = widget
        self._widget_id_to_test_id[id(widget)] = test_id

    def get(self, test_id: str) -> tk.Misc | None:
        """Return the widget for a given test_id, or ``None`` if not found.

        Args:
            test_id: The identifier to look up.

        Returns:
            The widget, or ``None``.
        """
        return self._id_to_widget.get(test_id)

    def get_id(self, widget: Any) -> str | None:
        """Return the test_id for a given widget, or ``None`` if unregistered.

        Args:
            widget: The widget to look up.

        Returns:
            The test_id string, or ``None``.
        """
        return self._widget_id_to_test_id.get(id(widget))

    def contains(self, test_id: str) -> bool:
        """Check whether a test_id is registered.

        Args:
            test_id: The identifier to check.

        Returns:
            ``True`` if registered.
        """
        return test_id in self._id_to_widget

    def all_ids(self) -> list[str]:
        """Return a sorted list of all registered test_ids.

        Returns:
            Sorted list of test_id strings.
        """
        return sorted(self._id_to_widget.keys())

    def all_widgets(self) -> list[tuple[str, tk.Misc]]:
        """Return all (test_id, widget) pairs sorted by test_id.

        Returns:
            List of (test_id, widget) tuples.
        """
        return sorted(self._id_to_widget.items(), key=lambda pair: pair[0])

    def clear(self) -> None:
        """Remove all registrations."""
        self._id_to_widget.clear()
        self._widget_id_to_test_id.clear()

    def __len__(self) -> int:
        """Return the number of registered widgets."""
        return len(self._id_to_widget)

    def __iter__(self) -> Iterator[str]:
        """Iterate over registered test_ids."""
        return iter(self._id_to_widget)

    def __contains__(self, test_id: str) -> bool:
        """Support ``in`` operator for test_ids."""
        return self.contains(test_id)

    def unregister(self, test_id: str) -> bool:
        """Remove a widget registration by test_id.

        Args:
            test_id: The identifier to remove.

        Returns:
            ``True`` if the registration existed and was removed.
        """
        widget = self._id_to_widget.pop(test_id, None)
        if widget is not None:
            self._widget_id_to_test_id.pop(id(widget), None)
            return True
        return False
