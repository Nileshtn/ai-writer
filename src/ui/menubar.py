"""Application menu bar: File, Edit, View, Format, Tools, and Help.

Builds a full-width desktop-style ``MenuBar`` and wires actions to a shared
``TextField`` editor (clipboard, selection, zoom, dialogs). Several File and
Format entries are placeholders and show a snackbar until implemented.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import flet as ft

from ui.canvas import DEFAULT_EDITOR_TEXT_SIZE

# Minimum width of each dropdown row (label + shortcut column).
_MENU_WIDTH = 240
# Zoom bounds for View menu; step is applied per Zoom In/Out click.
_MIN_TEXT_SIZE = 12
_MAX_TEXT_SIZE = 18
_ZOOM_STEP = 2


def _toast(page: ft.Page, message: str) -> None:
    """Show a brief snackbar message on the page.

    Args:
        page: Active Flet page used as the dialog host.
        message: User-visible text.
    """
    page.show_dialog(ft.SnackBar(ft.Text(message)))


def _selected_range(editor: ft.TextField) -> tuple[int, int]:
    """Return the start and end indices of the current selection or caret.

    Args:
        editor: Document text field.

    Returns:
        ``(start, end)`` with ``start <= end``. If there is no selection,
        both values are the caret index (collapsed range).
    """
    value = editor.value or ""
    sel = editor.selection
    if sel is None:
        caret = len(value)
        return caret, caret
    start = min(sel.base_offset, sel.extent_offset)
    end = max(sel.base_offset, sel.extent_offset)
    return start, end


def _selected_text(editor: ft.TextField) -> str:
    """Return the substring covered by the current selection.

    Args:
        editor: Document text field.

    Returns:
        Selected text, or an empty string when the range is collapsed.
    """
    start, end = _selected_range(editor)
    return (editor.value or "")[start:end]


def _replace_range(
    editor: ft.TextField, start: int, end: int, replacement: str
) -> None:
    """Replace ``value[start:end]`` with ``replacement`` and move the caret.

    Args:
        editor: Document text field to mutate.
        start: Inclusive start index.
        end: Exclusive end index.
        replacement: Text to insert in place of the selected range.
    """
    value = editor.value or ""
    editor.value = value[:start] + replacement + value[end:]
    caret = start + len(replacement)
    editor.selection = ft.TextSelection(base_offset=caret, extent_offset=caret)
    editor.focus()


def _menu_item(
    label: str,
    shortcut: str | None,
    on_click: Callable[[ft.ControlEvent], Any],
) -> ft.MenuItemButton:
    """Build one dropdown row with label and optional shortcut hint.

    Args:
        label: Primary menu text (e.g. ``"Save"``).
        shortcut: Optional hint shown on the right (display only unless wired
            globally); use ``None`` to hide.
        on_click: Flet click handler; omit behavior only for disabled items.

    Returns:
        A ``MenuItemButton`` ready to place under a ``SubmenuButton``.
    """
    return ft.MenuItemButton(
        content=ft.Row(
            controls=[
                ft.Text(label, expand=True),
                ft.Text(
                    shortcut or "",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            width=_MENU_WIDTH,
        ),
        on_click=on_click,
    )


def _submenu(title: str, items: list[ft.Control]) -> ft.SubmenuButton:
    """Build a top-level menu title with nested items.

    Args:
        title: Text on the menu bar (e.g. ``"File"``).
        items: Dropdown controls, usually from :func:`_menu_item`.

    Returns:
        A ``SubmenuButton`` for use in ``MenuBar.controls``.
    """
    return ft.SubmenuButton(
        content=ft.Text(title),
        controls=items,
    )


def build_menubar(page: ft.Page, editor: ft.TextField) -> ft.Control:
    """Assemble the full-width menu bar and bind it to ``editor``.

    Registers a page-scoped ``Clipboard`` service for cut/copy/paste. Shortcut
    labels in the UI are display-only unless global key handling is added
    elsewhere.

    Args:
        page: Active Flet page (dialogs, window, URL launch).
        editor: Shared writing ``TextField`` from :func:`ui.canvas.create_editor`.

    Returns:
        A bordered ``Container`` spanning the window width, with the ``MenuBar``
        aligned to the start.
    """
    clipboard = ft.Clipboard()
    _zoom = {"size": editor.text_size or DEFAULT_EDITOR_TEXT_SIZE}

    def stub(feature: str) -> Callable[[ft.ControlEvent], None]:
        """Create a handler that announces an unimplemented feature.

        Args:
            feature: Name shown in the snackbar (e.g. ``"Save"``).

        Returns:
            Click handler suitable for :func:`_menu_item`.
        """

        def handler(_e: ft.ControlEvent) -> None:
            _toast(page, f"{feature} — coming soon")

        return handler

    def new_document(_e: ft.ControlEvent) -> None:
        """Clear the document, prompting if the editor already has text."""
        if not (editor.value or "").strip():
            editor.value = ""
            editor.focus()
            return

        def discard(_e: ft.ControlEvent) -> None:
            """Confirm discarding the current document text."""
            editor.value = ""
            page.pop_dialog()
            editor.focus()

        def cancel(_e: ft.ControlEvent) -> None:
            """Dismiss the new-document confirmation without clearing."""
            page.pop_dialog()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("New document"),
                content=ft.Text("Discard the current text?"),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel),
                    ft.TextButton("Discard", on_click=discard),
                ],
            )
        )

    def select_all(_e: ft.ControlEvent) -> None:
        """Select the entire document in ``editor``."""
        text = editor.value or ""
        editor.focus()
        editor.selection = ft.TextSelection(
            base_offset=0,
            extent_offset=len(text),
        )

    async def copy_selection(_e: ft.ControlEvent) -> None:
        """Copy the current selection to the system clipboard."""
        text = _selected_text(editor)
        if not text:
            _toast(page, "Nothing selected to copy")
            return
        await clipboard.set(text)

    async def cut_selection(_e: ft.ControlEvent) -> None:
        """Cut the current selection to the clipboard and remove it from the document."""
        text = _selected_text(editor)
        if not text:
            _toast(page, "Nothing selected to cut")
            return
        start, end = _selected_range(editor)
        await clipboard.set(text)
        _replace_range(editor, start, end, "")

    async def paste_from_clipboard(_e: ft.ControlEvent) -> None:
        """Insert clipboard text at the selection or caret."""
        text = await clipboard.get()
        if not text:
            _toast(page, "Clipboard is empty")
            return
        start, end = _selected_range(editor)
        editor.focus()
        _replace_range(editor, start, end, text)

    def zoom(delta: int) -> Callable[[ft.ControlEvent], None]:
        """Return a handler that adjusts editor font size by ``delta`` pixels.

        Args:
            delta: Added to the current zoom level (use :data:`_ZOOM_STEP`).

        Returns:
            View-menu click handler clamped to ``_MIN_TEXT_SIZE``–``_MAX_TEXT_SIZE``.
        """

        def handler(_e: ft.ControlEvent) -> None:
            size = _zoom["size"] + delta
            _zoom["size"] = max(_MIN_TEXT_SIZE, min(_MAX_TEXT_SIZE, size))
            editor.text_size = _zoom["size"]

        return handler

    def reset_zoom(_e: ft.ControlEvent) -> None:
        """Reset editor font size to :data:`ui.canvas.DEFAULT_EDITOR_TEXT_SIZE`."""
        _zoom["size"] = DEFAULT_EDITOR_TEXT_SIZE
        editor.text_size = DEFAULT_EDITOR_TEXT_SIZE

    def toggle_full_screen(_e: ft.ControlEvent) -> None:
        """Toggle the native window full-screen flag."""
        page.window.full_screen = not page.window.full_screen

    async def exit_app(_e: ft.ControlEvent) -> None:
        """Request a graceful close of the application window."""
        await page.window.close()

    def word_count(_e: ft.ControlEvent) -> None:
        """Open a dialog with basic word and character counts."""
        text = editor.value or ""
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Word count"),
                content=ft.Text(f"{words:,} words · {chars:,} characters"),
                actions=[ft.TextButton("OK", on_click=lambda e: page.pop_dialog())],
            )
        )

    def about(_e: ft.ControlEvent) -> None:
        """Show application name and short description."""
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("About Writer"),
                content=ft.Text(
                    "Writer Assist\nA calm place to draft and edit plain text."
                ),
                actions=[ft.TextButton("OK", on_click=lambda e: page.pop_dialog())],
            )
        )

    async def open_docs(_e: ft.ControlEvent) -> None:
        """Open the Flet documentation site in the default browser."""
        await ft.UrlLauncher().launch_url("https://flet.dev/docs/")

    menubar = ft.MenuBar(
        controls=[
            _submenu(
                "File",
                [
                    _menu_item("New", "Ctrl+N", new_document),
                    _menu_item("Open…", "Ctrl+O", stub("Open")),
                    _menu_item("Save", "Ctrl+S", stub("Save")),
                    _menu_item("Save As…", "Ctrl+Shift+S", stub("Save As")),
                    _menu_item("Print…", "Ctrl+P", stub("Print")),
                    _menu_item("Exit", "Alt+F4", exit_app),
                ],
            ),
            _submenu(
                "Edit",
                [
                    _menu_item("Undo", "Ctrl+Z", stub("Undo")),
                    _menu_item("Redo", "Ctrl+Y", stub("Redo")),
                    _menu_item("Cut", "Ctrl+X", cut_selection),
                    _menu_item("Copy", "Ctrl+C", copy_selection),
                    _menu_item("Paste", "Ctrl+V", paste_from_clipboard),
                    _menu_item("Find…", "Ctrl+F", stub("Find")),
                    _menu_item("Replace…", "Ctrl+H", stub("Replace")),
                    _menu_item("Select All", "Ctrl+A", select_all),
                ],
            ),
            _submenu(
                "View",
                [
                    _menu_item("Zoom In", "Ctrl++", zoom(_ZOOM_STEP)),
                    _menu_item("Zoom Out", "Ctrl+-", zoom(-_ZOOM_STEP)),
                    _menu_item("Actual Size", "Ctrl+0", reset_zoom),
                    _menu_item("Full Screen", "F11", toggle_full_screen),
                ],
            ),
            _submenu(
                "Format",
                [
                    _menu_item("Font…", None, stub("Font")),
                    _menu_item("Paragraph…", None, stub("Paragraph")),
                ],
            ),
            _submenu(
                "Tools",
                [
                    _menu_item("Spelling…", None, stub("Spelling")),
                    _menu_item("Word Count…", None, word_count),
                ],
            ),
            _submenu(
                "Help",
                [
                    _menu_item("Documentation", None, open_docs),
                    _menu_item("About Writer", None, about),
                ],
            ),
        ],
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                menubar,
                ft.Container(expand=True),
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=ft.Padding.symmetric(horizontal=4, vertical=1),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
    )
