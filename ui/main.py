from __future__ import annotations

import sys

from PySide6 import QtWidgets

from ui.controller import MainController


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    controller = MainController()
    controller.show()
    return app.exec()
