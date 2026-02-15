"""Sample test script that demonstrates the full validation pipeline.

This script:
1. Launches the sample application
2. Injects the test harness
3. Simulates user interactions
4. Runs the full analysis suite
5. Prints the JSON report to stdout
6. Saves the report to ``sample_report.json``

Usage::

    python -m examples.sample_test

Or from the project root::

    python examples/sample_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.core.runner import TestRunner
from customtkinter_validator.test_harness.event_simulator import EventSimulator
from examples.sample_app import create_app


def interaction_script(sim: EventSimulator) -> None:
    """Drive the sample application through a typical user flow.

    Args:
        sim: The event simulator.
    """
    sim.focus("name_entry")
    sim.type_text("name_entry", "Alice Johnson")

    sim.tab("name_entry")

    sim.focus("email_entry")
    sim.type_text("email_entry", "alice@example.com")

    sim.focus("password_entry")
    sim.type_text("password_entry", "SecureP@ss123")

    sim.click("agree_checkbox")

    sim.click("submit_btn")

    sim.click("reset_btn")

    sim.hover("close_btn")


def main() -> None:
    """Run the full validation pipeline and output the report."""
    config = ValidatorConfig(
        min_contrast_ratio_normal=4.5,
        min_touch_target_px=24,
        min_padding_px=4,
    )

    runner = TestRunner(config)

    output_path = Path(__file__).resolve().parent / "sample_report.json"

    print("=" * 60)
    print("  CustomTkinter Validator — Sample Test Run")
    print("=" * 60)
    print()

    report = runner.run_headless(
        app_factory=create_app,
        script=interaction_script,
        output_path=output_path,
    )

    runner.print_report(indent=2)

    print()
    print("-" * 60)
    print(f"Report saved to: {output_path}")
    print()

    summary = report.get("summary_score", {})
    print(f"  Layout score:        {summary.get('layout_score', 0):.1f} / 100")
    print(f"  Accessibility score: {summary.get('accessibility_score', 0):.1f} / 100")
    print(f"  Interaction score:   {summary.get('interaction_score', 0):.1f} / 100")
    print(f"  Overall score:       {summary.get('overall_score', 0):.1f} / 100")
    print()

    layout_count = len(report.get("layout_violations", []))
    contrast_count = len(report.get("contrast_issues", []))
    accessibility_count = len(report.get("accessibility_issues", []))
    interaction_count = len(report.get("interaction_results", []))
    print(f"  Layout violations:     {layout_count}")
    print(f"  Contrast issues:       {contrast_count}")
    print(f"  Accessibility issues:  {accessibility_count}")
    print(f"  Interactions recorded: {interaction_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
