# CustomTkinter Validator

**AI-native GUI testing and UX validation framework for CustomTkinter applications.**

A deterministic, introspection-based tool that injects into running CustomTkinter apps, traverses the full widget tree, extracts structured metadata, computes measurable UX/UI metrics, simulates events deterministically, and outputs machine-readable JSON reports optimised for AI-agent evaluation.

---

## What It Detects

The validator runs **6 analyser categories** producing detailed, actionable findings:

| Category | # Checks | Examples |
|---|---|---|
| **Layout** | 7 | Overlap, spacing, touch targets, alignment, symmetry, widget-out-of-bounds, truncation risk |
| **Contrast** | 3 | WCAG AA (4.5:1), WCAG AAA (7:1), non-text contrast (3:1) |
| **Accessibility** | 6 | Missing labels, disabled primary actions, unreachable focusables, focus chain, small text, tab-vs-visual order |
| **UX Heuristics** | 13 | Cognitive overload, duplicate buttons, long button text, orphaned labels, missing placeholders, ungrouped radios, no primary action, button without command, etc. |
| **Consistency** | 7 | Inconsistent button/entry sizes, fonts, padding, corner radius, spacing, mixed layout managers |
| **Rules** | 6 | Hidden interactive, empty text buttons, excessive nesting, zero-dimension, disabled without reason, placeholder text quality |

---

## Setup Instructions

### Prerequisites

- Python 3.12 or later
- `customtkinter >= 5.2.0`
- A working Tcl/Tk installation (bundled with standard Python on Windows and macOS)

### Installation

```bash
# Clone the repository
cd CustomTkinterValidator

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
```

---

## Command-Line Usage

### Using the CLI

```bash
# Run against any module that exposes a create_app() function
python -m customtkinter_validator --app examples.sample_app --output report.json --print

# Override thresholds
python -m customtkinter_validator --app examples.sample_app \
    --min-contrast 4.5 \
    --min-touch-target 32 \
    -o my_report.json --print
```

### Running the Sample Test

```bash
python examples/sample_test.py
```

This launches the sample app headlessly, injects the harness, simulates a user flow (typing into fields, clicking buttons, tabbing), runs the full analysis, and saves `sample_report.json`.

### Programmatic Usage

```python
from customtkinter_validator import TestRunner, ValidatorConfig

config = ValidatorConfig(min_contrast_ratio_normal=4.5)
runner = TestRunner(config)

report = runner.run_headless(
    app_factory=my_create_app_function,
    script=lambda sim: [
        sim.type_text("email_entry", "test@example.com"),
        sim.click("submit_btn"),
    ],
    output_path="report.json",
)
```

---

## Architecture

```
customtkinter_validator/
├── __init__.py              # Package exports
├── __main__.py              # CLI entry point
├── core/
│   ├── config.py            # ValidatorConfig dataclass
│   └── runner.py            # TestRunner orchestrator
├── test_harness/
│   ├── widget_registry.py   # test_id → widget mapping
│   ├── injector.py          # Widget-tree walker + auto-id assignment
│   └── event_simulator.py   # Deterministic event generation
├── analyzer/
│   ├── tree_extractor.py    # Full widget metadata extraction
│   ├── layout_metrics.py    # Spatial analysis (overlap, spacing, alignment, bounds, truncation)
│   ├── contrast_checker.py  # WCAG 2.1 AA/AAA + non-text contrast
│   ├── accessibility_checker.py  # Focus chain, labels, disabled actions, text size, tab order
│   ├── ux_analyzer.py       # UX heuristics (cognitive load, labelling, conventions)
│   └── consistency_checker.py    # Visual consistency (sizing, fonts, spacing, styling)
├── reporting/
│   ├── rule_engine.py       # Configurable validation rules
│   └── json_serializer.py   # Canonical JSON output assembly
└── widgets/
    └── base.py              # TestableWidget mixin + T* wrapper classes
```

### Data Flow

```
App Window
  │
  ▼
Injector ──► WidgetRegistry (test_id → widget)
  │
  ▼
TreeExtractor ──► widget_tree (nested dict with 25+ fields per widget)
  │
  ├─► LayoutMetrics ──► layout_violations (overlap, spacing, alignment, bounds, truncation)
  ├─► ContrastChecker ──► contrast_issues (AA, AAA, non-text)
  ├─► AccessibilityChecker ──► accessibility_issues (labels, focus, text size, tab order)
  ├─► UXAnalyzer ──► ux_issues (cognitive load, labelling, conventions)
  ├─► ConsistencyChecker ──► consistency_issues (sizing, fonts, spacing)
  └─► RuleEngine ──► rule_violations (configurable rules)
  │
  ▼
EventSimulator ──► interaction_results
  │
  ▼
JsonSerializer ──► JSON report (6 issue categories + scores)
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| Widget-tree introspection only | Deterministic, no OS/display dependency |
| `test_id` as primary key | Stable across runs, no memory addresses |
| `event_generate` for simulation | Tkinter-native, no OS automation needed |
| Nested + flat output | AI agents can traverse or scan linearly |
| Severity + recommended_fix | Directly consumable by LLM reasoning |

---

## Extension Guide

### Adding Custom Rules

```python
from customtkinter_validator.reporting.rule_engine import Rule, RuleViolation

def check_button_colours(tree: dict) -> list[RuleViolation]:
    violations = []
    # Your custom check logic here
    return violations

runner.rule_engine.add_rule(Rule(
    rule_id="custom_button_colours",
    name="Button Colour Check",
    description="Ensures all buttons use the brand colour palette",
    enabled=True,
    check=check_button_colours,
))
```

### Adding Custom Widget Wrappers

```python
from customtkinter_validator.widgets.base import TestableWidget
import customtkinter as ctk

class TProgressBar(TestableWidget, ctk.CTkProgressBar):
    def __init__(self, master, *, test_id: str, **kwargs):
        self._init_test_id(test_id)
        super().__init__(master, **kwargs)
```

### Extending the Analyser

Create a new module in `analyzer/` that:
1. Takes the widget tree dict as input
2. Returns a list of dataclass instances with a `to_dict()` method
3. Is called from `runner.py`'s `analyse()` method

---

## Determinism Guarantees

The framework guarantees deterministic, replayable test runs through:

1. **No `time.sleep`**: All synchronisation uses `update_idletasks()` which processes pending geometry/display computations synchronously.

2. **`event_generate` over OS events**: Events are injected directly into Tk's event queue, bypassing the OS event system entirely.

3. **Deterministic test_ids**: Widget identifiers are derived from class name + sibling index in the tree hierarchy, making them stable across identical widget constructions.

4. **No screenshot/pixel dependency**: All checks use introspected properties (geometry, colour values, state flags), not rendered output.

5. **Stateless analysis**: Each `analyse()` call reads the current widget state fresh — no cached assumptions.

6. **Ordered traversal**: The widget tree is always traversed depth-first in `winfo_children()` order, which matches widget creation order.

---

## Limitations

1. **CustomTkinter internal structure**: CTk widgets use internal canvases and sub-widgets. The framework filters these heuristically via known attribute names (`_canvas`, `_text_label`, etc.). Unusual custom widgets may require extending the `internal_attr_names` config.

2. **Theme-dependent colours**: Colours extracted reflect the current appearance mode (Light/Dark) at analysis time. Switching modes requires re-analysis.

3. **Font metrics approximation**: Font sizes are read from widget configuration, not measured in pixels. Actual rendered size depends on DPI scaling and platform font rendering.

4. **Tab order**: The computed tab order follows Tk's `tk_focusNext()` chain, which may differ from visual reading order in complex layouts.

5. **Event fidelity**: `event_generate` does not trigger all OS-level side effects (e.g., tooltip timers, hover animations driven by the window manager).

6. **No cross-window support**: The framework analyses a single root window. Multi-window apps require separate injections.

7. **Headless environments**: On Linux CI servers without a display, you need `xvfb-run` to provide a virtual framebuffer:
   ```bash
   xvfb-run python -m customtkinter_validator --app myapp
   ```

---

## CTk-Aware False Positive Handling (v2.0.1)

CustomTkinter's architecture introduces patterns that naive analysis would incorrectly flag. The validator recognises and suppresses these CTk-inherent issues:

| Pattern | Handling |
|---|---|
| **CTkTabview inactive tabs** | Widgets hidden by tab switching are excluded from hidden-interactive, zero-dimension, disabled-without-reason, alignment, symmetry, spacing, overlap, touch-target, truncation, and button-size checks |
| **CTk canvas rendering** | Interactive CTk widgets (CTkButton, CTkEntry, etc.) render via an internal Tk canvas — the outer frame bg naturally blends with its parent. Non-text contrast checks skip these when the ratio is below 1.5:1 |
| **Grid alignment tolerance** | Grid-managed containers use 3× the normal alignment tolerance (min 10px) since small x-offsets come from `sticky` settings and internal padding, not misalignment |
| **Label font diversity** | Labels are excluded from font consistency checks because they serve diverse semantic roles (headings, body, captions, info-icons) |
| **Context-dependent disabled buttons** | Buttons with text like "Cancel", "Stop", "Abort", "Pause", "Undo", "Redo" are expected to start disabled and are excluded from disabled-without-reason and disabled-primary-action checks |
| **Acronyms in button casing** | Short all-caps words (2–4 chars, e.g. "AI", "PDF") are treated as single tokens for casing classification, so "AI Fix" is correctly classified as Title Case |
| **CTkScrollableFrame wrappers** | Single-child containers whose child is a CTkScrollableFrame are not flagged as unnecessary nesting |
| **Expanded primary action keywords** | 40+ action verbs recognised (start, run, review, execute, launch, analyse, validate, etc.) to avoid false no-primary-action warnings |

---

## Performance Considerations

| Operation | Typical Time | Notes |
|---|---|---|
| Injection (100 widgets) | < 50 ms | Single tree walk + registration |
| Tree extraction | < 100 ms | Geometry reads are O(1) per widget |
| Layout analysis | < 200 ms | O(n²) overlap check on visible widgets |
| Contrast checking | < 50 ms | Per-widget colour math |
| Accessibility check | < 100 ms | Focus chain walk is O(n) |
| JSON serialisation | < 20 ms | Standard library `json.dumps` |
| **Total pipeline** | **< 500 ms** | For typical apps with < 200 widgets |

For large applications (500+ widgets), the overlap detection's O(n²) pairwise check dominates. Consider:
- Filtering to visible widgets only (default)
- Increasing `overlap_tolerance_px` to reduce false positives
- Disabling symmetry checks for deeply nested layouts

---

## JSON Output Schema

```json
{
  "metadata": {
    "tool": "CustomTkinter Validator",
    "version": "2.0.1",
    "timestamp": "2026-02-15T12:00:00+00:00",
    "python_version": "3.12.0",
    "platform": "Windows-11-...",
    "tab_order": ["name_entry", "email_entry", "submit_btn"]
  },
  "widget_tree": {
    "widget_type": "CTk",
    "test_id": "CTk_root",
    "text": null,
    "placeholder_text": null,
    "font_family": null,
    "font_size": null,
    "font_weight": "normal",
    "fg_color": "#1a1a2e",
    "bg_color": "#1a1a2e",
    "width": 800,
    "height": 600,
    "corner_radius": null,
    "border_width": null,
    "has_command": false,
    "has_image": false,
    "values": null,
    "layout_manager": "pack",
    "layout_detail": {"side": "top", "fill": "both", "expand": true, "anchor": "center"},
    "children": ["..."]
  },
  "layout_violations": [
    {
      "rule_id": "overlap_detection | insufficient_padding | small_touch_target | alignment_inconsistency | symmetry_deviation | widget_outside_bounds | content_truncation_risk",
      "severity": "critical | high | medium | low",
      "widget_id": "...",
      "description": "...",
      "recommended_fix": "..."
    }
  ],
  "contrast_issues": [
    {
      "rule_id": "insufficient_contrast | insufficient_contrast_aaa | insufficient_non_text_contrast",
      "severity": "...",
      "widget_id": "...",
      "fg_color": "#555555",
      "bg_color": "#444444",
      "contrast_ratio": 1.28,
      "required_ratio": 4.5,
      "wcag_level": "AA | AAA"
    }
  ],
  "accessibility_issues": [
    {
      "rule_id": "missing_label | disabled_primary_action | unreachable_focusable | empty_focus_chain | small_text | tab_visual_order_mismatch",
      "severity": "...",
      "widget_id": "..."
    }
  ],
  "ux_issues": [
    {
      "rule_id": "cognitive_overload | duplicate_button_label | long_button_text | inconsistent_button_casing | missing_placeholder | orphaned_label | single_child_container | missing_window_title | empty_selection_widget | ungrouped_radio_button | no_primary_action | button_no_command | deep_single_nesting",
      "severity": "...",
      "widget_id": "..."
    }
  ],
  "consistency_issues": [
    {
      "rule_id": "inconsistent_button_size | inconsistent_entry_width | inconsistent_font | inconsistent_padding | inconsistent_corner_radius | mixed_layout_managers | inconsistent_spacing",
      "severity": "...",
      "widget_id": "..."
    }
  ],
  "rule_violations": [
    {
      "rule_id": "hidden_interactive | empty_text_button | excessive_nesting | zero_dimension_widget | disabled_without_reason | text_content_quality",
      "severity": "...",
      "widget_id": "..."
    }
  ],
  "interaction_results": ["..."],
  "summary_score": {
    "layout_score": 70.0,
    "accessibility_score": 50.0,
    "ux_score": 85.0,
    "interaction_score": 87.5,
    "overall_score": 63.75
  }
}
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
