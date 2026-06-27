"""Application entry point for File Copy Utility."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from utils.logger import setup_logging


def main() -> int:
    """Start the desktop application."""

    logger = setup_logging()
    logger.info("Application start")
    app = QApplication(sys.argv)
    window = MainWindow(logger)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
