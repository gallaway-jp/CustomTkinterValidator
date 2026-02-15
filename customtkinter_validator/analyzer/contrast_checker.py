"""WCAG 2.1 colour contrast analyser.

Computes relative luminance and contrast ratios for every text-bearing widget.
Flags violations against configurable thresholds aligned with WCAG AA/AAA
guidelines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from customtkinter_validator.core.config import ValidatorConfig


@dataclass(frozen=True)
class ContrastIssue:
    """A detected colour contrast violation.

    Attributes:
        rule_id: Machine-readable rule identifier.
        severity: ``"critical"``, ``"high"``, ``"medium"``, or ``"low"``.
        widget_id: The widget with the contrast issue.
        fg_color: Foreground colour as hex string.
        bg_color: Background colour as hex string.
        contrast_ratio: Computed contrast ratio.
        required_ratio: Minimum ratio required by the active rule.
        wcag_level: The WCAG level that was tested (``"AA"`` or ``"AAA"``).
        description: Human-readable explanation.
        recommended_fix: Suggested resolution.
    """

    rule_id: str
    severity: str
    widget_id: str
    fg_color: str
    bg_color: str
    contrast_ratio: float
    required_ratio: float
    wcag_level: str
    description: str
    recommended_fix: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dictionary.

        Returns:
            Plain dictionary.
        """
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "widget_id": self.widget_id,
            "fg_color": self.fg_color,
            "bg_color": self.bg_color,
            "contrast_ratio": round(self.contrast_ratio, 2),
            "required_ratio": self.required_ratio,
            "wcag_level": self.wcag_level,
            "description": self.description,
            "recommended_fix": self.recommended_fix,
        }


class ContrastChecker:
    """Checks colour contrast ratios using the WCAG 2.1 relative-luminance formula.

    The checker works on the flat widget-tree data produced by ``TreeExtractor``
    and does not require access to live widgets.
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        """Initialise the contrast checker.

        Args:
            config: Optional configuration overrides.
        """
        self._config = config or ValidatorConfig()

    def check(self, widget_tree: dict[str, Any]) -> list[ContrastIssue]:
        """Run contrast checks on every text-bearing widget in the tree.

        Args:
            widget_tree: Nested widget tree from ``TreeExtractor``.

        Returns:
            List of detected contrast issues.
        """
        flat = self._flatten(widget_tree)
        issues: list[ContrastIssue] = []

        for node in flat:
            text = node.get("text")
            if not text:
                continue

            fg = node.get("fg_color")
            bg = node.get("bg_color")
            if fg is None or bg is None:
                continue

            fg_rgb = self._hex_to_rgb(fg)
            bg_rgb = self._hex_to_rgb(bg)
            if fg_rgb is None or bg_rgb is None:
                continue

            ratio = self.contrast_ratio(fg_rgb, bg_rgb)
            is_large = self._is_large_text(node)
            required = (
                self._config.min_contrast_ratio_large
                if is_large
                else self._config.min_contrast_ratio_normal
            )

            if ratio < required:
                severity = "critical" if ratio < 2.0 else "high" if ratio < 3.0 else "medium"
                issues.append(
                    ContrastIssue(
                        rule_id="insufficient_contrast",
                        severity=severity,
                        widget_id=node.get("test_id", "unknown"),
                        fg_color=fg,
                        bg_color=bg,
                        contrast_ratio=ratio,
                        required_ratio=required,
                        wcag_level="AA",
                        description=(
                            f"'{node.get('test_id')}' has contrast ratio {ratio:.2f}:1 "
                            f"(required: {required}:1 for "
                            f"{'large' if is_large else 'normal'} text)"
                        ),
                        recommended_fix=(
                            f"Change the foreground colour of '{node.get('test_id')}' "
                            f"to achieve at least {required}:1 contrast against {bg}"
                        ),
                    )
                )
        return issues

    @staticmethod
    def contrast_ratio(
        color_a: tuple[int, int, int], color_b: tuple[int, int, int]
    ) -> float:
        """Compute the WCAG 2.1 contrast ratio between two sRGB colours.

        Args:
            color_a: ``(R, G, B)`` with values in 0–255.
            color_b: ``(R, G, B)`` with values in 0–255.

        Returns:
            Contrast ratio ≥ 1.0.
        """
        lum_a = ContrastChecker.relative_luminance(color_a)
        lum_b = ContrastChecker.relative_luminance(color_b)
        lighter = max(lum_a, lum_b)
        darker = min(lum_a, lum_b)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def relative_luminance(rgb: tuple[int, int, int]) -> float:
        """Compute the WCAG 2.1 relative luminance of an sRGB colour.

        Formula per WCAG 2.1 §1.4.3:
        - Linearise each channel: if C ≤ 0.04045, C_lin = C/12.92;
          otherwise C_lin = ((C + 0.055)/1.055)^2.4
        - L = 0.2126·R + 0.7152·G + 0.0722·B

        Args:
            rgb: ``(R, G, B)`` with values in 0–255.

        Returns:
            Relative luminance in [0, 1].
        """
        channels: list[float] = []
        for c in rgb:
            s = c / 255.0
            if s <= 0.04045:
                channels.append(s / 12.92)
            else:
                channels.append(((s + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    def _is_large_text(self, node: dict[str, Any]) -> bool:
        """Determine whether a widget's text qualifies as "large" per WCAG.

        Large text is ≥ 18pt, or ≥ 14pt and bold.

        Args:
            node: Widget metadata dictionary.

        Returns:
            ``True`` if the text is large.
        """
        size = node.get("font_size")
        if size is None:
            return False
        try:
            size = abs(int(size))
        except (ValueError, TypeError):
            return False

        weight = (node.get("font_weight") or "normal").lower()
        if size >= self._config.large_text_threshold_pt:
            return True
        if size >= self._config.large_text_bold_threshold_pt and weight == "bold":
            return True
        return False

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int] | None:
        """Parse a hex colour string to an ``(R, G, B)`` tuple.

        Supports ``#RGB``, ``#RRGGBB``, and ``#RRRGGGBBB`` formats.

        Args:
            hex_color: The hex colour string.

        Returns:
            ``(R, G, B)`` with values in 0–255, or ``None`` on failure.
        """
        color = hex_color.lstrip("#")
        try:
            if len(color) == 3:
                r = int(color[0] * 2, 16)
                g = int(color[1] * 2, 16)
                b = int(color[2] * 2, 16)
                return (r, g, b)
            if len(color) == 6:
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
                return (r, g, b)
            if len(color) == 9:
                r = int(color[0:3], 16) >> 4
                g = int(color[3:6], 16) >> 4
                b = int(color[6:9], 16) >> 4
                return (r, g, b)
        except ValueError:
            pass
        return None

    def _flatten(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten a nested widget tree into a list of nodes.

        Args:
            node: Tree root.

        Returns:
            Flat list of widget metadata dictionaries.
        """
        result: list[dict[str, Any]] = []
        if not node:
            return result
        node_copy = {k: v for k, v in node.items() if k != "children"}
        result.append(node_copy)
        for child in node.get("children", []):
            result.extend(self._flatten(child))
        return result
