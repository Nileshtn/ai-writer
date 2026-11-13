"""Writing surface: multiline editor control and layout wrapper.

This module owns the primary text input widget. The same ``TextField`` instance
is created once and shared with :mod:`ui.menubar` so menu actions (cut, paste,
zoom) target the live document.
"""

import flet as ft

# Default editor typography; kept here so canvas layout and menubar zoom stay in sync.
DEFAULT_EDITOR_TEXT_SIZE = 18


def create_editor() -> ft.TextField:
    """Create the main multiline writing control.

    Returns:
        A configured Flet ``TextField`` with no border, multiline input,
        autofocus, and Shift+Enter for new lines.

    Note:
        Callers should hold a single instance for the app lifetime and pass it
        to :func:`build_writing_canvas` and :func:`ui.menubar.build_menubar`.
    """
    return ft.TextField(
        multiline=True,
        expand=True,
        autofocus=True,
        hint_text="Start writing...",
        border=ft.InputBorder.NONE,
        text_size=DEFAULT_EDITOR_TEXT_SIZE,
        keyboard_type=ft.KeyboardType.MULTILINE,
        shift_enter=True,
    )


def build_writing_canvas(editor: ft.TextField) -> ft.Control:
    """Wrap the editor in a padded, full-height writing area.

    Args:
        editor: The shared document ``TextField`` from :func:`create_editor`.

    Returns:
        A ``SafeArea`` subtree that expands to fill remaining space below the
        menu bar.
    """
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.symmetric(horizontal=24, vertical=16),
            content=editor,
        ),
    )
