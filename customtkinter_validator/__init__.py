"""CustomTkinter Validator - AI-native GUI testing and UX validation framework."""

__version__ = "2.0.1"
__author__ = "CustomTkinter Validator Team"

from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.core.runner import TestRunner
from customtkinter_validator.test_harness.event_simulator import EventSimulator
from customtkinter_validator.test_harness.injector import Injector
from customtkinter_validator.test_harness.widget_registry import WidgetRegistry
from customtkinter_validator.widgets.base import (
    TButton,
    TCheckBox,
    TEntry,
    TFrame,
    TLabel,
    TTextbox,
    TestableWidget,
)

__all__ = [
    "TestRunner",
    "ValidatorConfig",
    "TestableWidget",
    "TButton",
    "TLabel",
    "TEntry",
    "TFrame",
    "TCheckBox",
    "TTextbox",
    "WidgetRegistry",
    "Injector",
    "EventSimulator",
]
