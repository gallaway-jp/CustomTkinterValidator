# Configuration

## ValidatorConfig Options

Customize validation behavior via the `ValidatorConfig` dataclass:

```python
from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.core.runner import TestRunner

config = ValidatorConfig(
    # Contrast thresholds
    min_contrast_ratio_normal=4.5,  # WCAG AA for normal text
    min_contrast_ratio_large=3.0,   # WCAG AA for large text (18pt+)
    
    # Touch targets
    min_touch_target_px=24,          # Minimum button/clickable size
    
    # Layout
    min_padding_px=4,                # Minimum spacing
    alignment_tolerance_px=2,        # Alignment threshold
    symmetry_tolerance_px=3,         # Symmetry threshold
    
    # Tree traversal
    max_tree_depth=50,               # Maximum nesting depth
    
    # Widget type sets
    container_widget_types={
        \"CTk\", \"CTkToplevel\", \"CTkFrame\", 
        \"CTkScrollableFrame\", \"CTkTabview\",
        \"TFrame\", \"Frame\", \"LabelFrame\", 
        \"Toplevel\", \"Tk\"
    },
    
    # Internal CTk attributes to filter
    internal_attr_names=[
        \"_canvas\", \"_text_label\", \"_entry\",
        \"_textbox\", \"_check_button\", \"_switch_button\",
        \"_radiobutton\", \"_slider\", \"_option_menu\",
        \"_fg_parts\"
    ]
)

runner = TestRunner(config=config)
```

## Preset Configurations

### Strict WCAG AAA

```python
strict_config = ValidatorConfig(
    min_contrast_ratio_normal=7.0,   # AAA
    min_contrast_ratio_large=4.5,    # AAA
    min_touch_target_px=44,          # Larger targets
    min_padding_px=8,
    alignment_tolerance_px=1,
    symmetry_tolerance_px=1
)
```

### Lenient Mode

```python
lenient_config = ValidatorConfig(
    min_contrast_ratio_normal=3.0,
    min_contrast_ratio_large=2.5,
    min_touch_target_px=16,
    min_padding_px=2,
    alignment_tolerance_px=5,
    symmetry_tolerance_px=8
)
```

### Mobile-First

```python
mobile_config = ValidatorConfig(
    min_touch_target_px=48,          # iOS/Android guidelines
    min_padding_px=8,
    alignment_tolerance_px=3,
    symmetry_tolerance_px=5
)
```

## Environment Variables

Set defaults via environment:

```bash
export VALIDATOR_MIN_CONTRAST=4.5
export VALIDATOR_MIN_TOUCH_TARGET=24
export VALIDATOR_MAX_DEPTH=50
```

```python
import os
from customtkinter_validator.core.config import ValidatorConfig

config = ValidatorConfig(
    min_contrast_ratio_normal=float(os.getenv(\"VALIDATOR_MIN_CONTRAST\", \"4.5\")),
    min_touch_target_px=int(os.getenv(\"VALIDATOR_MIN_TOUCH_TARGET\", \"24\")),
    max_tree_depth=int(os.getenv(\"VALIDATOR_MAX_DEPTH\", \"50\"))
)
```

## Next Steps

- [Extending](extending.md) - Add custom rules
- [API Reference](api-reference.md) - Complete API docs
