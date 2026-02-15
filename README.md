# CustomTkinter Validator

**AI-native GUI testing and UX validation framework for CustomTkinter applications.**

A deterministic, introspection-based tool that injects into running CustomTkinter apps, traverses the full widget tree, extracts structured metadata, computes measurable UX/UI metrics, simulates events deterministically, and outputs machine-readable JSON reports optimised for AI-agent evaluation.

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
│   ├── layout_metrics.py    # Spatial analysis (overlap, spacing, alignment)
│   ├── contrast_checker.py  # WCAG 2.1 contrast ratio computation
│   └── accessibility_checker.py  # Focus chain, labels, disabled actions
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
TreeExtractor ──► widget_tree (nested dict)
  │
  ├─► LayoutMetrics ──► layout_violations
  ├─► ContrastChecker ──► contrast_issues
  ├─► AccessibilityChecker ──► accessibility_issues
  └─► RuleEngine ──► rule_violations
  │
  ▼
EventSimulator ──► interaction_results
  │
  ▼
JsonSerializer ──► JSON report
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
    "version": "1.0.0",
    "timestamp": "2026-02-15T12:00:00+00:00",
    "python_version": "3.12.0",
    "platform": "Windows-11-...",
    "tab_order": ["name_entry", "email_entry", "submit_btn", ...]
  },
  "widget_tree": {
    "widget_type": "CTk",
    "test_id": "CTk_root",
    "children": [...]
  },
  "layout_violations": [
    {
      "rule_id": "overlap_detection",
      "severity": "high",
      "widget_id": "submit_btn",
      "related_widget_id": "reset_btn",
      "description": "...",
      "recommended_fix": "..."
    }
  ],
  "contrast_issues": [
    {
      "rule_id": "insufficient_contrast",
      "severity": "critical",
      "widget_id": "status_label",
      "fg_color": "#555555",
      "bg_color": "#444444",
      "contrast_ratio": 1.28,
      "required_ratio": 4.5,
      "wcag_level": "AA",
      "description": "...",
      "recommended_fix": "..."
    }
  ],
  "accessibility_issues": [...],
  "interaction_results": [...],
  "summary_score": {
    "layout_score": 70.0,
    "accessibility_score": 50.0,
    "interaction_score": 87.5,
    "overall_score": 66.25
  }
}
```

---

## License

MIT
