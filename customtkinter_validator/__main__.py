"""Command-line interface for the CustomTkinter Validator.

Usage::

    python -m customtkinter_validator --app examples.sample_app --output report.json

"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.core.runner import TestRunner


def main() -> None:
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="ctk-validator",
        description="AI-native GUI testing and UX validation for CustomTkinter apps",
    )
    parser.add_argument(
        "--app",
        required=True,
        help=(
            "Dotted module path to the application module. "
            "The module must expose a create_app() function that returns "
            "the root CTk window (without calling mainloop)."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        default="report.json",
        help="Output path for the JSON report (default: report.json)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2)",
    )
    parser.add_argument(
        "--min-contrast",
        type=float,
        default=None,
        help="Override minimum contrast ratio for normal text",
    )
    parser.add_argument(
        "--min-touch-target",
        type=int,
        default=None,
        help="Override minimum touch target size in pixels",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_report",
        help="Print the report to stdout in addition to saving",
    )
    parser.add_argument(
        "--auto-explore",
        action="store_true",
        default=False,
        help=(
            "Automatically discover and interact with every widget "
            "(no interaction script required)"
        ),
    )

    args = parser.parse_args()

    config = ValidatorConfig()
    if args.min_contrast is not None:
        config.min_contrast_ratio_normal = args.min_contrast
    if args.min_touch_target is not None:
        config.min_touch_target_px = args.min_touch_target

    try:
        module = importlib.import_module(args.app)
    except ModuleNotFoundError as exc:
        print(f"Error: cannot import module '{args.app}': {exc}", file=sys.stderr)
        sys.exit(1)

    create_app = getattr(module, "create_app", None)
    if create_app is None:
        print(
            f"Error: module '{args.app}' does not expose a create_app() function",
            file=sys.stderr,
        )
        sys.exit(1)

    runner = TestRunner(config)
    report = runner.run_headless(
        app_factory=create_app,
        output_path=args.output,
        auto_explore=args.auto_explore,
    )

    if args.print_report:
        runner.print_report(indent=args.indent)

    output_path = Path(args.output)
    total_issues = (
        len(report.get("layout_violations", []))
        + len(report.get("contrast_issues", []))
        + len(report.get("accessibility_issues", []))
    )
    overall = report.get("summary_score", {}).get("overall_score", 0)
    print(f"Report saved to {output_path.resolve()}")
    print(f"Total issues found: {total_issues}")
    print(f"Overall score: {overall:.1f}/100")


if __name__ == "__main__":
    main()
