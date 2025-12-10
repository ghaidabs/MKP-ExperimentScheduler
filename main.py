import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from ui import MainWindow, apply_light_palette


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('Segoe UI', 11))
    apply_light_palette(app)
    app.setWindowIcon(QIcon("icon.png"))
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
