"""
main.py
=======
Entry point for the Fasciculation Video Annotator.

Usage:
    python main.py
"""

import sys
from PySide6.QtWidgets import QApplication
from annotator.main_window import FasciculationAnnotator


def main():
    app    = QApplication(sys.argv)
    window = FasciculationAnnotator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
