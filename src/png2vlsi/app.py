from __future__ import annotations

import sys
import time

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from .gui.main_window import MainWindow
from .gui.splash import StartupSplash


MIN_SPLASH_SECONDS = 10.0


def main() -> int:
    start_time = time.monotonic()
    app = QApplication(sys.argv)
    app.setOrganizationName("PNG2VLSI")
    app.setApplicationName("PNG2VLSI Pixel")

    splash = StartupSplash()
    splash.show()
    splash.update_step("Initializing conversion workspace...")
    QCoreApplication.processEvents()

    splash.update_step("Loading image processing and export modules...")
    QCoreApplication.processEvents()

    splash.update_step("Preparing pixel-to-layout interface...")
    QCoreApplication.processEvents()

    window = MainWindow()
    splash.update_step("Opening main interface...")
    QCoreApplication.processEvents()

    elapsed = time.monotonic() - start_time
    if elapsed < MIN_SPLASH_SECONDS:
        time.sleep(MIN_SPLASH_SECONDS - elapsed)

    window.show()
    splash.finish(window)
    return app.exec()
