# API Reference

## Core Classes

### `TestRunner`

Main orchestrator for the validation pipeline.

```python
from customtkinter_validator.core.runner import TestRunner

runner = TestRunner(config: ValidatorConfig | None = None)
```

#### Methods

##### `set_app(root: tk.Misc) -> None`
Attach the runner to a live application root widget.

```python
app = create_my_app()
runner.set_app(app)
```

##### `inject() -> int`
Inject test IDs into all widgets. Returns the number of widgets registered.

```python
widget_count = runner.inject()
print(f"Registered {widget_count} widgets")
```

##### `simulate(script: Callable[[EventSimulator], Any]) -> list[dict]`
Run an interaction script. Returns list of interaction results.

```python
def my_script(sim):
    sim.click("submit_btn")

results = runner.simulate(my_script)
```

##### `analyse() -> dict[str, Any]`
Analyze the application and generate a report. Returns the complete JSON report.

```python
report = runner.analyse()
print(report['summary_score'])
```

##### `save_report(path: str | Path, indent: int = 2) -> Path`
Save the most recent report to a JSON file.

```python
output_path = runner.save_report("report.json")
```

##### `run_headless(app_factory, script, output_path) -> dict`
Convenience method that runs the complete pipeline.

```python
report = runner.run_headless(
    app_factory=lambda: MyApp(),
    script=my_test_script,
    output_path="report.json"
)
```

**Parameters:**
- `app_factory`: Callable that creates and returns the root window (must NOT call `mainloop()`)
- `script`: Optional interaction script callable
- `output_path`: Optional path to save JSON report

**Returns:** Complete report dictionary

#### Properties

- `registry: WidgetRegistry` - Access the widget registry
- `simulator: EventSimulator` - Access the event simulator
- `rule_engine: RuleEngine` - Access the rule engine
- `report: dict | None` - Most recent report

---

### `EventSimulator`

Simulates user interactions deterministically.

```python
from customtkinter_validator.test_harness.event_simulator import EventSimulator
```

#### Methods

##### `click(test_id: str) -> dict`
Simulate a mouse click on a widget.

```python
result = sim.click("submit_button")
# Returns: {"action": "click", "widget_id": "submit_button", "success": True}
```

##### `type_text(test_id: str, text: str) -> dict`
Type text into an entry or textbox widget.

```python
result = sim.type_text("email_field", "user@example.com")
```

##### `focus(test_id: str) -> dict`
Give keyboard focus to a widget.

```python
result = sim.focus("username_field")
```

##### `tab(test_id: str) -> dict`
Simulate pressing the Tab key while focused on a widget.

```python
result = sim.tab("first_field")  # Moves focus to next widget
```

##### `hover(test_id: str) -> dict`
Simulate mouse hover (Enter event).

```python
result = sim.hover("tooltip_icon")
```

##### `clear_results() -> None`
Clear the recorded interaction history.

#### Properties

- `results: list[dict]` - List of all recorded interactions

---

### `ValidatorConfig`

Configuration dataclass for customizing validation behavior.

```python
from customtkinter_validator.core.config import ValidatorConfig

config = ValidatorConfig(
    min_contrast_ratio_normal=4.5,
    min_contrast_ratio_large=3.0,
    min_touch_target_px=24,
    min_padding_px=4,
    max_tree_depth=50
)

runner = TestRunner(config=config)
```

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `min_contrast_ratio_normal` | `float` | `4.5` | WCAG AA contrast for normal text |
| `min_contrast_ratio_large` | `float` | `3.0` | WCAG AA contrast for large text (18pt+) |
| `min_contrast_ratio_aaa_normal` | `float` | `7.0` | WCAG AAA contrast for normal text |
| `min_contrast_ratio_aaa_large` | `float` | `4.5` | WCAG AAA contrast for large text |
| `min_contrast_non_text` | `float` | `3.0` | WCAG 2.1 non-text contrast (§1.4.11) |
| `min_touch_target_px` | `int` | `24` | Minimum touch target size (WCAG 2.5.5) |
| `min_padding_px` | `int` | `4` | Minimum padding between widgets |
| `alignment_tolerance_px` | `int` | `3` | Tolerance for alignment checks |
| `symmetry_tolerance_px` | `int` | `10` | Tolerance for symmetry checks |
| `min_font_size_pt` | `int` | `9` | Minimum readable font size |
| `max_widgets_per_container` | `int` | `12` | Maximum widgets before cognitive overload |
| `max_button_text_length` | `int` | `30` | Maximum button label character count |
| `inconsistent_size_tolerance_pct` | `float` | `50.0` | Tolerance for sibling size consistency |
| `widget_outside_bounds_tolerance_px` | `int` | `2` | Pixels allowed outside parent bounds |
| `tab_visual_order_tolerance_px` | `int` | `20` | Tolerance for tab vs visual order |
| `max_tree_depth` | `int` | `50` | Maximum widget tree depth |
| `container_widget_types` | `set[str]` | See below | Widget types treated as containers |
| `internal_attr_names` | `list[str]` | See below | CTk internal widget attributes |

**Default Container Types:**
```python
{
    "CTk", "CTkToplevel", "CTkFrame", "CTkScrollableFrame",
    "CTkTabview", "TFrame", "Frame", "LabelFrame", "Toplevel", "Tk"
}
```

**Default Internal Attributes:**
```python
[
    "_canvas", "_text_label", "_entry", "_textbox",
    "_check_button", "_switch_button", "_radiobutton",
    "_slider", "_option_menu", "_fg_parts"
]
```

---

### `RuleEngine`

Manage custom validation rules.

```python
from customtkinter_validator.reporting.rule_engine import RuleEngine

engine = runner.rule_engine
```

#### Methods

##### `register_rule(rule_id, check_fn, severity="medium", description="")`
Register a custom validation rule.

```python
def check_no_red_buttons(widget_tree):
    """Custom rule: buttons shouldn't be red."""
    issues = []
    # ... traverse tree and check ...
    return issues

engine.register_rule(
    rule_id="no_red_buttons",
    check_fn=check_no_red_buttons,
    severity="high",
    description="Buttons should not use red color"
)
```

**Parameters:**
- `rule_id`: Unique identifier
- `check_fn`: Function that takes widget_tree and returns list of violation dicts
- `severity`: "critical" | "high" | "medium" | "low"
- `description`: Human-readable description

##### `evaluate(widget_tree: dict) -> list[dict]`
Run all registered rules against a widget tree.

```python
violations = engine.evaluate(widget_tree)
```

---

## Testable Widgets

Wrapper classes that enforce explicit `test_id` assignment.

```python
from customtkinter_validator.widgets.base import (
    TFrame, TButton, TLabel, TEntry, TCheckBox,
    TTextbox, TSwitch, TRadioButton, TSlider,
    TOptionMenu, TComboBox
)
```

### Usage

```python
# All parameters same as CTk* except test_id is required
button = TButton(parent, text="Submit", test_id="submit_btn")
entry = TEntry(parent, placeholder_text="Email", test_id="email_field")
label = TLabel(parent, text="Welcome", test_id="heading")
```

### Mixin Pattern

```python
from customtkinter_validator.widgets.base import TestableWidget

class MyCustomWidget(ctk.CTkFrame, TestableWidget):
    def __init__(self, parent, *, test_id: str, **kwargs):
        ctk.CTkFrame.__init__(self, parent, **kwargs)
        TestableWidget.__init__(self, test_id)
```

---

## Analyzers

### Tree Extractor

Extract complete widget metadata.

```python
from customtkinter_validator.analyzer.tree_extractor import TreeExtractor

extractor = TreeExtractor(registry, config)
tree = extractor.extract(root_widget)
```

**Output Structure:**
```python
{
    "widget_type": str,
    "test_id": str,
    "text": str | None,
    "font_family": str | None,
    "font_size": int | None,
    "font_weight": str,
    "fg_color": str,  # Hex color
    "bg_color": str,
    "width": int,
    "height": int,
    "x": int,
    "y": int,
    "abs_x": int,
    "abs_y": int,
    "visibility": bool,
    "enabled": bool,
    "parent_id": str | None,
    "children_ids": list[str],
    "children": list[dict],
    "layout_manager": str,  # "pack" | "grid" | "place" | "wm"
    "padding": dict,
    "placeholder_text": str | None,
    "corner_radius": int | None,
    "border_width": int | None,
    "has_command": bool,
    "has_image": bool,
    "values": list[str] | None,
    "layout_detail": dict  # Detailed grid/pack/place info
}
    "enabled": bool,
    "parent_id": str | None,
    "children_ids": list[str],
    "children": list[dict],
    "layout_manager": str,  # "pack" | "grid" | "place" | "wm"
    "padding": dict
}
```

### Layout Metrics

Analyze spatial relationships and identify layout issues.

```python
from customtkinter_validator.analyzer.layout_metrics import LayoutMetrics

metrics = LayoutMetrics(config)
violations = metrics.analyse(widget_tree)
```

**Detects:**
- Overlapping widgets
- Insufficient padding
- Touch targets too small
- Alignment inconsistencies
- Symmetry deviations
- Widget outside parent bounds
- Content truncation risk

### Contrast Checker

Validate WCAG 2.1 contrast ratios.

```python
from customtkinter_validator.analyzer.contrast_checker import ContrastChecker

checker = ContrastChecker(config)
issues = checker.check(widget_tree)
```

**Detects:**
- WCAG AA violations (4.5:1 normal, 3:1 large)
- WCAG AAA violations (7:1 normal, 4.5:1 large)
- Non-text contrast violations (3:1 per §1.4.11)

### Accessibility Checker

Validate keyboard navigation and semantic structure.

```python
from customtkinter_validator.analyzer.accessibility_checker import AccessibilityChecker

checker = AccessibilityChecker(registry, config)
issues = checker.check(widget_tree)
tab_order = checker.compute_tab_order()
```

**Detects:**
- Missing labels for entry fields
- Disabled primary action buttons
- Unreachable widgets (no keyboard access)
- Empty focus chains
- Small text (below `min_font_size_pt`)
- Tab order vs visual order mismatch

### UX Analyzer

Heuristic analysis of common UX anti-patterns.

```python
from customtkinter_validator.analyzer.ux_analyzer import UXAnalyzer

analyzer = UXAnalyzer(config)
ux_issues = analyzer.analyse(widget_tree)
```

**Detects:**
- Cognitive overload (too many widgets per container)
- Duplicate button labels
- Long button text
- Inconsistent button casing
- Missing placeholder text in entries
- Orphaned labels
- Single-child containers (unnecessary nesting)
- Missing window title
- Empty selection widgets
- Ungrouped radio buttons
- No primary action in container
- Buttons without command callbacks
- Deep single nesting chains

### Consistency Checker

Validate visual consistency across similar widgets.

```python
from customtkinter_validator.analyzer.consistency_checker import ConsistencyChecker

checker = ConsistencyChecker(config)
consistency_issues = checker.check(widget_tree)
```

**Detects:**
- Inconsistent button sizes among siblings
- Inconsistent entry widths
- Inconsistent fonts in same widget type
- Inconsistent padding
- Inconsistent corner radii
- Mixed layout managers among siblings
- Inconsistent spacing between siblings

---

## Report Structure

### Metadata

```json
{
  "tool": "CustomTkinter Validator",
  "version": "2.0.0",
  "timestamp": "2026-02-15T12:00:00+00:00",
  "python_version": "3.12.0",
  "platform": "Windows-10-...",
  "tab_order": ["widget1", "widget2", ...]
}
```

### Violation Schema

All violations follow this structure:

```json
{
  "rule_id": "string",
  "severity": "critical" | "high" | "medium" | "low",
  "widget_id": "string",
  "description": "string",
  "recommended_fix": "string"
}
```

Additional fields vary by violation type:

**Contrast:**
```json
{
  "fg_color": "#RRGGBB",
  "bg_color": "#RRGGBB",
  "contrast_ratio": 3.14,
  "required_ratio": 4.5
}
```

**Layout:**
```json
{
  "measured_value": {...},
  "threshold": {...}
}
```

### Interaction Results

```json
{
  "action": "click" | "type_text" | "focus" | "tab" | "hover",
  "widget_id": "string",
  "timestamp": "ISO 8601",
  "success": true,
  "details": {...}
}
```

### Score Calculation

```python
# Layout Score (includes consistency issues)
base = 100
deduction = sum(SEVERITY_DEDUCTIONS[v.severity] for v in layout_violations + consistency_issues)
layout_score = max(0, base - deduction)

# Accessibility Score (includes contrast issues)
deduction = sum(SEVERITY_DEDUCTIONS[v.severity] for v in contrast_issues + accessibility_issues)
accessibility_score = max(0, base - deduction)

# UX Score (includes rule violations)
deduction = sum(SEVERITY_DEDUCTIONS[v.severity] for v in ux_issues + rule_violations)
ux_score = max(0, base - deduction)

# Interaction Score
success_rate = successful_interactions / total_interactions * 100

# Overall Score
overall = (layout * 0.3) + (accessibility * 0.4) + (interaction * 0.3)
ux_penalty = (100 - ux_score) * 0.15
overall = max(0, overall - ux_penalty)
```

**Severity Deductions:**
- `critical`: 25 points
- `high`: 15 points
- `medium`: 10 points
- `low`: 5 points

---

## CLI

```bash
python -m customtkinter_validator [OPTIONS]
```

**Options:**
- `--app MODULE`: Python module path (e.g., `examples.sample_app`)
- `--output PATH`: Output JSON file path
- `--print`: Print report to stdout

**Example:**
```bash
python -m customtkinter_validator \
    --app examples.sample_app \
    --output report.json \
    --print
```

---

## Exception Handling

All validator components handle exceptions gracefully:

- **TclError**: Widget destroyed or doesn't exist
- **AttributeError**: Widget doesn't support a property (e.g., `cget("font")`)
- **ValueError**: CustomTkinter raises for unsupported options

The validator catches these and continues analysis, ensuring partial results even with problematic widgets.

---

## Best Practices

1. **Use explicit test_ids** for important widgets
2. **Run validation early** in development
3. **Set baselines** and track score improvements
4. **Prioritize severity** when fixing issues
5. **Re-validate** after applying fixes

---

## Next Steps

- [See complete examples](examples.md)
- [Understand architecture](architecture.md)
- [Customize configuration](configuration.md)
- [Add custom rules](extending.md)
