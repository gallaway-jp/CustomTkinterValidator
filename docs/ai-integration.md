# AI Integration Guide

## Overview

CustomTkinter Validator is designed from the ground up for AI agent consumption. The JSON output is structured to enable AI models to:

1. **Understand the UI structure** via complete widget trees
2. **Identify UX issues** with severity ratings and fix recommendations
3. **Generate contextual fixes** using widget metadata and spatial relationships
4. **Validate fixes** by re-running analysis and comparing scores

## AI Agent Workflow

```
┌──────────────────────────────────────────────────────────┐
│  1. AI receives CustomTkinter source code                │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│  2. AI runs validator to get JSON report                 │
│     • Widget tree structure                              │
│     • Issue list with severities                         │
│     • Baseline scores                                    │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│  3. AI analyzes report and generates fixes               │
│     • Contrast: Change colors to meet WCAG               │
│     • Layout: Adjust padding/alignment                   │
│     • Accessibility: Add labels, fix tab order           │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│  4. AI applies fixes to source code                      │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│  5. AI re-runs validator to verify improvements          │
│     • Compare scores before/after                        │
│     • Verify issues resolved                             │
└──────────────────────────────────────────────────────────┘
```

## JSON Structure for AI Reasoning

### Widget Tree - Understanding the UI

```json
{
  "widget_tree": {
    "widget_type": "CTk",
    "test_id": "CTk_root",
    "text": null,
    "font_family": null,
    "font_size": null,
    "fg_color": "#242424",
    "bg_color": "#242424",
    "width": 720,
    "height": 500,
    "x": 100,
    "y": 100,
    "abs_x": 100,
    "abs_y": 100,
    "visibility": true,
    "enabled": true,
    "parent_id": null,
    "children_ids": ["heading", "form_frame", "submit_btn"],
    "children": [
      {
        "widget_type": "CTkLabel",
        "test_id": "heading",
        "text": "User Registration",
        "font_family": "Roboto",
        "font_size": 24,
        "fg_color": "#DCE4EE",
        "bg_color": "#242424"
      }
    ]
  }
}
```

**AI can extract:**
- Widget hierarchy (parent-child relationships)
- Visual properties (colors, fonts, dimensions)
- Spatial layout (absolute positions)
- Text content and labels
- State (visibility, enabled/disabled)

### Issues - Identifying Problems

Each issue includes:
- `rule_id`: Machine-readable identifier
- `widget_id`: Which widget has the problem
- `severity`: "critical" | "high" | "medium" | "low"
- `description`: Human-readable explanation
- `recommended_fix`: Actionable suggestion
- Context data (measured values, thresholds)

#### Contrast Issue Example

```json
{
  "rule_id": "insufficient_contrast",
  "widget_id": "status_label",
  "severity": "critical",
  "fg_color": "#555555",
  "bg_color": "#444444",
  "contrast_ratio": 1.90,
  "required_ratio": 4.5,
  "description": "'status_label' has contrast ratio 1.90:1 (required: 4.5:1)",
  "recommended_fix": "Increase brightness difference between #555555 and #444444"
}
```

**AI action:**
```python
# Before (ratio 1.90:1)
status_label = CTkLabel(fg_color="#555555", bg_color="#444444")

# After (ratio 5.12:1)
status_label = CTkLabel(fg_color="#CCCCCC", bg_color="#333333")
```

#### Accessibility Issue Example

```json
{
  "rule_id": "missing_label",
  "widget_id": "email_entry",
  "severity": "high",
  "description": "Entry widget 'email_entry' has no associated label",
  "recommended_fix": "Add a descriptive label widget as a sibling"
}
```

**AI action:**
```python
# Before
email_entry = TEntry(form, test_id="email_entry")

# After
email_label = TLabel(form, text="Email:", test_id="email_label")
email_entry = TEntry(form, test_id="email_entry")
```

#### Layout Issue Example

```json
{
  "rule_id": "alignment_inconsistency",
  "widget_id": "submit_btn",
  "severity": "low",
  "measured_value": {"abs_x": 150},
  "threshold": {"expected_x": 145, "tolerance": 2},
  "description": "Widget is misaligned with siblings (x=150, expected ~145)"
}
```

**AI action:**
```python
# Adjust grid/pack parameters to align buttons
submit_btn.grid(row=5, column=0, sticky="ew", padx=(145, 0))
```

### Scores - Measuring Improvement

```json
{
  "summary_score": {
    "layout_score": 45.0,      // 0-100, based on violation count & severity
    "accessibility_score": 60.0,
    "interaction_score": 100.0,
    "overall_score": 66.0       // Weighted average
  }
}
```

**AI can:**
- Establish baseline before fixes
- Verify improvements after fixes
- Prioritize high-impact issues (critical severity, low scores)

## AI Prompt Templates

### 1. Initial Analysis

```
You are a UX expert analyzing a CustomTkinter application.

INPUT:
- Source code: [app.py]
- Validation report: [report.json]

TASK:
1. Read the widget_tree to understand the UI structure
2. List all issues grouped by category (contrast, accessibility, layout)
3. Prioritize issues by severity (critical > high > medium > low)
4. For each issue, explain:
   - What's wrong
   - Why it matters for UX/accessibility
   - How to fix it

OUTPUT:
Structured analysis with prioritized fix recommendations.
```

### 2. Automated Fixing

```
You are a code refactoring agent.

INPUT:
- Source code: [app.py]
- Validation report showing:
  - 2 contrast issues (critical)
  - 1 missing label (high)
  - 5 alignment issues (low)

TASK:
Generate a fixed version of app.py that resolves all critical and high severity issues.

CONSTRAINTS:
- Maintain exact functionality
- Only change visual/layout properties
- Add missing labels/widgets as needed
- Ensure WCAG 2.1 compliance (4.5:1 contrast for normal text)

OUTPUT:
Complete fixed source code.
```

### 3. Verification

```
You are a QA engineer validating UX fixes.

INPUT:
- Baseline report: [before.json] - Overall score: 52.0
- Updated report: [after.json] - Overall score: 85.0

TASK:
1. Compare scores category by category
2. Verify all critical/high issues resolved
3. Check for any new issues introduced
4. Confirm improvement: +33 points overall

OUTPUT:
Verification summary with pass/fail status.
```

## AI Code Generation Patterns

### Pattern 1: Contrast Fixes

**From report:**
```json
{
  "widget_id": "error_label",
  "fg_color": "#666666",
  "bg_color": "#555555",
  "contrast_ratio": 1.21,
  "required_ratio": 4.5
}
```

**AI generates:**
```python
# Calculate acceptable colors
# Using WCAG formula: need min 4.5:1 ratio
# Background #555555 (L=0.106)
# Foreground needs L=0.106*4.5-0.05 = 0.427 minimum
# RGB(217, 217, 217) = #D9D9D9 gives 4.56:1 ✓

error_label.configure(fg_color="#D9D9D9")  # Now 4.56:1
```

### Pattern 2: Label Association

**From report:**
```json
{
  "rule_id": "missing_label",
  "widget_id": "password_entry"
}
```

**AI generates:**
```python
# Find the entry in source
# password_entry = TEntry(form_frame, test_id="password_entry")

# Insert label before it
password_label = TLabel(
    form_frame, 
    text="Password:", 
    test_id="password_label"
)
password_label.grid(row=2, column=0, sticky="w", padx=10, pady=(10, 0))
password_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=(10, 5))
```

### Pattern 3: Layout Alignment

**From report:**
```json
{
  "rule_id": "alignment_inconsistency",
  "widget_id": "reset_btn",
  "measured_value": {"abs_x": 310},
  "sibling_x_values": [300, 300, 310]
}
```

**AI generates:**
```python
# Align reset_btn with siblings at x=300
# Add consistent padx to all buttons in the button_frame

for btn in [submit_btn, cancel_btn, reset_btn]:
    btn.grid(sticky="ew", padx=(300-btn_frame.winfo_x(), 10))
```

## Advanced AI Scenarios

### Scenario 1: Theme-Aware Fixes

AI can detect appearance mode and generate fixes that work in both light/dark themes:

```python
# Report shows contrast issue in dark mode only
# AI generates tuple-based colors:

label.configure(
    fg_color=("#333333", "#EEEEEE"),  # (light mode, dark mode)
    bg_color=("#FFFFFF", "#1a1a1a")
)
```

### Scenario 2: Form Layout Optimization

AI can use widget tree spatial data to:
1. Detect form patterns (label-entry pairs)
2. Calculate optimal grid alignment
3. Generate consistent spacing

```python
# AI detects labels at various x positions: [10, 12, 15, 10]
# Generates consistent layout:

for i, (label, entry) in enumerate(form_fields):
    label.grid(row=i, column=0, sticky="w", padx=10, pady=5)
    entry.grid(row=i, column=1, sticky="ew", padx=10, pady=5)
```

### Scenario 3: Accessibility Enhancement

AI can use tab_order data to fix keyboard navigation:

```json
{
  "tab_order": ["name_entry", "submit_btn", "email_entry"]
}
```

AI detects logical error (email should come before submit) and generates:

```python
# Set focus chain explicitly
name_entry.lift()
email_entry.lift()
submit_btn.lift()
```

## Batch Processing

AI can process multiple apps and generate comparative insights:

```python
apps = ["app1", "app2", "app3"]
reports = []

for app in apps:
    report = run_validation(app)
    reports.append(report)

# AI analyzes patterns across apps
common_issues = find_common_issues(reports)
best_practices = extract_high_scoring_patterns(reports)
```

## Integration with AI Development Workflows

### Code Review Agent
```
1. Developer commits CTk app code
2. CI runs validator automatically
3. AI reviews JSON report
4. AI posts code review comments with specific fixes
5. Developer applies suggestions
```

### Automated UX Improvement
```
1. AI agent receives legacy CTk app
2. Runs validation (baseline: score 45)
3. AI generates improved version
4. Runs validation (new score: 82)
5. AI commits improvements with documentation
```

### Design System Compliance
```
1. Define design system rules as custom validators
2. AI validates all apps against design system
3. AI generates compliance report
4. AI auto-fixes non-compliant apps
```

## Best Practices for AI Agents

1. **Always run validation before and after changes** - Establishes baseline and verifies improvement

2. **Prioritize by severity** - Fix critical/high issues first, low issues last

3. **Preserve functionality** - Only change visual/layout properties, never logic

4. **Use widget tree for context** - Understand parent-child relationships before making changes

5. **Validate incrementally** - Fix one category at a time, verify, then move to next

6. **Generate test scripts** - Create interaction scripts that exercise the fixed functionality

7. **Document changes** - Include score improvements and resolved issue counts in commit messages

## Example: Complete AI-Driven Fix

**Input Report:**
```json
{
  "summary_score": {"overall_score": 52.0},
  "contrast_issues": [
    {"widget_id": "status_label", "contrast_ratio": 1.90, "required_ratio": 4.5}
  ],
  "accessibility_issues": [
    {"rule_id": "missing_label", "widget_id": "notes_entry"}
  ]
}
```

**AI-Generated Fix:**
```python
# Before
status_label = CTkLabel(app, text="Ready", fg_color="#555555", bg_color="#444444")
notes_entry = CTkEntry(app, test_id="notes_entry")

# After
status_label = CTkLabel(app, text="Ready", fg_color="#CCCCCC", bg_color="#333333")  # 5.12:1 ✓
notes_label = CTkLabel(app, text="Notes:")
notes_entry = CTkEntry(app, test_id="notes_entry")
```

**Verification Report:**
```json
{
  "summary_score": {"overall_score": 85.0},
  "contrast_issues": [],
  "accessibility_issues": []
}
```

**AI Commit Message:**
```
fix: Improve UX score from 52.0 to 85.0

- Fixed status_label contrast ratio (1.90:1 → 5.12:1)
- Added missing label for notes_entry
- All critical and high severity issues resolved
```

## Next Steps

- [See complete examples](examples.md)
- [Learn about custom validation rules](extending.md)
- [Explore architecture details](architecture.md)
