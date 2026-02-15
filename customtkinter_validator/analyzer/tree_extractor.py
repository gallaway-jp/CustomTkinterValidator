"""Widget-tree extractor: traverses the live widget tree and produces a fully
serialisable metadata structure for every widget.

All data is extracted via Tkinter introspection — no screenshots, no OCR,
no coordinate clicking.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Any

import customtkinter as ctk

from customtkinter_validator.core.config import ValidatorConfig
from customtkinter_validator.test_harness.widget_registry import WidgetRegistry


class TreeExtractor:
    """Extracts a complete, serialisable widget-tree structure from a live app.

    Every node in the resulting tree contains widget type, test_id, text,
    font details, colours, geometry, visibility, enabled state, parent/child
    relationships, layout manager, and padding information.
    """

    def __init__(self, registry: WidgetRegistry, config: ValidatorConfig | None = None) -> None:
        """Initialise the extractor.

        Args:
            registry: The widget registry to use for id resolution.
            config: Optional configuration overrides.
        """
        self._registry = registry
        self._config = config or ValidatorConfig()

    def extract(self, root: tk.Misc) -> dict[str, Any]:
        """Extract the full widget tree starting from *root*.

        Calls ``update_idletasks()`` to ensure geometry data is current.

        Args:
            root: The root widget.

        Returns:
            Nested dictionary representing the full widget tree.
        """
        root.update_idletasks()
        return self._extract_node(root, parent_id=None, depth=0)

    def _extract_node(self, widget: tk.Misc, parent_id: str | None, depth: int) -> dict[str, Any]:
        """Recursively extract metadata for a single widget and its children.

        Args:
            widget: The widget to extract.
            parent_id: The test_id of the parent widget.
            depth: Current recursion depth.

        Returns:
            Dictionary of widget metadata.
        """
        if depth > self._config.max_tree_depth:
            return {}

        test_id = self._registry.get_id(widget) or "unknown"
        widget_type = type(widget).__name__

        text = self._get_text(widget)
        font_info = self._get_font_info(widget)
        fg_color = self._get_text_color(widget)
        bg_color = self._get_bg_color(widget)
        geometry = self._get_geometry(widget)
        visibility = self._get_visibility(widget)
        enabled = self._get_enabled_state(widget)
        layout_info = self._get_layout_info(widget)
        placeholder = self._get_placeholder(widget)
        corner_radius = self._get_numeric_attr(widget, "corner_radius")
        border_width = self._get_numeric_attr(widget, "border_width")
        has_command = self._has_command(widget)
        has_image = self._has_image(widget)
        values = self._get_values(widget)
        detailed_layout = self._get_detailed_layout_info(widget, layout_info.get("manager"))

        children_data: list[dict[str, Any]] = []
        children_ids: list[str] = []

        if self._is_container(widget):
            user_children = self._get_user_children(widget)
            for child in user_children:
                child_data = self._extract_node(child, parent_id=test_id, depth=depth + 1)
                if child_data:
                    children_data.append(child_data)
                    children_ids.append(child_data.get("test_id", "unknown"))

        return {
            "widget_type": widget_type,
            "test_id": test_id,
            "text": text,
            "placeholder_text": placeholder,
            "font_family": font_info.get("family"),
            "font_size": font_info.get("size"),
            "font_weight": font_info.get("weight"),
            "fg_color": fg_color,
            "bg_color": bg_color,
            "width": geometry["width"],
            "height": geometry["height"],
            "x": geometry["x"],
            "y": geometry["y"],
            "abs_x": geometry["abs_x"],
            "abs_y": geometry["abs_y"],
            "visibility": visibility,
            "enabled": enabled,
            "parent_id": parent_id,
            "children_ids": children_ids,
            "children": children_data,
            "layout_manager": layout_info.get("manager"),
            "padding": layout_info.get("padding"),
            "corner_radius": corner_radius,
            "border_width": border_width,
            "has_command": has_command,
            "has_image": has_image,
            "values": values,
            "layout_detail": detailed_layout,
        }

    def _get_text(self, widget: tk.Misc) -> str | None:
        """Extract the text content of a widget.

        Supports CTkLabel, CTkButton, CTkCheckBox, CTkEntry, CTkTextbox, and
        their Tkinter equivalents.

        Args:
            widget: The widget to inspect.

        Returns:
            The text content, or ``None`` if the widget has no text.
        """
        try:
            return str(widget.cget("text"))  # type: ignore[arg-type]
        except (tk.TclError, AttributeError, ValueError):
            pass

        if hasattr(widget, "get"):
            try:
                value = widget.get()  # type: ignore[call-args]
                if isinstance(value, str):
                    return value
            except (tk.TclError, TypeError, ValueError):
                pass
            try:
                value = widget.get("1.0", tk.END)  # type: ignore[call-args]
                if isinstance(value, str):
                    return value.rstrip("\n")
            except (tk.TclError, TypeError, ValueError):
                pass

        return None

    def _get_font_info(self, widget: tk.Misc) -> dict[str, Any]:
        """Extract font family, size, and weight from a widget.

        Handles ``CTkFont`` objects, tuples, and string descriptors.

        Args:
            widget: The widget to inspect.

        Returns:
            Dictionary with ``family``, ``size``, and ``weight`` keys.
        """
        default: dict[str, Any] = {"family": None, "size": None, "weight": "normal"}

        font: Any = None
        try:
            font = widget.cget("font")  # type: ignore[arg-type]
        except (tk.TclError, AttributeError, ValueError):
            return default

        if font is None or font == "":
            return default

        if hasattr(font, "cget"):
            try:
                return {
                    "family": font.cget("family"),
                    "size": font.cget("size"),
                    "weight": font.cget("weight"),
                }
            except (tk.TclError, AttributeError):
                pass

        if isinstance(font, (list, tuple)):
            return {
                "family": font[0] if len(font) > 0 else None,
                "size": font[1] if len(font) > 1 else None,
                "weight": font[2] if len(font) > 2 else "normal",
            }

        if isinstance(font, str):
            try:
                parsed = tkfont.Font(font=font)
                return {
                    "family": parsed.cget("family"),
                    "size": parsed.cget("size"),
                    "weight": parsed.cget("weight"),
                }
            except (tk.TclError, RuntimeError):
                parts = font.split()
                return {
                    "family": parts[0] if len(parts) > 0 else None,
                    "size": _safe_int(parts[1]) if len(parts) > 1 else None,
                    "weight": parts[2] if len(parts) > 2 else "normal",
                }

        return default

    def _get_text_color(self, widget: tk.Misc) -> str | None:
        """Extract the foreground / text colour of a widget.

        For CTk widgets, resolves theme-aware colour tuples based on the
        current appearance mode.

        Args:
            widget: The widget to inspect.

        Returns:
            Hex colour string (e.g. ``"#ff0000"``), or ``None``.
        """
        for attr in ("text_color", "fg_color", "foreground", "fg"):
            color = self._try_cget_color(widget, attr)
            if color is not None:
                return color

        for private in ("_text_color", "_fg_color"):
            raw = getattr(widget, private, None)
            if raw is not None:
                resolved = self._resolve_ctk_color(widget, raw)
                if resolved is not None:
                    return resolved

        return None

    def _get_bg_color(self, widget: tk.Misc) -> str | None:
        """Extract the background colour of a widget.

        Args:
            widget: The widget to inspect.

        Returns:
            Hex colour string, or ``None``.
        """
        for attr in ("bg_color", "fg_color", "background", "bg"):
            color = self._try_cget_color(widget, attr)
            if color is not None:
                return color

        for private in ("_bg_color", "_fg_color"):
            raw = getattr(widget, private, None)
            if raw is not None:
                resolved = self._resolve_ctk_color(widget, raw)
                if resolved is not None:
                    return resolved

        return None

    def _try_cget_color(self, widget: tk.Misc, option: str) -> str | None:
        """Attempt to read a colour option via ``cget`` and resolve it.

        Args:
            widget: The widget.
            option: The configuration option name.

        Returns:
            Resolved hex colour, or ``None``.
        """
        try:
            raw = widget.cget(option)  # type: ignore[arg-type]
        except (tk.TclError, AttributeError, ValueError):
            return None

        if raw is None or raw == "" or raw == "transparent":
            return None

        return self._resolve_ctk_color(widget, raw)

    def _resolve_ctk_color(self, widget: tk.Misc, color: Any) -> str | None:
        """Resolve a CTk colour value to a single hex string.

        Handles tuples ``(light, dark)``, hex strings, and named colours.

        Args:
            widget: Widget instance for ``winfo_rgb`` access.
            color: The raw colour value.

        Returns:
            ``"#rrggbb"`` hex string, or ``None`` for transparent/invalid.
        """
        if color is None or color == "transparent":
            return None

        if isinstance(color, (list, tuple)):
            mode = self._get_appearance_mode()
            idx = 0 if mode == "Light" else 1
            color = color[idx] if idx < len(color) else color[0]

        if not isinstance(color, str):
            return None

        if color == "transparent":
            return None

        try:
            r, g, b = widget.winfo_rgb(color)
            return f"#{r >> 8:02x}{g >> 8:02x}{b >> 8:02x}"
        except (tk.TclError, ValueError):
            if color.startswith("#"):
                return color.lower()
            return None

    def _get_appearance_mode(self) -> str:
        """Return the current CTk appearance mode.

        Returns:
            ``"Light"`` or ``"Dark"``.
        """
        if self._config.appearance_mode:
            return self._config.appearance_mode
        try:
            return ctk.get_appearance_mode()
        except Exception:
            return "Light"

    def _get_geometry(self, widget: tk.Misc) -> dict[str, int]:
        """Extract the geometry of a widget in pixels.

        Args:
            widget: The widget to measure.

        Returns:
            Dictionary with ``x``, ``y``, ``abs_x``, ``abs_y``, ``width``, ``height``.
        """
        try:
            return {
                "x": widget.winfo_x(),
                "y": widget.winfo_y(),
                "abs_x": widget.winfo_rootx(),
                "abs_y": widget.winfo_rooty(),
                "width": widget.winfo_width(),
                "height": widget.winfo_height(),
            }
        except tk.TclError:
            return {"x": 0, "y": 0, "abs_x": 0, "abs_y": 0, "width": 0, "height": 0}

    @staticmethod
    def _get_visibility(widget: tk.Misc) -> bool:
        """Determine whether a widget is visible (mapped and viewable).

        Args:
            widget: The widget to check.

        Returns:
            ``True`` if the widget is visible.
        """
        try:
            return bool(widget.winfo_viewable())
        except tk.TclError:
            return False

    @staticmethod
    def _get_enabled_state(widget: tk.Misc) -> bool:
        """Determine whether a widget is in the enabled (normal) state.

        Args:
            widget: The widget to check.

        Returns:
            ``True`` if the widget is enabled.
        """
        try:
            state = widget.cget("state")  # type: ignore[arg-type]
            if isinstance(state, str):
                return state.lower() not in ("disabled", "readonly")
            return True
        except (tk.TclError, AttributeError, ValueError):
            return True

    def _get_layout_info(self, widget: tk.Misc) -> dict[str, Any]:
        """Extract the layout manager type and padding for a widget.

        Args:
            widget: The widget to inspect.

        Returns:
            Dictionary with ``manager`` and ``padding`` keys.
        """
        manager: str | None = None
        padding: dict[str, int] = {"padx": 0, "pady": 0, "ipadx": 0, "ipady": 0}

        try:
            mgr = widget.winfo_manager()
            if mgr:
                manager = mgr
        except tk.TclError:
            pass

        if manager == "grid":
            try:
                info: dict[str, Any] = widget.grid_info()  # type: ignore[assignment]
                padding = {
                    "padx": _parse_pad(info.get("padx", 0)),
                    "pady": _parse_pad(info.get("pady", 0)),
                    "ipadx": _parse_pad(info.get("ipadx", 0)),
                    "ipady": _parse_pad(info.get("ipady", 0)),
                }
            except tk.TclError:
                pass
        elif manager == "pack":
            try:
                info: dict[str, Any] = widget.pack_info()  # type: ignore[assignment]
                padding = {
                    "padx": _parse_pad(info.get("padx", 0)),
                    "pady": _parse_pad(info.get("pady", 0)),
                    "ipadx": _parse_pad(info.get("ipadx", 0)),
                    "ipady": _parse_pad(info.get("ipady", 0)),
                }
            except tk.TclError:
                pass

        return {"manager": manager, "padding": padding}

    def _get_user_children(self, widget: tk.Misc) -> list[tk.Misc]:
        """Return user-added children, filtering out CTk internal widgets.

        Args:
            widget: The parent widget.

        Returns:
            Filtered list of child widgets.
        """
        try:
            all_children = widget.winfo_children()
        except tk.TclError:
            return []

        internal_ids: set[int] = set()
        for attr_name in self._config.internal_attr_names:
            obj = getattr(widget, attr_name, None)
            if obj is not None and isinstance(obj, tk.Misc):
                internal_ids.add(id(obj))

        result: list[tk.Misc] = []
        for child in all_children:
            if id(child) in internal_ids:
                continue
            try:
                if not child.winfo_exists():
                    continue
            except tk.TclError:
                continue
            # Include all user children, whether or not they're in the registry
            result.append(child)
        return result

    @staticmethod
    def _get_placeholder(widget: tk.Misc) -> str | None:
        """Extract placeholder text from an entry widget.

        Args:
            widget: The widget to inspect.

        Returns:
            Placeholder text, or ``None``.
        """
        for attr in ("_placeholder_text", "placeholder_text"):
            val = getattr(widget, attr, None)
            if val and isinstance(val, str):
                return val
        try:
            return str(widget.cget("placeholder_text"))  # type: ignore[arg-type]
        except (tk.TclError, AttributeError, ValueError):
            pass
        return None

    @staticmethod
    def _get_numeric_attr(widget: tk.Misc, attr: str) -> int | None:
        """Read a numeric configuration attribute.

        Args:
            widget: The widget to inspect.
            attr: The attribute name (e.g. ``'corner_radius'``).

        Returns:
            Integer value, or ``None``.
        """
        try:
            val = widget.cget(attr)  # type: ignore[arg-type]
            if val is not None:
                return int(val)
        except (tk.TclError, AttributeError, ValueError, TypeError):
            pass
        raw = getattr(widget, f"_{attr}", None)
        if raw is not None:
            try:
                return int(raw)
            except (ValueError, TypeError):
                pass
        return None

    @staticmethod
    def _has_command(widget: tk.Misc) -> bool:
        """Check whether a widget has a command/callback bound.

        Args:
            widget: The widget to inspect.

        Returns:
            ``True`` if a command is bound.
        """
        cmd = getattr(widget, "_command", None)
        if cmd is not None:
            return True
        try:
            cmd_str = widget.cget("command")  # type: ignore[arg-type]
            if cmd_str and str(cmd_str).strip():
                return True
        except (tk.TclError, AttributeError, ValueError):
            pass
        return False

    @staticmethod
    def _has_image(widget: tk.Misc) -> bool:
        """Check whether a widget has an image configured.

        Args:
            widget: The widget to inspect.

        Returns:
            ``True`` if an image is present.
        """
        img = getattr(widget, "_image", None)
        if img is not None:
            return True
        try:
            img_val = widget.cget("image")  # type: ignore[arg-type]
            if img_val and str(img_val).strip():
                return True
        except (tk.TclError, AttributeError, ValueError):
            pass
        return False

    @staticmethod
    def _get_values(widget: tk.Misc) -> list[str] | None:
        """Extract selectable values from combo/option-menu widgets.

        Args:
            widget: The widget to inspect.

        Returns:
            List of value strings, or ``None``.
        """
        raw = getattr(widget, "_values", None)
        if raw is not None and isinstance(raw, (list, tuple)):
            return [str(v) for v in raw]
        try:
            val = widget.cget("values")  # type: ignore[arg-type]
            if val and isinstance(val, (list, tuple)):
                return [str(v) for v in val]
        except (tk.TclError, AttributeError, ValueError):
            pass
        return None

    @staticmethod
    def _get_detailed_layout_info(widget: tk.Misc, manager: str | None) -> dict[str, Any] | None:
        """Extract detailed grid/pack placement parameters.

        Args:
            widget: The widget to inspect.
            manager: Layout manager name (``'grid'``, ``'pack'``, or ``'place'``).

        Returns:
            Dictionary of layout details, or ``None``.
        """
        if manager == "grid":
            try:
                info = widget.grid_info()
                return {
                    "row": int(info.get("row", 0)),
                    "column": int(info.get("column", 0)),
                    "rowspan": int(info.get("rowspan", 1)),
                    "columnspan": int(info.get("columnspan", 1)),
                    "sticky": str(info.get("sticky", "")),
                }
            except (tk.TclError, ValueError):
                pass
        elif manager == "pack":
            try:
                info = widget.pack_info()
                return {
                    "side": str(info.get("side", "top")),
                    "fill": str(info.get("fill", "none")),
                    "expand": bool(int(info.get("expand", 0))),
                    "anchor": str(info.get("anchor", "center")),
                }
            except (tk.TclError, ValueError):
                pass
        elif manager == "place":
            try:
                info = widget.place_info()
                return {
                    "relx": float(info.get("relx", 0)),
                    "rely": float(info.get("rely", 0)),
                    "relwidth": float(info.get("relwidth", 0)),
                    "relheight": float(info.get("relheight", 0)),
                    "anchor": str(info.get("anchor", "nw")),
                }
            except (tk.TclError, ValueError):
                pass
        return None

    def _is_container(self, widget: tk.Misc) -> bool:
        """Check whether a widget is a container that holds user children.

        Checks the widget's class name and all its base classes to support
        custom classes that inherit from container types.

        Args:
            widget: The widget to check.

        Returns:
            ``True`` if the widget is a container type.
        """
        # Check the widget's class and all its base classes
        for cls in type(widget).__mro__:
            if cls.__name__ in self._config.container_widget_types:
                return True
        return False


def _parse_pad(value: Any) -> int:
    """Parse a Tkinter padding value to an integer.

    Handles integers, strings, and tuples ``(left, right)`` by returning
    the maximum.

    Args:
        value: The raw padding value.

    Returns:
        Integer pixel value.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    if isinstance(value, (list, tuple)):
        try:
            return max(int(v) for v in value)
        except (ValueError, TypeError):
            return 0
    return 0


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int, returning ``None`` on failure.

    Args:
        value: The value to convert.

    Returns:
        Integer or ``None``.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
