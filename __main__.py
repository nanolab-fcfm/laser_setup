from pymeasure.display.Qt import QtWidgets
from pymeasure.experiment import Procedure
from PyQt6.QtCore import QLocale
from PyQt6.QtGui import QIcon

from lib.display import get_dark_palette, MainWindow, remove_empty_data
from lib import _config_file_used
from Scripts import Apps, Scripts

import os
import sys
from typing import Type

app = QtWidgets.QApplication(sys.argv)
app.setStyle('Fusion')
app.setPalette(get_dark_palette())
QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))


class AppWindow(QtWidgets.QMainWindow):
    def __init__(self, apps: dict[str, Type[Procedure]]):
        super().__init__()
        self.setWindowTitle('Laser Setup')
        # self.setWindowIcon(QIcon(r"C:\Users\benja\OneDrive\Imágenes\icons\favicon.ico"))
        self.resize(640, 480)
        self.setCentralWidget(QtWidgets.QWidget())

        self.apps = apps
        self.windows = {}

        # App Buttons
        self.layout = QtWidgets.QGridLayout(self.centralWidget())
        self.buttons = {}
        for i, (name, cls) in enumerate(apps.items()):
            self.buttons[name] = QtWidgets.QPushButton(name)
            self.buttons[name].clicked.connect(self.open_app(name))
            self.buttons[name].setToolTip(cls.__doc__)
            self.layout.addWidget(self.buttons[name], 2, i)

        # README Widget
        readme = QtWidgets.QTextEdit(readOnly=True)
        readme.setStyleSheet("""
            font-size: 12pt;
        """)
        with open('README.md') as f:
            readme.setMarkdown(f.read())
        self.layout.addWidget(readme, 1, 0, 1, len(apps))
        
        # Settings Button
        settings = QtWidgets.QPushButton('Settings')
        settings.clicked.connect(self.edit_settings)
        self.layout.addWidget(settings, 0, 0)
        
        # Reload window button
        self.reload = QtWidgets.QPushButton('Reload')
        self.reload.clicked.connect(lambda: os.execl(sys.executable, sys.executable, *sys.argv))
        self.layout.addWidget(self.reload, 0, len(apps)-1)
        
        for i, (name, func) in enumerate(Scripts.items()):
            button = QtWidgets.QPushButton(name)
            button.clicked.connect(self.run_script(name))
            self.layout.addWidget(button, 3, i)

    def open_app(self, name: str):
        def func():
            self.windows[name] = MainWindow(self.apps[name], title=name)
            self.windows[name].show()
            # self.close()
        return func
    
    def run_script(self, name: str):
        def func():
            Scripts[name]()
            self.suggest_reload()
        return func
    
    def edit_settings(self):
        os.startfile(_config_file_used.replace('/', '\\'))
        self.suggest_reload()
        
    def suggest_reload(self):
        self.reload.setStyleSheet('background-color: red;')
        self.reload.setText('Reload to apply changes')
        
        

if __name__ == '__main__':
    window = AppWindow(Apps)
    window.show()
    app.exec()
    remove_empty_data()
    sys.exit()
