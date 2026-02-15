# Extending the Validator

## Custom Validation Rules

Add custom rules via the `RuleEngine`:

```python
from customtkinter_validator.core.runner import TestRunner

def check_no_red_text(widget_tree):
    \"\"\"Custom rule: Text should not be red.\"\"\"
    issues = []
    
    def traverse(node):
        fg_color = node.get(\"fg_color\", \"\").lower()
        if \"ff0000\" in fg_color or fg_color == \"red\":
            issues.append({
                \"widget_id\": node[\"test_id\"],
                \"description\": f\"Widget has red text color ({fg_color})\",
                \"recommended_fix\": \"Change text color to a less alarming color\"
            })
        
        for child in node.get(\"children\", []):
            traverse(child)
    
    traverse(widget_tree)
    return issues

# Register the rule
runner = TestRunner()
runner.rule_engine.register_rule(
    rule_id=\"no_red_text\",
    check_fn=check_no_red_text,
    severity=\"medium\",
    description=\"Text should not use red color (reserved for errors)\"
)
```

## Rule Function Signature

```python
def my_rule(widget_tree: dict) -> list[dict]:
    \"\"\"
    Args:
        widget_tree: Complete widget tree with all metadata
    
    Returns:
        List of violation dictionaries with:
        - widget_id: str (required)
        - description: str (required)
        - recommended_fix: str (required)
        - Any additional context fields
    \"\"\"
    return [...]
```

## Custom Widget Types

### Using the Mixin

```python
from customtkinter_validator.widgets.base import TestableWidget
import customtkinter as ctk

class MyCustomWidget(ctk.CTkFrame, TestableWidget):
    def __init__(self, parent, *, test_id: str, title: str = \"\", **kwargs):
        ctk.CTkFrame.__init__(self, parent, **kwargs)
        TestableWidget.__init__(self, test_id)
        
        # Your custom widget implementation
        self.title_label = ctk.CTkLabel(self, text=title)
        self.title_label.pack()
```

### Custom Wrapper

```python
class TMyWidget(ctk.CTkComboBox):
    def __init__(self, master, *, test_id: str, **kwargs):
        super().__init__(master, **kwargs)
        self._test_id = test_id
        
        if not test_id or not test_id.strip():
            raise ValueError(\"test_id must be a non-empty string\")
```

## Custom Analyzers

Create analyzers that implement the interface:

```python
class CustomAnalyzer:
    def __init__(self, config):
        self.config = config
    
    def analyse(self, widget_tree: dict) -> list[dict]:
        \"\"\"Analyse widget tree and return violations.\"\"\"
        violations = []
        # ... your analysis logic ...
        return violations

# Use in custom runner
class CustomRunner(TestRunner):
    def __init__(self, config=None):
        super().__init__(config)
        self.custom_analyzer = CustomAnalyzer(self._config)
    
    def analyse(self):
        report = super().analyse()
        custom_violations = self.custom_analyzer.analyse(self._tree_extractor.extract(self._root))
        report[\"custom_violations\"] = custom_violations
        return report
```

## Adding Container Types

Support custom container widgets:

```python
from customtkinter_validator.core.config import ValidatorConfig

config = ValidatorConfig(
    container_widget_types={
        # Standard types
        \"CTk\", \"CTkFrame\", \"CTkToplevel\",
        # Add your custom containers
        \"MyCustomContainer\",
        \"MyDashboardFrame\",
        \"MyTabWidget\"
    }
)
```

## Next Steps

- [API Reference](api-reference.md) - Complete API documentation
- [Examples](examples.md) - See usage examples
- [Architecture](architecture.md) - Understand internals
