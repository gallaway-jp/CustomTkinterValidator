# Architecture

## System Overview

CustomTkinter Validator uses a pipeline architecture:

```
App → Injector → Simulator → Analyzers → Serializer → JSON
```

## Component Breakdown

### 1. Test Harness Layer

#### Widget Registry (`test_harness/widget_registry.py`)
Bidirectional mapping between test_ids and widget objects.

```python
registry.register("submit_btn", button_widget)
widget = registry.get_widget("submit_btn")
test_id = registry.get_id(widget)  # Reverse lookup
```

**Key Features:**
- O(1) lookup in both directions
- Uses `id(widget)` for reverse mapping
- Thread-safe registration

#### Injector (`test_harness/injector.py`)
Recursively walks widget tree and assigns test_ids.

**Algorithm:**
1. Start at root widget
2. Check if widget has `_test_id` attribute (explicit ID)
3. If not, generate hierarchical ID: `ClassName_siblingIndex`
4. Register in WidgetRegistry
5. Recurse only into container widgets (Frame, CTk, etc.)
6. Filter out internal CTk widgets (`_canvas`, `_text_label`, etc.)

**Container Detection:**
```python
def _is_container(widget):
    # Check widget's class and all base classes
    for cls in type(widget).__mro__:
        if cls.__name__ in container_types:
            return True
    return False
```

This supports custom classes like `class MyApp(ctk.CTk)`.

#### Event Simulator (`test_harness/event_simulator.py`)
Generates deterministic Tkinter events.

**Implementation:**
- Uses `widget.event_generate("<ButtonPress-1>")` for clicks
- Uses `widget.insert(0, text)` for text entry
- Uses `widget.focus_set()` for focus
- Records all interactions in `results` list

**Determinism:**
- No actual mouse/keyboard hardware involved
- Predictable event sequence
- Replayable from test script

### 2. Analyzer Layer

#### Tree Extractor (`analyzer/tree_extractor.py`)
Extracts complete widget metadata.

**Metadata Collected:**
- Visual: colors, fonts, dimensions
- Spatial: absolute/relative positions
- Structural: parent-child relationships
- State: visibility, enabled/disabled
- Layout: manager type, padding

**Recursion Strategy:**
```python
def _extract_node(widget, parent_id, depth):
    metadata = {...}  # Extract all properties
    
    if self._is_container(widget):
        for child in self._get_user_children(widget):
            child_data = self._extract_node(child, test_id, depth+1)
            metadata["children"].append(child_data)
    
    return metadata
```

#### Layout Metrics (`analyzer/layout_metrics.py`)
Spatial analysis using computational geometry.

**Algorithms:**

**Overlap Detection:**
```python
class BoundingBox:
    def overlaps(self, other):
        return not (
            self.x2 < other.x1 or  # self is left of other
            self.x1 > other.x2 or  # self is right of other
            self.y2 < other.y1 or  # self is above other
            self.y1 > other.y2     # self is below other
        )
```

**Alignment Detection:**
- Group widgets by parent
- For each group, collect all x/y coordinates
- Find modes (most common values)
- Flag widgets deviating beyond tolerance

**Symmetry Detection:**
- Calculate center of mass for widget groups
- Measure distance from center
- Flag asymmetric arrangements

#### Contrast Checker (`analyzer/contrast_checker.py`)
WCAG 2.1 compliant contrast calculation.

**Relative Luminance Formula:**
```python
def relative_luminance(rgb):
    # Linearize sRGB values
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    
    R, G, B = [linearize(c) for c in rgb]
    return 0.2126 * R + 0.7152 * G + 0.0722 * B

def contrast_ratio(L1, L2):
    lighter = max(L1, L2)
    darker = min(L1, L2)
    return (lighter + 0.05) / (darker + 0.05)
```

**Color Resolution:**
- CTk colors can be tuples: `("#light", "#dark")`
- Uses `customtkinter.get_appearance_mode()` to resolve
- Handles #RGB, #RRGGBB, #RRRGGGBBB formats

**Three Check Levels:**
- WCAG AA (4.5:1 normal, 3:1 large) — severity: critical/high
- WCAG AAA (7:1 normal, 4.5:1 large) — severity: low
- Non-text contrast (3:1 for interactive elements per §1.4.11) — severity: medium

#### Accessibility Checker (`analyzer/accessibility_checker.py`)
Keyboard navigation and semantic structure validation.

**Tab Order Computation:**
1. Try `widget.tk_focusNext()` (native Tk tab order)
2. If empty (headless mode), fall back to geometry-based sort:
   ```python
   sorted(widgets, key=lambda w: (abs_y, abs_x))
   ```

**Focus Chain Validation:**
- Ensures at least one widget accepts focus
- Checks `takefocus` property via `widget.cget("takefocus")`
- For CTk widgets, checks `widget._canvas.cget("takefocus")`

**Label Detection:**
- Groups labels and entries by parent container
- Compares label count vs entry count
- Flags entries where labels < entries

**Additional Checks:**
- Small text detection (font size below `min_font_size_pt`)
- Tab vs visual order mismatch (tab order diverges from top-to-bottom, left-to-right reading order)

#### UX Analyzer (`analyzer/ux_analyzer.py`)
Heuristic analysis of common UX anti-patterns.

**13 Checks:**
- `cognitive_overload`: Container with too many widgets (exceeds `max_widgets_per_container`)
- `duplicate_button_label`: Multiple buttons with identical text in same container
- `long_button_text`: Button label exceeds `max_button_text_length` characters
- `inconsistent_button_casing`: Sibling buttons using mixed text casing styles
- `missing_placeholder`: Entry field without placeholder text
- `orphaned_label`: Label not adjacent to any interactive widget
- `single_child_container`: Frame with a single child (unnecessary nesting)
- `missing_window_title`: Top-level window without a title
- `empty_selection_widget`: ComboBox/OptionMenu with no values
- `ungrouped_radio_button`: RadioButton not inside a grouping frame
- `no_primary_action`: Container with buttons but none visually distinguished
- `button_no_command`: Button without a command callback bound
- `deep_single_nesting`: Chain of single-child containers

#### Consistency Checker (`analyzer/consistency_checker.py`)
Cross-widget visual consistency analysis.

**7 Checks:**
- `inconsistent_button_size`: Sibling buttons with significantly different dimensions
- `inconsistent_entry_width`: Sibling entries with significantly different widths
- `inconsistent_font`: Widgets of the same type using different fonts
- `inconsistent_padding`: Same widget type with different padding within a container
- `inconsistent_corner_radius`: Siblings with different corner radii
- `mixed_layout_managers`: Siblings using different layout managers (grid vs pack)
- `inconsistent_spacing`: Varying gaps between adjacent siblings

### 3. Reporting Layer

#### Rule Engine (`reporting/rule_engine.py`)
Pluggable validation rules.

**Built-in Rules:**
- `hidden_interactive`: Interactive widgets with `visibility=False`
- `empty_text_button`: Buttons with no text
- `excessive_nesting`: Widget tree depth > threshold
- `zero_dimension_widget`: Widgets with width/height = 0
- `disabled_without_reason`: Disabled widget with no nearby explanatory label
- `text_content_quality`: Placeholder-style text ("Label", "Button", "test", "todo")

**Custom Rule Interface:**
```python
def my_custom_rule(widget_tree: dict) -> list[dict]:
    issues = []
    # Traverse tree and detect violations
    # ...
    return [
        {
            "widget_id": "...",
            "description": "...",
            "recommended_fix": "..."
        }
    ]
```

#### JSON Serializer (`reporting/json_serializer.py`)
Assembles the final report.

**Report Structure:**
```json
{
  "metadata": {...},
  "widget_tree": {...},
  "layout_violations": [...],
  "contrast_issues": [...],
  "accessibility_issues": [...],
  "ux_issues": [...],
  "consistency_issues": [...],
  "rule_violations": [...],
  "interaction_results": [...],
  "summary_score": {...}
}
```

**Score Calculation:**
```python
def _compute_category_score(violations, base=100):
    total = sum(
        SEVERITY_DEDUCTIONS[v["severity"]]
        for v in violations
    )
    return max(0, base - total)
```

The overall score combines layout (30%), accessibility (30%), and interaction (30%) with a 15% UX penalty adjustment.

### 4. Core Layer

#### Configuration (`core/config.py`)
Dataclass with validation thresholds.

```python
@dataclass
class ValidatorConfig:
    min_contrast_ratio_normal: float = 4.5
    min_touch_target_px: int = 24
    # ...
```

#### Runner (`core/runner.py`)
Orchestrates the entire pipeline.

**Pipeline Stages:**
```python
1. set_app(root)           # Attach to app
2. inject()                # Assign test_ids
3. simulate(script)        # Run interactions
4. analyse()               # Extract & analyze
5. save_report(path)       # Write JSON
```

**Headless Mode:**
```python
def run_headless(app_factory, script, output_path):
    root = app_factory()
    root.update_idletasks()  # Force geometry calculation
    self.set_app(root)
    self.inject()
    if script:
        self.simulate(script)
    report = self.analyse()
    if output_path:
        self.save_report(output_path)
    root.destroy()
    return report
```

## Data Flow

### Injection Phase
```
App Root
  ↓
Injector.inject(root)
  ↓
Injector._walk(widget, depth)
  ↓ (for each widget)
Injector._resolve_test_id(widget)
  ↓
Registry.register(test_id, widget)
```

### Analysis Phase
```
Registry (test_id ↔ widget)
  ↓
TreeExtractor.extract(root)
  ↓
{ widget_tree: {...} }
  ↓
LayoutMetrics.analyse(tree) → violations
ContrastChecker.check(tree) → issues
AccessibilityChecker.check(tree) → issues
UXAnalyzer.analyse(tree) → ux_issues
ConsistencyChecker.check(tree) → consistency_issues
RuleEngine.evaluate(tree) → violations
  ↓
JSONSerializer.build_report(...)
  ↓
{ report.json }
```

## Design Patterns

### Strategy Pattern (Analyzers)
Each analyzer implements same interface: `analyse(widget_tree) → issues`

### Registry Pattern (Widget Tracking)
Central registry for bidirectional widget ↔ ID mapping

### Builder Pattern (Report Assembly)
Serializer assembles report from multiple data sources

### Template Method (Validation Pipeline)
Runner defines pipeline, subclasses can override steps

### Factory Pattern (App Creation)
User provides `app_factory` callable for testability

## Thread Safety

The validator is **not thread-safe** by design:
- Tkinter is single-threaded
- All operations must run on main thread
- Use `app.after()` for deferred operations

## Performance Characteristics

**Time Complexity:**
- Tree traversal: O(N) where N = widget count
- Overlap detection: O(N²) within each parent
- Alignment checks: O(N log N) for sorting
- Overall: O(N²) worst case

**Space Complexity:**
- Widget tree: O(N)
- Registry: O(N)
- Report JSON: O(N)

**Typical Performance:**
- 100 widgets: < 1 second
- 1000 widgets: ~2-3 seconds
- 10000 widgets: ~30 seconds

## Extensibility Points

1. **Custom Rules**: `RuleEngine.register_rule()`
2. **Custom Analyzers**: Subclass base analyzer interface
3. **Custom Widgets**: Use `TestableWidget` mixin
4. **Custom Config**: Extend `ValidatorConfig` dataclass
5. **Custom Serializers**: Implement `build_report()` method
6. **UX Heuristics**: Add checks to `UXAnalyzer`
7. **Consistency Rules**: Add checks to `ConsistencyChecker`

## Error Handling Strategy

**Graceful Degradation:**
- If a widget can't be analyzed, skip it (don't crash)
- If a property can't be read, use default value
- If an analyzer fails, continue with others
- Always produce partial results

**Exception Types Handled:**
```python
try:
    value = widget.cget("font")
except (tk.TclError, AttributeError, ValueError):
    value = default_value
```

## Next Steps

- [API Reference](api-reference.md) - Detailed API docs
- [Examples](examples.md) - Usage examples
- [Extending](extending.md) - Add custom functionality
- [Configuration](configuration.md) - Customize behavior
