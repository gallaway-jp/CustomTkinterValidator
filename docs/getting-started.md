# Getting Started

## Installation

### From Source

```bash
git clone https://github.com/gallaway-jp/CustomTkinterValidator
cd CustomTkinterValidator
pip install -e .
```

### Dependencies

The validator requires:
- Python 3.12 or higher
- CustomTkinter 5.2 or higher

All dependencies are automatically installed via `pip install -e .`

## Your First Test

### 1. Create a Simple App

Create `my_app.py`:

```python
import customtkinter as ctk

def create_app():
    """Factory function that returns the app (without calling mainloop)."""
    app = ctk.CTk()
    app.title("My First App")
    app.geometry("400x300")
    
    # Add some widgets
    label = ctk.CTkLabel(app, text="Welcome!")
    label.pack(pady=20)
    
    entry = ctk.CTkEntry(app, placeholder_text="Enter your name")
    entry.pack(pady=10)
    
    button = ctk.CTkButton(app, text="Submit")
    button.pack(pady=10)
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.mainloop()
```

### 2. Create a Test Script

Create `test_my_app.py`:

```python
from pathlib import Path
from customtkinter_validator.core.runner import TestRunner
from my_app import create_app

def test_script(sim):
    """Define user interactions to test."""
    # Simulate typing in the entry field
    sim.type_text("CTkEntry_0", "John Doe")
    
    # Click the button
    sim.click("CTkButton_0")

if __name__ == "__main__":
    runner = TestRunner()
    
    # Run headless validation
    runner.run_headless(
        app_factory=create_app,
        script=test_script,
        output_path=Path("my_app_report.json")
    )
    
    print("✓ Validation complete! Check my_app_report.json")
```

### 3. Run the Test

```bash
python test_my_app.py
```

### 4. View the Report

```bash
# Pretty-print the JSON
python -m json.tool my_app_report.json

# Or view specific sections
python -c "
import json
data = json.load(open('my_app_report.json'))
print('Score:', data['summary_score']['overall_score'])
print('Issues:', len(data['contrast_issues']), 'contrast,',
                 len(data['accessibility_issues']), 'accessibility')
"
```

## Understanding the Output

The report contains:

### Widget Tree
Complete hierarchy of your UI:
```json
{
  "widget_type": "CTk",
  "test_id": "CTk_root",
  "children": [
    {
      "widget_type": "CTkLabel",
      "test_id": "CTkLabel_0",
      "text": "Welcome!",
      "fg_color": "#DCE4EE",
      "bg_color": "#242424"
    }
  ]
}
```

### Contrast Issues
WCAG 2.1 violations:
```json
{
  "widget_id": "status_label",
  "fg_color": "#555555",
  "bg_color": "#444444",
  "contrast_ratio": 1.90,
  "required_ratio": 4.5,
  "severity": "critical"
}
```

### Accessibility Issues
```json
{
  "rule_id": "missing_label",
  "widget_id": "email_entry",
  "severity": "high",
  "description": "Entry widget has no associated label"
}
```

### Layout Violations
```json
{
  "rule_id": "alignment_inconsistency",
  "widget_id": "submit_btn",
  "measured_value": {"abs_x": 150},
  "threshold": {"expected_x": 145},
  "severity": "low"
}
```

### Summary Scores
```json
{
  "layout_score": 75.0,
  "accessibility_score": 85.0,
  "interaction_score": 100.0,
  "overall_score": 86.0
}
```

## Using Test IDs

### Auto-Generated IDs
By default, widgets get hierarchical IDs like:
- `CTk_root`
- `CTk_root.CTkFrame_0`
- `CTk_root.CTkFrame_0.CTkButton_1`

### Explicit IDs (Recommended)
Use the `TestableWidget` mixin or wrapper classes:

```python
from customtkinter_validator.widgets.base import TButton, TEntry, TLabel

# Instead of:
# button = ctk.CTkButton(app, text="Submit")

# Use:
button = TButton(app, text="Submit", test_id="submit_btn")
entry = TEntry(app, test_id="email_entry")
label = TLabel(app, text="Email:", test_id="email_label")

# Now you can reference them by name:
sim.click("submit_btn")
sim.type_text("email_entry", "user@example.com")
```

## Common Patterns

### Testing Forms

```python
def test_registration_form(sim):
    # Fill out the form
    sim.type_text("name_field", "Alice Johnson")
    sim.type_text("email_field", "alice@example.com")
    sim.type_text("password_field", "SecurePass123!")
    
    # Check the agreement checkbox
    sim.click("agree_checkbox")
    
    # Submit
    sim.click("submit_button")
```

### Testing Navigation

```python
def test_tab_navigation(sim):
    # Tab through fields
    sim.focus("first_field")
    sim.tab("first_field")
    sim.tab("second_field")
    sim.tab("third_field")
```

### Testing Hover Effects

```python
def test_tooltips(sim):
    sim.hover("help_icon")
    sim.hover("info_button")
```

## Step-by-Step Validation

You can also run validation step-by-step:

```python
runner = TestRunner()

# 1. Attach the app
app = create_app()
runner.set_app(app)

# 2. Inject test IDs
widget_count = runner.inject()
print(f"Registered {widget_count} widgets")

# 3. Simulate interactions
def my_script(sim):
    sim.click("submit_btn")

runner.simulate(my_script)

# 4. Analyze
report = runner.analyse()

# 5. Save
runner.save_report("my_report.json")

# 6. Clean up
app.destroy()
```

## CLI Usage

```bash
# Run validation from command line
python -m customtkinter_validator \
    --app examples.sample_app \
    --output report.json \
    --print
```

## Troubleshooting

### "No module named 'customtkinter_validator'"
Make sure you installed with `pip install -e .` from the project root.

### "AttributeError: 'CTkButton' object has no attribute '_test_id'"
This is normal - the validator auto-generates IDs. Use explicit test_id only if you need predictable names.

### "Empty focus chain" warning
This happens when no widgets accept keyboard focus (e.g., all labels). Not necessarily an error.

### Widget not detected
- Ensure the widget is actually created before analysis
- Check that it's a child of a container widget (Frame, CTk, etc.)
- Verify `app.update_idletasks()` was called (done automatically in `run_headless`)

## Next Steps

- [Learn the architecture](architecture.md)
- [Explore the API](api-reference.md)
- [See more examples](examples.md)
- [Customize configuration](configuration.md)
- [Add custom rules](extending.md)
