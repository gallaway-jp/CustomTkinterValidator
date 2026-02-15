# CustomTkinter Validator Documentation

## Overview

CustomTkinter Validator is a comprehensive AI-native GUI testing and UX validation framework for CustomTkinter applications. It uses widget-tree introspection (no screenshots or OCR) to analyze applications and generate structured JSON reports optimized for AI agent consumption.

## Key Features

- **Widget Tree Introspection**: Analyzes complete widget hierarchies without screenshots
- **WCAG 2.1 Compliance**: Validates contrast ratios using official luminance formulas
- **Accessibility Checking**: Detects missing labels, focus chain issues, disabled actions
- **Layout Analysis**: Identifies spacing, alignment, symmetry, and overlap issues
- **Event Simulation**: Deterministic, replayable user interactions
- **JSON Reports**: Structured output optimized for AI agent evaluation
- **Zero Configuration**: Works out-of-the-box on any CustomTkinter app

## Quick Links

- [Getting Started](getting-started.md) - Installation and first test
- [Architecture](architecture.md) - System design and components
- [API Reference](api-reference.md) - Complete API documentation
- [Examples](examples.md) - Usage examples and patterns
- [Configuration](configuration.md) - Customization options
- [Extending](extending.md) - Adding custom rules and checks
- [AI Integration](ai-integration.md) - Using with AI agents

## Use Cases

### 1. Automated UX Validation
Run validation as part of CI/CD to catch accessibility and layout issues before deployment.

### 2. AI-Powered Code Review
Feed JSON reports to AI agents for contextual UX recommendations and automated fixes.

### 3. Regression Testing
Establish baselines and detect UX regressions across releases.

### 4. Accessibility Audits
Ensure WCAG compliance and keyboard navigability.

### 5. Comparative Analysis
Compare UX metrics across different applications or versions.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CustomTkinter App                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Widget Tree Injector                        │
│         (Assigns test_id to every widget)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Event Simulator (Optional)                   │
│         (Clicks, typing, focus, hover, tab)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Analyzers                                 │
│  ┌──────────────┬──────────────┬──────────────────────┐    │
│  │ Tree         │ Layout       │ Contrast             │    │
│  │ Extractor    │ Metrics      │ Checker              │    │
│  └──────────────┴──────────────┴──────────────────────┘    │
│  ┌──────────────┬──────────────┬──────────────────────┐    │
│  │ Accessibility │ UX           │ Consistency          │    │
│  │ Checker       │ Analyzer     │ Checker              │    │
│  └──────────────┴──────────────┴──────────────────────┘    │
│  ┌──────────────┐                                          │
│  │ Rule Engine  │                                          │
│  └──────────────┘                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  JSON Serializer                             │
│         (Canonical report with scores)                       │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

- **Python 3.12+**: Modern Python with dataclasses and type hints
- **CustomTkinter 5.2+**: Target UI library
- **Tkinter**: Low-level introspection via `winfo_*` methods
- **WCAG 2.1**: Contrast ratios for AA (4.5:1), AAA (7:1), and non-text (3:1)

## Design Principles

1. **Widget-Tree Only**: No screenshots, OCR, or coordinate clicking
2. **Deterministic**: Same app state → same report (reproducible)
3. **AI-Optimized**: JSON structure designed for LLM reasoning
4. **Zero-Config**: Works on any CustomTkinter app immediately
5. **Extensible**: Easy to add custom rules and checks

## Quick Start

```python
from customtkinter_validator.core.runner import TestRunner

def app_factory():
    import customtkinter as ctk
    app = ctk.CTk()
    # ... build your UI ...
    return app

def test_script(sim):
    sim.click("submit_button")
    sim.type_text("username_field", "test@example.com")

runner = TestRunner()
runner.run_headless(
    app_factory=app_factory,
    script=test_script,
    output_path="report.json"
)
```

## Report Structure

```json
{
  "metadata": {
    "tool": "CustomTkinter Validator",
    "version": "2.0.0",
    "timestamp": "2026-02-15T12:00:00+00:00",
    "tab_order": ["widget1", "widget2", ...]
  },
  "widget_tree": { ... },
  "layout_violations": [ ... ],
  "contrast_issues": [ ... ],
  "accessibility_issues": [ ... ],
  "ux_issues": [ ... ],
  "consistency_issues": [ ... ],
  "rule_violations": [ ... ],
  "interaction_results": [ ... ],
  "summary_score": {
    "layout_score": 75.0,
    "accessibility_score": 85.0,
    "ux_score": 70.0,
    "interaction_score": 100.0,
    "overall_score": 82.0
  }
}
```

## Next Steps

1. [Install and run your first test](getting-started.md)
2. [Understand the architecture](architecture.md)
3. [Explore the API](api-reference.md)
4. [See examples](examples.md)
5. [Configure validation rules](configuration.md)
