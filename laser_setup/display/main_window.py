import os
import sys
import logging
from importlib.metadata import metadata
from typing import Type

from pymeasure.experiment import Procedure

from .. import config, config_path, _config_file_used
from ..utils import remove_empty_data
from ..procedures import MetaProcedure
from .Qt import QtGui, QtWidgets, QtCore
from .experiment_window import ExperimentWindow, MetaProcedureWindow

log = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """The main window for program. It contains buttons to open
    the experiment windows, sequence windows, and run scripts.
    """
    def __init__(
            self,
            sequences: dict[str, Type[MetaProcedure]],
            experiments: dict[str, Type[Procedure]],
            scripts: dict[str, callable],
            **kwargs
        ):
        super().__init__(**kwargs)
        self.setWindowTitle('Laser Setup')
        self.setWindowIcon(
            self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        )
        self.resize(640, 480)
        self.setCentralWidget(QtWidgets.QWidget())

        menu = self.menuBar()
        settings_menu = menu.addMenu('&Settings')
        settings_menu.addAction('Edit settings', self.edit_settings)

        procedure_menu = menu.addMenu('&Procedures')
        for cls, name in experiments.items():
            action = QtGui.QAction(name, self)
            action.triggered.connect(self.open_app(cls))
            action.setToolTip(cls.__doc__)
            action.setStatusTip(cls.__doc__.replace('    ', ''))
            procedure_menu.addAction(action)

        sequence_menu = menu.addMenu('Se&quences')
        for cls, name in sequences.items():
            action = QtGui.QAction(name, self)
            action.triggered.connect(self.open_sequence(cls))
            action.setToolTip(cls.__doc__)
            action.setStatusTip(cls.__doc__.replace('    ', ''))
            sequence_menu.addAction(action)

        script_menu = menu.addMenu('&Scripts')
        for f, name in scripts.items():
            action = QtGui.QAction(name, self)
            doc = sys.modules[f.__module__].__doc__ or ''
            action.triggered.connect(self.run_script(f))
            action.setToolTip(doc)
            action.setStatusTip(doc.replace('    ', ''))
            script_menu.addAction(action)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready', 3000)

        self.sequences = sequences
        self.experiments = experiments
        self.scripts = scripts
        self.gridx = max(len(experiments), len(scripts), 3)
        self.windows = {}

        # Experiment Buttons
        self._layout = QtWidgets.QGridLayout(self.centralWidget())

        # README Widget
        readme = QtWidgets.QTextEdit(readOnly=True)
        readme.setStyleSheet("""
            font-size: 12pt;
        """)
        try:
            with open('README.md') as f:
                readme_text = f.read()
        except FileNotFoundError:
            readme_text = metadata('laser_setup').get('Description')
        readme.setMarkdown(readme_text)
        self._layout.addWidget(readme, 1, 0, 1, self.gridx)

        # Reload window button
        self.reload = QtWidgets.QPushButton('Reload')
        self.reload.clicked.connect(
            lambda: os.execl(sys.executable, sys.executable, '.', *sys.argv[1:])
        )
        self._layout.addWidget(self.reload, 0, self.gridx-1)

    def open_sequence(self, cls: Type[MetaProcedure]):
        def func():
            self.windows[cls] = MetaProcedureWindow(cls, title=self.sequences[cls], parent=self)
            self.windows[cls].show()
            self.suggest_reload()
        return func

    def open_app(self, cls: Type[Procedure]):
        def func():
            self.windows[cls] = ExperimentWindow(cls, title=self.experiments[cls], parent=self)
            self.windows[cls].show()
        return func

    def run_script(self, f: callable):
        def func():
            try:
                f(parent=self)
            except TypeError:
                f()
            self.suggest_reload()
        return func

    def edit_settings(self):
        if _config_file_used != config_path:
            choice = self.select_from_list('No config file found',
                ['Create new config', 'Use default config'], 'Select an option:')

            if choice == 'Create new config':
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    config.write(f)

            elif choice == 'Use default config':
                return

        os.startfile(config_path.replace('/', '\\'))
        self.suggest_reload()

    def suggest_reload(self):
        self.reload.setStyleSheet('background-color: red;')
        self.reload.setText('Reload to apply changes')

    def error_dialog(self, message:str):
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(f"An error occurred:\n{message}\nPlease reload the program.")
        error_dialog.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        error_dialog.exec()
        self.reload.click()

    def lock_window(self, msg: str = ''):
        self.setEnabled(False)
        self.lock_msg = msg
        self.locked = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Icon.Information, 'Locked', msg)
        self.locked.exec()

    def select_from_list(self, title: str, items: list[str], label: str = '') -> str:
        item, ok = QtWidgets.QInputDialog.getItem(self, title, label, items, 0, False)
        if ok:
            return item
        return None

    def question_box(self, title: str, text: str) -> bool:
        buttons = QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        reply = QtWidgets.QMessageBox.question(self, title, text, buttons)
        return reply == QtWidgets.QMessageBox.StandardButton.Yes


def display_window(Window: Type[QtWidgets.QMainWindow], *args, **kwargs):
    """Displays the window for the given class. Allows for the
    window to be run from the GUI, by queuing it in the manager.
    It also allows for existing data to be loaded and displayed.

    :param Window: The Qt Window subclass to display.
    :param args: The arguments to pass to the window class.
    """
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(config['GUI']['style'])    # Get available styles with QtWidgets.QStyleFactory.keys()
    if bool(eval(config['GUI']['dark_mode'])):
        app.setPalette(get_dark_palette())
    QtCore.QLocale.setDefault(QtCore.QLocale(
        QtCore.QLocale.Language.English,
        QtCore.QLocale.Country.UnitedStates
    ))
    window = Window(*args, **kwargs)
    window.show()
    app.exec()
    remove_empty_data()
    sys.exit()


def display_experiment(cls: Type[Procedure], title: str = ''):
    """Wrapper around display_window for ExperimentWindow.
    TODO: Remove this function and use display_window directly.
    """
    display_window(ExperimentWindow, cls, title)


def get_dark_palette():
    palette = QtGui.QPalette()
    ColorRole = QtGui.QPalette.ColorRole

    # Set the background color
    palette.setColor(ColorRole.Window, QtGui.QColor(50, 50, 50))

    # Set the title text color
    palette.setColor(ColorRole.WindowText, QtGui.QColor(200, 200, 200))

    # Set the input text color
    palette.setColor(ColorRole.Text, QtGui.QColor(200, 200, 200))

    # Set the button color
    palette.setColor(ColorRole.Button, QtGui.QColor(30, 30, 30))

    # Set the button text color
    palette.setColor(ColorRole.ButtonText, QtGui.QColor(200, 200, 200))

    # Set the base color
    palette.setColor(ColorRole.Base, QtGui.QColor(35, 35, 35))

    # Set the alternate background color
    palette.setColor(ColorRole.AlternateBase, QtGui.QColor(45, 45, 45))

    # Set the highlight color
    palette.setColor(ColorRole.Highlight, QtGui.QColor(42, 130, 218))

    # Set the highlighted text color
    palette.setColor(ColorRole.HighlightedText, QtGui.QColor(240, 240, 240))

    return palette


def standard_icon(icon: str):
    """Returns the standard icon for the given name."""
    return QtWidgets.QApplication.style().standardIcon(getattr(QtWidgets.QStyle.StandardPixmap, icon))