# Examples

## Basic Examples

### Example 1: Minimal Validation

```python
import customtkinter as ctk
from customtkinter_validator.core.runner import TestRunner

def create_app():
    app = ctk.CTk()
    app.title("Hello World")
    
    label = ctk.CTkLabel(app, text="Hello, World!")
    label.pack(pady=20)
    
    return app

# Run validation
runner = TestRunner()
report = runner.run_headless(
    app_factory=create_app,
    script=None,  # No interactions
    output_path="hello_report.json"
)

print(f"Overall score: {report['summary_score']['overall_score']}")
```

### Example 2: Testing a Form

```python
from customtkinter_validator.widgets.base import TFrame, TLabel, TEntry, TButton

def create_login_form():
    app = ctk.CTk()
    app.geometry("400x300")
    
    frame = TFrame(app, test_id="main_frame")
    frame.pack(padx=20, pady=20, fill="both", expand=True)
    
    # Username
    TLabel(frame, text="Username:", test_id="username_label").pack(pady=(10, 0))
    TEntry(frame, test_id="username_entry").pack(pady=(5, 10))
    
    # Password
    TLabel(frame, text="Password:", test_id="password_label").pack(pady=(10, 0))
    TEntry(frame, show="*", test_id="password_entry").pack(pady=(5, 10))
    
    # Submit
    TButton(frame, text="Login", test_id="login_btn").pack(pady=20)
    
    return app

def test_login(sim):
    sim.type_text("username_entry", "admin")
    sim.tab("username_entry")
    sim.type_text("password_entry", "password123")
    sim.click("login_btn")

runner = TestRunner()
report = runner.run_headless(
    app_factory=create_login_form,
    script=test_login,
    output_path="login_report.json"
)
```

See [complete examples on GitHub](https://github.com/gallaway-jp/CustomTkinterValidator/tree/main/examples).

## Next Steps

- [API Reference](api-reference.md)
- [Configuration](configuration.md) 
- [Extending](extending.md)
- [AI Integration](ai-integration.md)
