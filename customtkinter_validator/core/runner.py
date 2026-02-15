"""Test runner: orchestrates injection, analysis, simulation, and reporting.

The runner is the primary entry point for test scripts. It coordinates all
subsystems into a single, linear pipeline that produces a JSON report.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Any, Callable

from customtkinter_validator.analyzer.accessibility_checker import AccessibilityChecker
from customtkinter_validator.analyzer.consistency_checker import ConsistencyChecker
from customtkinter_validator.analyzer.contrast_checker import ContrastChecker
from customtkinter_validator.analyzer.layout_metrics import LayoutMetrics
from customtkinter_validator.analyzer.tree_extractor import TreeExtractor
from customtkinter_validator.analyzer.ux_analyzer import UXAnalyzer
from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.reporting.json_serializer import JsonSerializer
from customtkinter_validator.reporting.rule_engine import RuleEngine
from customtkinter_validator.test_harness.event_simulator import EventSimulator
from customtkinter_validator.test_harness.injector import Injector
from customtkinter_validator.test_harness.widget_registry import WidgetRegistry


class TestRunner:
    """Orchestrates the full validation pipeline for a CustomTkinter application.

    Typical usage::

        runner = TestRunner()
        runner.set_app(my_ctk_app)
        runner.inject()
        runner.simulate(lambda sim: [
            sim.type_text("name_entry", "Alice"),
            sim.click("submit_btn"),
        ])
        report = runner.analyse()
        runner.save_report("report.json")

    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        """Initialise the test runner.

        Args:
            config: Optional configuration overrides.
        """
        self._config = config or ValidatorConfig()
        self._registry = WidgetRegistry()
        self._injector = Injector(self._registry, self._config)
        self._simulator = EventSimulator(self._registry)
        self._tree_extractor = TreeExtractor(self._registry, self._config)
        self._layout_metrics = LayoutMetrics(self._config)
        self._contrast_checker = ContrastChecker(self._config)
        self._accessibility_checker = AccessibilityChecker(self._registry, self._config)
        self._ux_analyzer = UXAnalyzer(self._config)
        self._consistency_checker = ConsistencyChecker(self._config)
        self._rule_engine = RuleEngine(self._config)
        self._serializer = JsonSerializer(self._config)
        self._root: tk.Misc | None = None
        self._report: dict[str, Any] | None = None

    @property
    def registry(self) -> WidgetRegistry:
        """Return the widget registry."""
        return self._registry

    @property
    def simulator(self) -> EventSimulator:
        """Return the event simulator."""
        return self._simulator

    @property
    def rule_engine(self) -> RuleEngine:
        """Return the rule engine for custom rule registration."""
        return self._rule_engine

    @property
    def report(self) -> dict[str, Any] | None:
        """Return the most recent report, or ``None`` if not yet analysed."""
        return self._report

    def set_app(self, root: tk.Misc) -> None:
        """Attach the runner to a live application root widget.

        Args:
            root: The root window (typically ``customtkinter.CTk``).
        """
        self._root = root

    def inject(self) -> int:
        """Inject the harness into the attached application.

        Must be called after ``set_app``. Triggers ``update_idletasks()``
        and populates the widget registry.

        Returns:
            The number of widgets registered.

        Raises:
            RuntimeError: If no application has been attached.
        """
        if self._root is None:
            raise RuntimeError("No application attached. Call set_app() first.")
        return self._injector.inject(self._root)

    def simulate(
        self, script: Callable[[EventSimulator], Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run an interaction script against the live application.

        The *script* callable receives the ``EventSimulator`` and can call
        any of its methods (``click``, ``type_text``, ``tab``, etc.).

        Args:
            script: A callable that drives the event simulator. Pass ``None``
                to skip simulation.

        Returns:
            List of interaction result dictionaries.
        """
        if script is not None:
            script(self._simulator)
        return [r.to_dict() for r in self._simulator.results]

    def analyse(self) -> dict[str, Any]:
        """Run the full analysis pipeline and build the report.

        Performs tree extraction, layout checks, contrast checks,
        accessibility checks, rule evaluation, and score computation.

        Returns:
            The complete JSON-serialisable report dictionary.

        Raises:
            RuntimeError: If no application has been attached.
        """
        if self._root is None:
            raise RuntimeError("No application attached. Call set_app() first.")

        self._root.update_idletasks()

        widget_tree = self._tree_extractor.extract(self._root)
        layout_violations = self._layout_metrics.analyse(widget_tree)
        contrast_issues = self._contrast_checker.check(widget_tree)
        accessibility_issues = self._accessibility_checker.check(widget_tree)
        ux_issues = self._ux_analyzer.analyse(widget_tree)
        consistency_issues = self._consistency_checker.check(widget_tree)
        rule_violations = self._rule_engine.evaluate(widget_tree)
        tab_order = self._accessibility_checker.compute_tab_order()

        self._report = self._serializer.build_report(
            widget_tree=widget_tree,
            layout_violations=layout_violations,
            contrast_issues=contrast_issues,
            accessibility_issues=accessibility_issues,
            ux_issues=ux_issues,
            consistency_issues=consistency_issues,
            rule_violations=rule_violations,
            interaction_results=self._simulator.results,
            tab_order=tab_order,
        )
        return self._report

    def save_report(self, path: str | Path, indent: int = 2) -> Path:
        """Save the most recent report to a JSON file.

        Args:
            path: Destination file path.
            indent: JSON indentation level.

        Returns:
            The path of the written file.

        Raises:
            RuntimeError: If ``analyse()`` has not been called yet.
        """
        if self._report is None:
            raise RuntimeError("No report available. Call analyse() first.")
        return self._serializer.save(self._report, path, indent=indent)

    def print_report(self, indent: int = 2) -> None:
        """Print the most recent report to stdout.

        Args:
            indent: JSON indentation level.

        Raises:
            RuntimeError: If ``analyse()`` has not been called yet.
        """
        if self._report is None:
            raise RuntimeError("No report available. Call analyse() first.")
        print(self._serializer.serialise(self._report, indent=indent))

    def run_headless(
        self,
        app_factory: Callable[[], tk.Misc],
        script: Callable[[EventSimulator], Any] | None = None,
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Convenience method: create app, inject, simulate, analyse, save.

        This is the recommended entry point for CI/headless testing.

        Args:
            app_factory: A callable that creates and returns the root window.
                The factory MUST NOT call ``mainloop()``.
            script: Optional interaction script.
            output_path: Optional path to save the JSON report.

        Returns:
            The complete report dictionary.
        """
        root = app_factory()
        self.set_app(root)

        try:
            root.update_idletasks()
            root.update()
        except Exception:
            pass

        self.inject()

        if script is not None:
            self.simulate(script)

        report = self.analyse()

        if output_path is not None:
            self.save_report(output_path)

        try:
            root.destroy()
        except Exception:
            pass

        return report
