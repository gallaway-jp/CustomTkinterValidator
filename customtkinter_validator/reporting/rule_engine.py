"""Rule engine: configurable, severity-tagged validation rules.

Rules are pure functions that accept a widget-tree dictionary and return a list
of violations. The engine aggregates results from all active rules and computes
a normalised quality score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from customtkinter_validator.core.config import ValidatorConfig


@dataclass(frozen=True)
class RuleViolation:
    """A single violation produced by a rule.

    Attributes:
        rule_id: Machine-readable identifier.
        severity: ``"critical"``, ``"high"``, ``"medium"``, or ``"low"``.
        widget_id: The widget involved.
        description: Human-readable explanation.
        recommended_fix: Suggested resolution.
    """

    rule_id: str
    severity: str
    widget_id: str
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
            "description": self.description,
            "recommended_fix": self.recommended_fix,
        }


RuleFunction = Callable[[dict[str, Any]], list[RuleViolation]]


@dataclass
class Rule:
    """A named, configurable validation rule.

    Attributes:
        rule_id: Unique identifier for the rule.
        name: Human-readable name.
        description: What the rule checks.
        enabled: Whether the rule is active.
        check: The rule function.
    """

    rule_id: str
    name: str
    description: str
    enabled: bool
    check: RuleFunction


class RuleEngine:
    """Evaluates a set of configurable rules against the widget tree.

    The engine maintains a list of rules, runs each active rule, collects
    violations, and computes a normalised quality score.
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        """Initialise the rule engine.

        Args:
            config: Optional configuration overrides.
        """
        self._config = config or ValidatorConfig()
        self._rules: list[Rule] = []
        self._register_builtin_rules()

    @property
    def rules(self) -> list[Rule]:
        """Return all registered rules."""
        return list(self._rules)

    def add_rule(self, rule: Rule) -> None:
        """Register a custom rule.

        Args:
            rule: The rule to add.
        """
        self._rules.append(rule)

    def enable_rule(self, rule_id: str) -> None:
        """Enable a rule by its id.

        Args:
            rule_id: The identifier of the rule to enable.
        """
        for rule in self._rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                return

    def disable_rule(self, rule_id: str) -> None:
        """Disable a rule by its id.

        Args:
            rule_id: The identifier of the rule to disable.
        """
        for rule in self._rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                return

    def evaluate(self, widget_tree: dict[str, Any]) -> list[RuleViolation]:
        """Run all enabled rules and collect violations.

        Args:
            widget_tree: Nested widget tree from ``TreeExtractor``.

        Returns:
            Aggregated list of violations from all rules.
        """
        violations: list[RuleViolation] = []
        for rule in self._rules:
            if rule.enabled:
                violations.extend(rule.check(widget_tree))
        return violations

    def compute_score(self, violations: list[RuleViolation], max_score: float = 100.0) -> float:
        """Compute a normalised quality score from violations.

        Deducts points per violation based on severity. The score is clamped
        to [0, max_score].

        Args:
            violations: List of rule violations.
            max_score: Starting score.

        Returns:
            Normalised score in [0, max_score].
        """
        total_deduction = sum(
            self._config.get_severity_deduction(v.severity) for v in violations
        )
        return max(0.0, min(max_score, max_score - total_deduction))

    def _register_builtin_rules(self) -> None:
        """Register the default set of built-in validation rules."""
        self._rules.extend([
            Rule(
                rule_id="hidden_interactive",
                name="Hidden Interactive Widget",
                description="Interactive widgets should be visible to the user",
                enabled=True,
                check=self._rule_hidden_interactive,
            ),
            Rule(
                rule_id="empty_text_button",
                name="Empty Text Button",
                description="Buttons should have descriptive text",
                enabled=True,
                check=self._rule_empty_text_button,
            ),
            Rule(
                rule_id="excessive_nesting",
                name="Excessive Nesting",
                description="Widget tree should not be excessively deep",
                enabled=True,
                check=self._rule_excessive_nesting,
            ),
            Rule(
                rule_id="zero_dimension_widget",
                name="Zero-Dimension Widget",
                description="Visible widgets should have non-zero dimensions",
                enabled=True,
                check=self._rule_zero_dimension,
            ),
            Rule(
                rule_id="disabled_without_reason",
                name="Disabled Without Nearby Explanation",
                description="Disabled widgets should have nearby text explaining why",
                enabled=True,
                check=self._rule_disabled_without_reason,
            ),
            Rule(
                rule_id="text_content_quality",
                name="Text Content Quality",
                description="Labels and buttons should have meaningful text",
                enabled=True,
                check=self._rule_text_content_quality,
            ),
        ])

    @staticmethod
    def _flatten(node: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten a nested tree into a list.

        Args:
            node: Tree root.

        Returns:
            Flat list.
        """
        result: list[dict[str, Any]] = []
        if not node:
            return result
        result.append({k: v for k, v in node.items() if k != "children"})
        for child in node.get("children", []):
            result.extend(RuleEngine._flatten(child))
        return result

    @staticmethod
    def _rule_hidden_interactive(tree: dict[str, Any]) -> list[RuleViolation]:
        """Flag interactive widgets that are not visible.

        Args:
            tree: Widget tree.

        Returns:
            Violations.
        """
        interactive = {
            "CTkButton", "CTkEntry", "CTkCheckBox", "CTkSwitch",
            "CTkRadioButton", "CTkSlider", "CTkOptionMenu", "CTkComboBox",
            "CTkTextbox", "TButton", "TEntry", "TCheckBox",
            "Button", "Entry", "Checkbutton",
        }
        violations: list[RuleViolation] = []
        for node in RuleEngine._flatten(tree):
            wtype = node.get("widget_type", "")
            if wtype in interactive and not node.get("visibility", True):
                violations.append(
                    RuleViolation(
                        rule_id="hidden_interactive",
                        severity="high",
                        widget_id=node.get("test_id", "unknown"),
                        description=(
                            f"Interactive widget '{node.get('test_id')}' "
                            f"({wtype}) is not visible"
                        ),
                        recommended_fix=(
                            f"Make '{node.get('test_id')}' visible or remove it "
                            f"if it is not needed"
                        ),
                    )
                )
        return violations

    @staticmethod
    def _rule_empty_text_button(tree: dict[str, Any]) -> list[RuleViolation]:
        """Flag buttons without descriptive text.

        Args:
            tree: Widget tree.

        Returns:
            Violations.
        """
        button_types = {"CTkButton", "TButton", "Button"}
        violations: list[RuleViolation] = []
        for node in RuleEngine._flatten(tree):
            wtype = node.get("widget_type", "")
            if wtype in button_types:
                text = (node.get("text") or "").strip()
                if not text:
                    violations.append(
                        RuleViolation(
                            rule_id="empty_text_button",
                            severity="medium",
                            widget_id=node.get("test_id", "unknown"),
                            description=(
                                f"Button '{node.get('test_id')}' has no text label"
                            ),
                            recommended_fix=(
                                f"Add descriptive text to '{node.get('test_id')}' "
                                f"so users understand its purpose"
                            ),
                        )
                    )
        return violations

    @staticmethod
    def _rule_excessive_nesting(tree: dict[str, Any]) -> list[RuleViolation]:
        """Flag widgets at excessive nesting depth (>10 levels).

        Args:
            tree: Widget tree.

        Returns:
            Violations.
        """
        violations: list[RuleViolation] = []

        def walk(node: dict[str, Any], depth: int) -> None:
            if depth > 10 and node.get("widget_type") not in ("CTk", "Tk"):
                violations.append(
                    RuleViolation(
                        rule_id="excessive_nesting",
                        severity="low",
                        widget_id=node.get("test_id", "unknown"),
                        description=(
                            f"Widget '{node.get('test_id')}' is at nesting "
                            f"depth {depth}, which may indicate overly complex layout"
                        ),
                        recommended_fix=(
                            f"Simplify the widget hierarchy around "
                            f"'{node.get('test_id')}'"
                        ),
                    )
                )
            for child in node.get("children", []):
                walk(child, depth + 1)

        walk(tree, 0)
        return violations

    @staticmethod
    def _rule_zero_dimension(tree: dict[str, Any]) -> list[RuleViolation]:
        """Flag visible widgets with zero width or height.

        Args:
            tree: Widget tree.

        Returns:
            Violations.
        """
        violations: list[RuleViolation] = []
        for node in RuleEngine._flatten(tree):
            if not node.get("visibility", True):
                continue
            w = node.get("width", 0)
            h = node.get("height", 0)
            if w == 0 or h == 0:
                wtype = node.get("widget_type", "")
                if wtype in ("CTk", "Tk", "Toplevel"):
                    continue
                violations.append(
                    RuleViolation(
                        rule_id="zero_dimension_widget",
                        severity="medium",
                        widget_id=node.get("test_id", "unknown"),
                        description=(
                            f"Widget '{node.get('test_id')}' has dimensions "
                            f"{w}x{h}px — it may not be rendered"
                        ),
                        recommended_fix=(
                            f"Ensure '{node.get('test_id')}' has a size set "
                            f"either explicitly or via its layout manager"
                        ),
                    )
                )
        return violations

    @staticmethod
    def _rule_disabled_without_reason(tree: dict[str, Any]) -> list[RuleViolation]:
        """Flag disabled widgets with no nearby explanatory text.

        When a widget is disabled, there should be a visible label or
        tooltip explaining why.

        Args:
            tree: Widget tree.

        Returns:
            Violations.
        """
        interactive = {
            "CTkButton", "CTkEntry", "CTkCheckBox", "CTkSwitch",
            "CTkRadioButton", "CTkSlider", "CTkOptionMenu", "CTkComboBox",
            "TButton", "TEntry", "TCheckBox",
            "Button", "Entry", "Checkbutton",
        }
        label_types = {"CTkLabel", "TLabel", "Label"}
        violations: list[RuleViolation] = []

        flat = RuleEngine._flatten(tree)
        # Collect labels by parent
        labels_by_parent: dict[str | None, list[str]] = {}
        for node in flat:
            if node.get("widget_type", "") in label_types:
                text = (node.get("text") or "").lower()
                parent = node.get("parent_id")
                labels_by_parent.setdefault(parent, []).append(text)

        for node in flat:
            wtype = node.get("widget_type", "")
            if wtype not in interactive:
                continue
            if node.get("enabled", True):
                continue
            # Check if any sibling label mentions disabled/unavailable/required/etc.
            parent = node.get("parent_id")
            sibling_labels = labels_by_parent.get(parent, [])
            hint_keywords = {
                "disabled", "unavailable", "locked", "required",
                "must", "need", "first", "before", "not available",
            }
            has_explanation = any(
                any(kw in label for kw in hint_keywords)
                for label in sibling_labels
            )
            if not has_explanation:
                violations.append(
                    RuleViolation(
                        rule_id="disabled_without_reason",
                        severity="low",
                        widget_id=node.get("test_id", "unknown"),
                        description=(
                            f"Widget '{node.get('test_id')}' is disabled but "
                            f"there is no nearby text explaining why"
                        ),
                        recommended_fix=(
                            f"Add a label or tooltip near '{node.get('test_id')}' "
                            f"explaining why it is disabled and what the user "
                            f"needs to do to enable it"
                        ),
                    )
                )
        return violations

    @staticmethod
    def _rule_text_content_quality(tree: dict[str, Any]) -> list[RuleViolation]:
        """Flag widgets with low-quality text content.

        Detects single-character labels (not icons), placeholder-style labels
        like 'Label' or 'Button', and labels that are just numbers.

        Args:
            tree: Widget tree.

        Returns:
            Violations.
        """
        text_types = {
            "CTkButton", "TButton", "Button",
            "CTkLabel", "TLabel", "Label",
        }
        placeholder_texts = {
            "label", "button", "text", "title", "header",
            "ctkbutton", "ctklabel", "untitled", "placeholder",
            "test", "todo", "fixme", "xxx",
        }
        violations: list[RuleViolation] = []
        for node in RuleEngine._flatten(tree):
            wtype = node.get("widget_type", "")
            if wtype not in text_types:
                continue
            text = (node.get("text") or "").strip()
            if not text:
                continue

            text_lower = text.lower()
            if text_lower in placeholder_texts:
                violations.append(
                    RuleViolation(
                        rule_id="text_content_quality",
                        severity="medium",
                        widget_id=node.get("test_id", "unknown"),
                        description=(
                            f"Widget '{node.get('test_id')}' has placeholder-style "
                            f"text '{text}' that appears to be a development-time "
                            f"default"
                        ),
                        recommended_fix=(
                            f"Replace '{text}' in '{node.get('test_id')}' with "
                            f"meaningful, descriptive text"
                        ),
                    )
                )
        return violations
