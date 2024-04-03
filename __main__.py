from pymeasure.display.Qt import QtWidgets
from pymeasure.experiment import Procedure
from PyQt6.QtCore import QLocale
from PyQt6.QtWidgets import QStyle

import os
import sys
from typing import Type

from lib.display import get_dark_palette, ExperimentWindow, remove_empty_data
from lib import _config_file_used
from Scripts.It import It
from Scripts.IV import IV
from Scripts.IVg import IVg
from Scripts.Pt import Pt
from Scripts.calibrate_laser import LaserCalibration
from Scripts.setup_adapters import main as setup_adapters_main
from Scripts.console import main as console_main
from Scripts.find_dp_script import main as find_dp_script_main

Experiments = {
    'I vs V': IV,
    'I vs Vg': IVg,
    'I vs t': It,
    'P vs t': Pt,
    'Calibrate Laser': LaserCalibration,
}

Scripts = {
    'Set up Adapters': setup_adapters_main,
    'Console': console_main,
    'Find Dirac Point': find_dp_script_main,
}


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, apps: dict[str, Type[Procedure]], scripts: dict[str, callable]):
        super().__init__()
        self.setWindowTitle('Laser Setup')
        # Set the window icon to sp_computericon
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.resize(640, 480)
        self.setCentralWidget(QtWidgets.QWidget())

        self.apps = apps
        self.scripts = scripts
        self.gridx = max(len(apps), len(scripts), 3)
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
        self.layout.addWidget(readme, 1, 0, 1, self.gridx)
        
        # Settings Button
        settings = QtWidgets.QPushButton('Settings')
        settings.clicked.connect(self.edit_settings)
        self.layout.addWidget(settings, 0, 0)
        
        # Reload window button
        self.reload = QtWidgets.QPushButton('Reload')
        self.reload.clicked.connect(lambda: os.execl(sys.executable, sys.executable, *sys.argv))
        self.layout.addWidget(self.reload, 0, self.gridx-1)
        
        for i, (name, func) in enumerate(scripts.items()):
            button = QtWidgets.QPushButton(name)
            button.clicked.connect(self.run_script(name))
            self.layout.addWidget(button, 3, i)

    def open_app(self, name: str):
        def func():
            self.windows[name] = ExperimentWindow(self.apps[name], title=name)
            self.windows[name].show()
        return func
    
    def run_script(self, name: str):
        def func():
            self.scripts[name]()
            self.suggest_reload()
        return func
    
    def edit_settings(self):
        os.startfile(_config_file_used.replace('/', '\\'))
        self.suggest_reload()
        
    def suggest_reload(self):
        self.reload.setStyleSheet('background-color: red;')
        self.reload.setText('Reload to apply changes')
        
    def error_dialog(self, message:str):
        from PyQt6.QtWidgets import QMessageBox
        error_dialog = QMessageBox()
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(f"An error occurred:\n{message}\nPlease reload the program.")
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.exec()
        self.reload.click() 


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setPalette(get_dark_palette())
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))

    window = MainWindow(Experiments, Scripts)
    window.show()
    app.exec()
    remove_empty_data()
    sys.exit()
