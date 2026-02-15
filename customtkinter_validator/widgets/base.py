"""Base wrapper classes for CustomTkinter widgets that enforce deterministic test_id.

Every widget used in a testable application SHOULD use these wrappers to guarantee
a stable, unique test_id for introspection and event simulation. Widgets without
explicit test_ids will receive auto-generated ids during injection, but explicit
ids are preferred for test stability across code changes.
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk


class TestableWidget:
    """Mixin that adds a mandatory ``test_id`` to any CustomTkinter widget.

    The ``test_id`` serves as the sole deterministic identifier used by the
    test harness for widget lookup, event targeting, and report generation.
    It must be unique within the application widget tree.
    """

    _test_id: str

    def _init_test_id(self, test_id: str) -> None:
        """Validate and store the test_id.

        Args:
            test_id: A non-empty, unique string identifier for this widget.

        Raises:
            ValueError: If ``test_id`` is empty or not a string.
        """
        if not isinstance(test_id, str) or not test_id.strip():
            raise ValueError(
                f"{self.__class__.__name__} requires a non-empty string test_id, "
                f"got {test_id!r}"
            )
        self._test_id = test_id.strip()

    @property
    def test_id(self) -> str:
        """Return the deterministic test identifier for this widget."""
        return self._test_id


class TFrame(TestableWidget, ctk.CTkFrame):
    """Testable CTkFrame with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable frame.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkFrame arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TButton(TestableWidget, ctk.CTkButton):
    """Testable CTkButton with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable button.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkButton arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TLabel(TestableWidget, ctk.CTkLabel):
    """Testable CTkLabel with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable label.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkLabel arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TEntry(TestableWidget, ctk.CTkEntry):
    """Testable CTkEntry with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable entry.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkEntry arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TCheckBox(TestableWidget, ctk.CTkCheckBox):
    """Testable CTkCheckBox with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable checkbox.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkCheckBox arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TTextbox(TestableWidget, ctk.CTkTextbox):
    """Testable CTkTextbox with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable textbox.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkTextbox arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TSwitch(TestableWidget, ctk.CTkSwitch):
    """Testable CTkSwitch with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable switch.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkSwitch arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TRadioButton(TestableWidget, ctk.CTkRadioButton):
    """Testable CTkRadioButton with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable radio button.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkRadioButton arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TSlider(TestableWidget, ctk.CTkSlider):
    """Testable CTkSlider with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable slider.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkSlider arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TOptionMenu(TestableWidget, ctk.CTkOptionMenu):
    """Testable CTkOptionMenu with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable option menu.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkOptionMenu arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)


class TComboBox(TestableWidget, ctk.CTkComboBox):
    """Testable CTkComboBox with a mandatory ``test_id``."""

    def __init__(self, master: Any, *, test_id: str, **kwargs: Any) -> None:
        """Create a testable combobox.

        Args:
            master: Parent widget.
            test_id: Unique identifier for testing.
            **kwargs: Additional CTkComboBox arguments.
        """
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)
