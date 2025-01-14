import logging
import os
import sys
from functools import partial
from importlib.metadata import metadata
from pathlib import Path
from typing import Type

from pymeasure.experiment import Procedure

from .. import config, default_config_path
from ..cli import Scripts, parameters_to_db
from ..instruments import InstrumentManager, Instruments
from ..procedures import Experiments, from_str
from ..utils import get_status_message, remove_empty_data
from .experiment_window import ExperimentWindow, SequenceWindow
from .Qt import ConsoleWidget, QtCore, QtGui, QtWidgets, Worker
from .widgets import LogsWidget, SQLiteWidget

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

        procedure_menu = menu.addMenu('&Procedures')
        procedure_menu.setToolTipsVisible(True)
        for cls, name in Experiments:
            action = QtGui.QAction(name, self)
            doc = cls.__doc__.replace('    ', '').strip()
            action.triggered.connect(partial(self.open_app, cls))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f'Ctrl+{len(procedure_menu.actions()) + 1}')
            procedure_menu.addAction(action)

        sequence_menu = menu.addMenu('Se&quences')
        sequence_menu.setToolTipsVisible(True)
        for name, list_str in config['Sequences'].items():
            action = QtGui.QAction(name, self)
            doc = str(list_str).replace("'", "").replace('"', '')
            action.triggered.connect(partial(
                self.open_sequence, name, list(map(from_str, list_str))
            ))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f'Ctrl+Shift+{len(sequence_menu.actions()) + 1}')
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
            action.setShortcut(f'Alt+{len(script_menu.actions()) + 1}')
            script_menu.addAction(action)

        view_menu = menu.addMenu('&View')
        view_menu.addAction(
            'Parameter Database', partial(self.open_database, 'parameters.db')
        )

        self.log_widget = LogsWidget('Logs', parent=self)
        self.log_widget.setWindowFlags(QtCore.Qt.WindowType.Dialog)

        self.log = logging.getLogger('laser_setup')
        self.log.setLevel(config['Logging']['console_level'])
        self.log.addHandler(self.log_widget.handler)

        log_action = view_menu.addAction('Logs', self.log_widget.show)
        log_action.setShortcut('Ctrl+Shift+L')

        console_action = view_menu.addAction('Console', self.open_console)
        console_action.setShortcut('Ctrl+Shift+C')

        settings_menu = menu.addMenu('&Settings')
        settings_menu.addAction('Edit settings', self.edit_settings)

        # Help
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
        self.reload.setShortcut('Ctrl+R')
        self.status_bar.addPermanentWidget(self.reload)

    def open_sequence(self, name: str, procedure_list: list[Type[Procedure]]):
        window = SequenceWindow(procedure_list, title=name, parent=self)
        window.show()

    def open_app(self, cls: Type[Procedure]):
        # Get the index of the title from the transpose. This turned out ugly.
        title = Experiments[list(zip(*Experiments))[0].index(cls)][1]
        self.windows[cls] = ExperimentWindow(cls, title=title)
        self.windows[cls].show()

    def run_script(self, f: callable):
        """Runs the given script function in the main thread."""
        try:
            f(parent=self)
        except TypeError:
            f()
        self.suggest_reload()

    def open_widget(self, widget: QtWidgets.QWidget, title: str):
        """Opens a widget in a new window."""
        widget.setWindowFlags(QtCore.Qt.WindowType.Dialog)
        widget.setWindowTitle(title)
        widget.resize(640, 480)
        widget.show()

    def edit_settings(self):
        save_path = Path(config['_session']['save_path'])
        if config['_session']['config_path_used'] == default_config_path:
            create_config = self.question_box(
                'Create new config?',
                'No custom configuration found. Create new config file?'
            )
            if not create_config:
                log.warning('Cannot edit settings without a custom config file.')
                return

            save_path.parent.mkdir(parents=True, exist_ok=True)

            _save_path = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Save config file', str(save_path), 'YAML files (*.yml)'
            )[0]
            save_path = Path(_save_path)
            text = default_config_path.read_text()
            save_path.write_text(text)
            log.info(f'Created new config file at {save_path}')

        os.startfile(save_path)
        self.suggest_reload()

    def suggest_reload(self):
        self.reload.setStyleSheet('background-color: red;')
        self.reload.setText('Reload to apply changes')

    def error_dialog(self, message:str):
        error_dialog = QtWidgets.QMessageBox(parent=self)
        error_dialog.setText(f"An error occurred:\n{message}\nPlease reload the program.")
        error_dialog.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        self.open_widget(error_dialog, 'Error')
        error_dialog.exec()
        self.reload.click()

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
        text_edit = QtWidgets.QTextEdit(parent=self)
        text_edit.setPlainText(text)
        self.open_widget(text_edit, title)

    def open_console(self):
        """Opens an interactive console. Loads common modules and instruments."""
        from ..instruments import FakeAdapter
        instruments = InstrumentManager()

        header = "Interactive console. To instantiate an instrument, use the 'instruments.connect' method.\n"
        if '-d' in sys.argv or '--debug' in sys.argv:
            header += "\nDebug mode (the InstrumentManager will use a FakeAdapter if it can't connect to an instrument).\n"

        self.console_widget = ConsoleWidget(
            namespace=globals() | locals(), text=header, parent=self
        )
        self.open_widget(self.console_widget, 'Console')


    def open_database(self, db_name: str):
        db_path = Path(config['Filename']['directory']) / db_name
        if not db_path.exists():
            ans = self.question_box(
                'Database not found', f'Database {db_path} not found. Create new database?'
            )
            if not ans:
                return
            parameters_to_db.create_db(parent=self)

        db_widget = SQLiteWidget(db_path.as_posix(), parent=self)
        db_widget.closeEvent = lambda _: db_widget.con.close()
        self.open_widget(db_widget, db_name)

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
    pixmap = QtGui.QPixmap(config['GUI']['splash_image'])
    pixmap = pixmap.scaledToHeight(480)
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()

    # Get available styles with QtWidgets.QStyleFactory.keys()
    app.setStyle(config['GUI']['style'])
    if bool(config['GUI']['dark_mode']):
        app.setPalette(get_dark_palette())
    QtCore.QLocale.setDefault(QtCore.QLocale(
        QtCore.QLocale.Language.English,
        QtCore.QLocale.Country.UnitedStates
    ))

    window = Window(*args, **kwargs)
    splash.finish(window)
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

    # Set the link color
    palette.setColor(ColorRole.Link, QtGui.QColor(42, 130, 218))

    # Set the highlight color
    palette.setColor(ColorRole.Highlight, QtGui.QColor(42, 130, 218))

    # Set the highlighted text color
    palette.setColor(ColorRole.HighlightedText, QtGui.QColor(240, 240, 240))

    return palette
