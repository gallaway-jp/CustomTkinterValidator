"""JSON report serialiser.

Compiles widget-tree data, violations, interaction results, and scores into
the canonical JSON output format designed for AI-agent consumption.
"""

from __future__ import annotations

import datetime
import json
import platform
from pathlib import Path
from typing import Any

from customtkinter_validator.analyzer.accessibility_checker import AccessibilityIssue
from customtkinter_validator.analyzer.consistency_checker import ConsistencyIssue
from customtkinter_validator.analyzer.contrast_checker import ContrastIssue
from customtkinter_validator.analyzer.layout_metrics import LayoutViolation
from customtkinter_validator.analyzer.ux_analyzer import UXIssue
from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.reporting.rule_engine import RuleViolation
from customtkinter_validator.test_harness.event_simulator import InteractionResult


class JsonSerializer:
    """Assembles and serialises the final validation report.

    The output follows the canonical schema:

    .. code-block:: json

        {
            "metadata": {...},
            "widget_tree": {...},
            "layout_violations": [...],
            "contrast_issues": [...],
            "accessibility_issues": [...],
            "interaction_results": [...],
            "summary_score": {
                "layout_score": float,
                "accessibility_score": float,
                "interaction_score": float,
                "overall_score": float
            }
        }
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        """Initialise the serialiser.

        Args:
            config: Optional configuration overrides.
        """
        self._config = config or ValidatorConfig()

    def build_report(
        self,
        widget_tree: dict[str, Any],
        layout_violations: list[LayoutViolation],
        contrast_issues: list[ContrastIssue],
        accessibility_issues: list[AccessibilityIssue],
        ux_issues: list[UXIssue],
        consistency_issues: list[ConsistencyIssue],
        rule_violations: list[RuleViolation],
        interaction_results: list[InteractionResult],
        tab_order: list[str],
    ) -> dict[str, Any]:
        """Build the complete report dictionary.

        Args:
            widget_tree: Nested widget metadata tree.
            layout_violations: Detected layout problems.
            contrast_issues: Detected contrast problems.
            accessibility_issues: Detected accessibility problems.
            ux_issues: Detected UX heuristic problems.
            consistency_issues: Detected visual consistency problems.
            rule_violations: Custom rule violations.
            interaction_results: Event simulation outcomes.
            tab_order: Computed keyboard tab order.

        Returns:
            The canonical report dictionary, ready for JSON serialisation.
        """
        layout_score = self._compute_category_score(
            [v.to_dict() for v in layout_violations]
            + [v.to_dict() for v in consistency_issues]
        )
        accessibility_score = self._compute_category_score(
            [v.to_dict() for v in contrast_issues]
            + [v.to_dict() for v in accessibility_issues]
        )
        ux_score = self._compute_category_score(
            [v.to_dict() for v in ux_issues]
            + [v.to_dict() for v in rule_violations]
        )
        interaction_score = self._compute_interaction_score(interaction_results)

        overall_score = (
            self._config.score_weight_layout * layout_score
            + self._config.score_weight_accessibility * accessibility_score
            + self._config.score_weight_interaction * interaction_score
        )
        # Adjust overall score by UX penalty
        ux_penalty = (100.0 - ux_score) * 0.15  # 15% weight for UX issues
        overall_score = max(0.0, overall_score - ux_penalty)

        return {
            "metadata": self._build_metadata(tab_order),
            "widget_tree": widget_tree,
            "layout_violations": [v.to_dict() for v in layout_violations],
            "contrast_issues": [v.to_dict() for v in contrast_issues],
            "accessibility_issues": (
                [v.to_dict() for v in accessibility_issues]
            ),
            "ux_issues": [v.to_dict() for v in ux_issues],
            "consistency_issues": [v.to_dict() for v in consistency_issues],
            "rule_violations": [v.to_dict() for v in rule_violations],
            "interaction_results": [r.to_dict() for r in interaction_results],
            "summary_score": {
                "layout_score": round(layout_score, 2),
                "accessibility_score": round(accessibility_score, 2),
                "ux_score": round(ux_score, 2),
                "interaction_score": round(interaction_score, 2),
                "overall_score": round(overall_score, 2),
            },
        }

    def serialise(self, report: dict[str, Any], indent: int = 2) -> str:
        """Serialise the report dictionary to a JSON string.

        Args:
            report: The report dictionary.
            indent: JSON indentation level.

        Returns:
            Formatted JSON string.
        """
        return json.dumps(report, indent=indent, default=str, ensure_ascii=False)

    def save(self, report: dict[str, Any], path: str | Path, indent: int = 2) -> Path:
        """Write the report to a JSON file.

        Args:
            report: The report dictionary.
            path: Destination file path.
            indent: JSON indentation level.

        Returns:
            The path of the written file.
        """
        filepath = Path(path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(self.serialise(report, indent=indent), encoding="utf-8")
        return filepath

    def _build_metadata(self, tab_order: list[str]) -> dict[str, Any]:
        """Build the metadata section of the report.

        Args:
            tab_order: Computed tab traversal order.

        Returns:
            Metadata dictionary.
        """
        return {
            "tool": "CustomTkinter Validator",
            "version": "2.0.0",
            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "tab_order": tab_order,
        }

    def _compute_category_score(
        self, violations: list[dict[str, Any]], max_score: float = 100.0
    ) -> float:
        """Compute a category score by deducting for each violation.

        Args:
            violations: List of violation dictionaries (must have ``severity``).
            max_score: Starting score.

        Returns:
            Score in [0, max_score].
        """
        deduction = sum(
            self._config.get_severity_deduction(v.get("severity", "low"))
            for v in violations
        )
        return max(0.0, min(max_score, max_score - deduction))

    @staticmethod
    def _compute_interaction_score(results: list[InteractionResult]) -> float:
        """Compute an interaction score from simulation results.

        The score is the percentage of successful interactions, or 100 if
        no interactions were performed.

        Args:
            results: List of interaction outcomes.

        Returns:
            Score in [0, 100].
        """
        if not results:
            return 100.0
        successes = sum(1 for r in results if r.success)
        return round((successes / len(results)) * 100.0, 2)
