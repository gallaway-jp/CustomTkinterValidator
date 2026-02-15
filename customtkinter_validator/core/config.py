"""Validator configuration with sensible defaults for all thresholds and rules.

All numeric thresholds are configurable. The defaults follow WCAG 2.1 AA
guidelines where applicable and common desktop-UI heuristics elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=False)
class ValidatorConfig:
    """Central configuration for the validation framework.

    Attributes:
        min_contrast_ratio_normal: WCAG AA minimum contrast for normal text (4.5:1).
        min_contrast_ratio_large: WCAG AA minimum contrast for large text (3:1).
        large_text_threshold_pt: Font size in points above which text is "large".
        large_text_bold_threshold_pt: Bold font size threshold for "large" text.
        min_touch_target_px: Minimum interactive widget dimension in pixels.
        min_padding_px: Minimum padding between sibling widgets.
        overlap_tolerance_px: Pixel tolerance before flagging overlap.
        alignment_tolerance_px: Pixel tolerance for alignment consistency checks.
        symmetry_tolerance_px: Pixel tolerance for basic symmetry detection.
        score_weight_layout: Weight for layout score in overall score.
        score_weight_accessibility: Weight for accessibility score in overall score.
        score_weight_interaction: Weight for interaction score in overall score.
        severity_deductions: Points deducted per violation severity level.
        container_widget_types: Widget class names treated as containers for recursion.
        internal_attr_names: CTk internal attributes to exclude from child enumeration.
        appearance_mode: Force a specific appearance mode (None = auto-detect).
        max_tree_depth: Safety limit for recursive tree traversal.
    """

    min_contrast_ratio_normal: float = 4.5
    min_contrast_ratio_large: float = 3.0
    large_text_threshold_pt: int = 18
    large_text_bold_threshold_pt: int = 14
    min_touch_target_px: int = 24
    min_padding_px: int = 4
    overlap_tolerance_px: int = 0
    alignment_tolerance_px: int = 3
    symmetry_tolerance_px: int = 10
    score_weight_layout: float = 0.30
    score_weight_accessibility: float = 0.40
    score_weight_interaction: float = 0.30
    severity_deductions: dict[str, float] = field(
        default_factory=lambda: {
            "critical": 25.0,
            "high": 15.0,
            "medium": 10.0,
            "low": 5.0,
        }
    )
    container_widget_types: set[str] = field(
        default_factory=lambda: {
            "CTk",
            "CTkToplevel",
            "CTkFrame",
            "CTkScrollableFrame",
            "CTkTabview",
            "TFrame",
            "Frame",
            "LabelFrame",
            "Toplevel",
            "Tk",
        }
    )
    internal_attr_names: list[str] = field(
        default_factory=lambda: [
            "_canvas",
            "_text_label",
            "_entry",
            "_textbox",
            "_scrollbar",
            "_label",
            "_button",
            "_check_image_label",
            "_radio_image_label",
            "_switch_canvas",
            "_parent_frame",
            "_parent_canvas",
            "_slider",
            "_progressbar",
            "_fg_color",
        ]
    )
    appearance_mode: str | None = None
    max_tree_depth: int = 50

    def get_severity_deduction(self, severity: str) -> float:
        """Return the point deduction for a given severity level.

        Args:
            severity: One of 'critical', 'high', 'medium', 'low'.

        Returns:
            The deduction amount.
        """
        return self.severity_deductions.get(severity, 5.0)
