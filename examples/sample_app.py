"""Sample CustomTkinter application with intentional UX issues.

This application demonstrates a user registration form with several
deliberately introduced defects for the validator to detect:

1. **Contrast issue**: The status label uses light grey text on a light
   background, violating WCAG AA contrast requirements.

2. **Spacing issue**: The Submit and Reset buttons have insufficient padding
   between them.

3. **Tab order issue**: The Close button has ``takefocus=False``, making it
   unreachable via keyboard navigation.

4. **Disabled primary action**: The Reset button is disabled despite being
   a primary-looking action.

5. **Missing label**: The notes entry in the footer has no associated label.
"""

from __future__ import annotations

import customtkinter as ctk

from customtkinter_validator.widgets.base import (
    TButton,
    TCheckBox,
    TEntry,
    TFrame,
    TLabel,
)


def create_app() -> ctk.CTk:
    """Create and return the sample application root window.

    Returns the root window **without** calling ``mainloop()`` so that the
    test runner can drive the event loop programmatically.

    Returns:
        The configured ``CTk`` root window.
    """
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Sample Registration Form")
    app.geometry("480x620")
    app.resizable(False, False)

    _build_ui(app)
    return app


def _build_ui(app: ctk.CTk) -> None:
    """Construct all UI elements inside the root window.

    Args:
        app: The root window.
    """
    heading = TLabel(
        app,
        test_id="heading_label",
        text="User Registration",
        font=ctk.CTkFont(size=22, weight="bold"),
    )
    heading.pack(pady=(20, 10))

    form_frame = TFrame(app, test_id="form_frame")
    form_frame.pack(padx=30, pady=10, fill="x")

    _add_field(form_frame, "name", "Full Name:", row=0)
    _add_field(form_frame, "email", "Email:", row=1)
    _add_field(form_frame, "password", "Password:", row=2, show="*")

    agree_cb = TCheckBox(
        form_frame,
        test_id="agree_checkbox",
        text="I agree to the Terms and Conditions",
    )
    agree_cb.grid(row=3, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")

    button_frame = TFrame(app, test_id="button_frame")
    button_frame.pack(padx=30, pady=(5, 5), fill="x")

    submit_btn = TButton(
        button_frame,
        test_id="submit_btn",
        text="Submit",
        command=lambda: _on_submit(app),
    )
    submit_btn.pack(side="left", padx=(10, 2), pady=5)

    reset_btn = TButton(
        button_frame,
        test_id="reset_btn",
        text="Reset",
        state="disabled",
    )
    reset_btn.pack(side="left", padx=(1, 10), pady=5)

    error_label = TLabel(
        app,
        test_id="error_label",
        text="",
        text_color="red",
        font=ctk.CTkFont(size=12),
    )
    error_label.pack(padx=30, pady=(0, 5))

    footer_frame = TFrame(app, test_id="footer_frame")
    footer_frame.pack(padx=30, pady=(10, 5), fill="x")

    status_label = TLabel(
        footer_frame,
        test_id="status_label",
        text="Status: Ready",
        text_color="#555555",
        fg_color="#444444",
        font=ctk.CTkFont(size=11),
    )
    status_label.pack(padx=10, pady=5, fill="x")

    # --- Issue: notes_entry in its own frame with NO label ---
    notes_frame = TFrame(app, test_id="notes_frame")
    notes_frame.pack(padx=30, pady=(0, 5), fill="x")

    notes_entry = TEntry(
        notes_frame,
        test_id="notes_entry",
        placeholder_text="Additional notes...",
    )
    notes_entry.pack(padx=10, pady=(0, 5), fill="x")

    close_btn = TButton(
        footer_frame,
        test_id="close_btn",
        text="Close",
        command=app.destroy,
    )
    close_btn.pack(padx=10, pady=(0, 10))
    # Set takefocus via the underlying Tk layer to create a tab-order issue
    try:
        close_btn._canvas.configure(takefocus=False)  # type: ignore[union-attr]
    except (AttributeError, Exception):
        pass


def _add_field(
    parent: TFrame,
    name: str,
    label_text: str,
    row: int,
    show: str | None = None,
) -> None:
    """Add a label + entry row to the form grid.

    Args:
        parent: The parent frame.
        name: Base name for test_ids.
        label_text: Text for the label.
        row: Grid row index.
        show: Character mask for password fields.
    """
    label = TLabel(parent, test_id=f"{name}_label", text=label_text)
    label.grid(row=row, column=0, padx=(10, 5), pady=8, sticky="e")

    kwargs: dict[str, object] = {"placeholder_text": f"Enter {name}..."}
    if show is not None:
        kwargs["show"] = show

    entry = TEntry(parent, test_id=f"{name}_entry", **kwargs)  # type: ignore[arg-type]
    entry.grid(row=row, column=1, padx=(5, 10), pady=8, sticky="ew")

    parent.grid_columnconfigure(1, weight=1)


def _on_submit(app: ctk.CTk) -> None:
    """Handle the Submit button click.

    Args:
        app: The root window (used to look up child widgets).
    """
    pass


if __name__ == "__main__":
    root = create_app()
    root.mainloop()
