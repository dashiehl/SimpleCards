import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from app.config import ROOT_DIR
from app.db.connection import init_db
from app.ui.main_window import MainWindow


def main() -> None:
    init_db()

    app = QApplication(sys.argv)
    qss_path = ROOT_DIR / "app" / "theming" / "dark_theme.qss"
    app.setStyleSheet(qss_path.read_text())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
