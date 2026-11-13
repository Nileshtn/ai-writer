"""Writer Assist application entry point.

Runs a Flet desktop (or web) app with a documented menu bar and a full-page
writing canvas. Layout is a single column: menubar on top, editor below.
"""

import flet as ft

from ui.canvas import build_writing_canvas, create_editor
from ui.menubar import build_menubar


def main(page: ft.Page) -> None:
    """Configure the page and mount the menubar plus writing surface.

    Args:
        page: Flet page created for each user session by ``ft.run``.
    """
    page.title = "Writer"
    page.padding = 0

    editor = create_editor()
    page.add(
        ft.Column(
            controls=[
                # build_menubar(page, editor),
                build_writing_canvas(editor),
            ],
            spacing=0,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )


if __name__ == "__main__":
    ft.run(main)
