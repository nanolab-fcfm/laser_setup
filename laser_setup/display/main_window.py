import os
import sys
import logging
from functools import partial
from importlib.metadata import metadata
from typing import Type

from pymeasure.experiment import Procedure

from .. import config, config_path, _config_file_used
from ..cli import Scripts, parameters_to_db
from ..utils import remove_empty_data, get_status_message
from ..procedures import Experiments, from_str
from ..instruments import InstrumentManager, Instruments
from .Qt import QtGui, QtWidgets, QtCore, Worker
from .widgets import SQLiteWidget
from .experiment_window import ExperimentWindow, SequenceWindow

log = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """The main window for program. It contains buttons to open
    the experiment windows, sequence windows, and run scripts.
    """
    def __init__(self, **kwargs):
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
        procedure_menu.setToolTipsVisible(True)
        for cls, name in Experiments:
            action = QtGui.QAction(name, self)
            doc = cls.__doc__.replace('    ', '').strip()
            action.triggered.connect(partial(self.open_app, cls))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            procedure_menu.addAction(action)

        sequence_menu = menu.addMenu('Se&quences')
        sequence_menu.setToolTipsVisible(True)
        for name, list_str in config.items('Sequences'):
            action = QtGui.QAction(name, self)
            doc = list_str
            action.triggered.connect(partial(
                self.open_sequence, name, from_str(list_str)
            ))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            sequence_menu.addAction(action)

        script_menu = menu.addMenu('&Scripts')
        script_menu.setToolTipsVisible(True)
        for f, name in Scripts:
            action = QtGui.QAction(name, self)
            doc = sys.modules[f.__module__].__doc__ or ''
            doc = doc.replace('    ', '').strip()
            action.triggered.connect(partial(self.run_script, f))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            script_menu.addAction(action)

        view_menu = menu.addMenu('&View')
        view_menu.addAction(
            'Parameter Database', partial(self.open_database, 'parameters.db')
        )

        help_menu = menu.addMenu('&Help')
        help_menu.setToolTipsVisible(True)

        instrument_help = help_menu.addMenu('Instruments')
        for cls, name in Instruments:
            action = QtGui.QAction(name, self)
            action.triggered.connect(partial(
                self.text_window, name, InstrumentManager.help(cls, return_str=True)
            ))
            instrument_help.addAction(action)

        self.status_bar = self.statusBar()

        thread = QtCore.QThread(parent=self)
        worker = Worker(get_status_message, thread)
        worker.finished.connect(lambda msg: self.status_bar.showMessage(msg, 3000))
        thread.start()

        self.windows: dict[str|Type[Procedure], QtWidgets.QMainWindow] = {}

        # Experiment Buttons
        self._layout = QtWidgets.QGridLayout(self.centralWidget())

        # README Widget
        readme = QtWidgets.QTextBrowser(parent=self)
        readme.setOpenExternalLinks(True)
        readme.setStyleSheet("""
            font-size: 12pt;
        """)
        try:
            with open('README.md') as f:
                readme_text = f.read()
        except FileNotFoundError:
            readme_text = metadata('laser_setup').get('Description')
        readme.setMarkdown(readme_text)
        self._layout.addWidget(readme)

        # Reload window button
        self.reload = QtWidgets.QPushButton('Reload')
        self.reload.clicked.connect(
            lambda: os.execl(sys.executable, sys.executable, '-m', 'laser_setup', *sys.argv[1:])
        )   # TODO: fix bug where the terminal misbehaves after reload
        self.status_bar.addPermanentWidget(self.reload)

    def open_sequence(self, name: str, procedure_list: list[Type[Procedure]]):
        self.windows[name] = SequenceWindow(procedure_list, title=name, parent=self)
        self.windows[name].show()
        self.suggest_reload()

    def open_app(self, cls: Type[Procedure]):
        # Get the index of the title from the transpose. This turned out ugly.
        title = Experiments[list(zip(*Experiments))[0].index(cls)][1]
        self.windows[cls] = ExperimentWindow(cls, title=title, parent=self)
        self.windows[cls].show()

    def run_script(self, f: callable):
        try:
            f(parent=self)
        except TypeError:
            f()
        self.suggest_reload()

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

    def text_window(self, title: str, text: str):
        """Displays a text window with the given title and text. adds a scroll bar"""
        text_window = QtWidgets.QDialog()
        text_window.setWindowTitle(title)
        text_window.resize(640, 480)

        text_layout = QtWidgets.QVBoxLayout(text_window)
        text_edit = QtWidgets.QTextEdit(text_window)
        text_edit.setPlainText(text)
        text_layout.addWidget(text_edit)
        text_window.setLayout(text_layout)
        text_window.exec()

    def open_database(self, db_name: str):
        path = config['Filename']['directory'] + '/' + db_name
        if not os.path.exists(path):
            ans = self.question_box(
                'Database not found', f'Database {path} not found. Create new database?'
            )
            if not ans:
                return
            parameters_to_db.create_db(parent=self)

        sqlite_widget = SQLiteWidget(path, parent=self)
        window = QtWidgets.QMainWindow(parent=self)
        window.setCentralWidget(sqlite_widget)
        window.resize(640, 480)
        window.setWindowTitle(db_name)
        window.show()

    def closeEvent(self, event):
        """Ensures all running threads are properly stopped."""
        for child in self.findChildren(QtCore.QThread):
            if child.isRunning():
                child.quit()
                child.wait()
        super().closeEvent(event)


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
