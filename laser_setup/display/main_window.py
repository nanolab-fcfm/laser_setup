import logging
import os
import sys
from functools import partial
from importlib.metadata import metadata
from pathlib import Path
from typing import Callable

from pymeasure.experiment import Procedure

from ..cli import parameters_to_db
from ..config import ConfigHandler, DefaultPaths, config, instantiate
from ..config.defaults import ProceduresType, ScriptsType, SequencesType
from ..instruments import InstrumentManager, Instruments
from ..Qt import ConsoleWidget, QtCore, QtGui, QtWidgets, Worker
from ..utils import get_status_message, remove_empty_data
from .experiment_window import ExperimentWindow, SequenceWindow
from .widgets import LogsWidget, SQLiteWidget
from .camera_widget import CameraWidget

log = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """The main window for program. It contains buttons to open
    the experiment windows, sequence windows, and run scripts.
    """

    def __init__(
        self,
        title: str = 'Main Window',
        size: list[int, int] = [640, 480],
        widget_size: list[int, int] = [640, 480],
        icon: str = '',
        readme_file: str | Path = 'README.md',
        procedures: ProceduresType = None,
        sequences: SequencesType = None,
        scripts: ScriptsType = None,
        **kwargs
    ):
        self.widget_size = widget_size
        self.readme_path = Path(readme_file)
        self.procedures = procedures
        self.sequences = sequences
        self.scripts = scripts
        self.config_handler = ConfigHandler(parent=self, config=config)

        super().__init__(**kwargs)
        self.setWindowTitle(title)
        self.setWindowIcon(icon or self.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_TitleBarMenuButton
        ))
        self.resize(*size)
        self.setCentralWidget(QtWidgets.QWidget(parent=self))

        self.windows: dict[type[Procedure] | str, QtWidgets.QMainWindow] = {}
        self._layout = QtWidgets.QGridLayout(self.centralWidget())
        menu = self.menuBar()

        procedure_menu = menu.addMenu('&Procedures')
        procedure_menu.setToolTipsVisible(True)
        for item in self.procedures:
            cls = item.target
            action = QtGui.QAction(item.name or getattr(cls, 'name', cls.__name__), self)
            doc = cls.__doc__.replace('    ', '').strip()
            action.triggered.connect(partial(self.open_app, cls))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f'Ctrl+{len(procedure_menu.actions()) + 1}')
            procedure_menu.addAction(action)

        sequence_menu = menu.addMenu('Se&quences')
        sequence_menu.setToolTipsVisible(True)
        for name, seq_list in self.sequences.items():
            action = QtGui.QAction(name, self)
            doc = str(seq_list).replace("'", "").replace('"', '')
            action.triggered.connect(partial(
                self.open_sequence, name, seq_list
            ))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f'Ctrl+Shift+{len(sequence_menu.actions()) + 1}')
            sequence_menu.addAction(action)

        script_menu = menu.addMenu('&Scripts')
        script_menu.setToolTipsVisible(True)
        for item in self.scripts:
            func = item.target
            action = QtGui.QAction(item.name or func.__doc__, self)
            doc = sys.modules[func.__module__].__doc__ or ''
            doc = doc.replace('    ', '').strip()
            action.triggered.connect(partial(self.run_script, func))
            action.setToolTip(doc)
            action.setStatusTip(doc)
            action.setShortcut(f'Alt+{len(script_menu.actions()) + 1}')
            script_menu.addAction(action)

        view_menu = menu.addMenu('&View')
        db_action = view_menu.addAction(
            'Parameter Database', partial(self.open_database, config.Dir.database)
        )
        db_action.setShortcut('Ctrl+Shift+D')

        video_action = view_menu.addAction('Cameras', self.open_camera)
        video_action.setShortcut('Ctrl+Shift+C')

        self.log_widget = LogsWidget('Logs', parent=self)
        self.log_widget.setWindowFlags(QtCore.Qt.WindowType.Dialog)

        self.log = logging.getLogger('laser_setup')
        self.log.setLevel(config.Logging.console_level)
        self.log.addHandler(self.log_widget.handler)

        log_action = view_menu.addAction('Logs', self.log_widget.show)
        log_action.setShortcut('Ctrl+Shift+L')

        console_action = view_menu.addAction('Terminal', self.open_terminal)
        console_action.setShortcut('Ctrl+Shift+T')

        settings_menu = menu.addMenu('&Settings')
        settings_menu.addAction('Edit config', self.config_handler.edit_config)
        settings_menu.addAction('Load config', self.config_handler.import_config)

        # Help
        help_menu = menu.addMenu('&Help')
        help_menu.setToolTipsVisible(True)

        instrument_help = help_menu.addMenu('Instruments')
        for cls in Instruments:
            name = getattr(cls, 'name', cls.__name__)
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

        # README Widget
        readme = QtWidgets.QTextBrowser(parent=self)
        readme.setOpenExternalLinks(True)
        readme.setStyleSheet("""
            font-size: 12pt;
        """)
        if self.readme_path.is_file():
            readme_text = self.readme_path.read_text()
        else:
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

    def open_sequence(self, name: str, procedure_list: list[type[Procedure]]):
        window = SequenceWindow(procedure_list, title=name,
                                parent=self, **instantiate(config.Qt.SequenceWindow))
        window.show()

    def open_app(self, cls: type[Procedure]):
        self.windows[cls] = ExperimentWindow(
            cls, **instantiate(config.Qt.ExperimentWindow)
        )
        self.windows[cls].show()

    def run_script(self, f: Callable):
        """Runs the given script function in the main thread."""
        try:
            f(parent=self)
        except TypeError:
            f()
        self.suggest_reload()

    def open_widget(self, widget: QtWidgets.QWidget, title: str):
        """Opens a widget in a new window."""
        widget.setWindowFlags(QtCore.Qt.WindowType.Window)
        widget.setWindowTitle(title)
        widget.resize(*self.widget_size)
        widget.show()

    def suggest_reload(self):
        self.reload.setStyleSheet('background-color: red;')
        self.reload.setText('Reload to apply changes')
        self.reload.setShortcut('Ctrl+R')

    def error_dialog(self, message: str):
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
        MessageBox = QtWidgets.QMessageBox
        buttons = MessageBox.StandardButton.Yes | MessageBox.StandardButton.No
        reply = MessageBox.question(self, title, text, buttons)
        return reply == MessageBox.StandardButton.Yes

    def text_window(self, title: str, text: str):
        """Displays a text window with the given title and text. adds a scroll bar"""
        text_edit = QtWidgets.QTextEdit(parent=self)
        text_edit.setPlainText(text)
        self.open_widget(text_edit, title)

    def open_camera(self):
        """Opens the camera widget."""
        self.camera_widget = CameraWidget(parent=self)
        self.open_widget(self.camera_widget, 'Cameras')

    def open_terminal(self):
        """Opens an interactive console. Loads common modules and instruments."""
        from ..instruments import FakeAdapter  # noqa: F401
        instruments = InstrumentManager()

        header = (
            "Interactive console. To instantiate an instrument, use the "
            "'instruments.connect' method.\n"
        )
        if '-d' in sys.argv or '--debug' in sys.argv:
            header += (
                "\nDebug mode (the InstrumentManager will use a FakeAdapter if "
                "it can't connect to an instrument).\n"
            )
        self.console_widget = ConsoleWidget(
            namespace=globals() | locals(), text=header, parent=self
        )
        self.open_widget(self.console_widget, 'Console')

    def open_database(self, db_name: str):
        db_path = Path(config.Dir.data_dir) / db_name
        if not db_path.exists():
            ans = self.question_box(
                'Database not found', f'Database {db_path} not found. Create new database?'
            )
            if not ans:
                return
            parameters_to_db.create_db(parent=self)

        self.db_widget = SQLiteWidget(db_path.as_posix(), parent=self)
        self.open_widget(self.db_widget, db_name)

    def closeEvent(self, event):
        """Ensures all running threads are properly stopped."""
        for child in self.findChildren(QtCore.QThread):
            if child.isRunning():
                child.quit()
                child.wait()
        super().closeEvent(event)


def display_window(Window: type[QtWidgets.QMainWindow], *args, **kwargs):
    """Displays the window for the given class. Allows for the
    window to be run from the GUI, by queuing it in the manager.
    It also allows for existing data to be loaded and displayed.

    :param Window: The Qt Window subclass to display.
    :param args: The arguments to pass to the window class.
    """
    app = QtWidgets.QApplication(sys.argv)
    splash_image = Path(config.Qt.GUI.splash_image)
    if not splash_image.exists():
        splash_image = DefaultPaths.splash

    pixmap = QtGui.QPixmap(splash_image.as_posix())
    pixmap = pixmap.scaledToHeight(480)
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()

    # Get available styles with QtWidgets.QStyleFactory.keys()
    app.setStyle(config.Qt.GUI.style)
    if config.Qt.GUI.dark_mode:
        app.setPalette(get_dark_palette())
    QtCore.QLocale.setDefault(QtCore.QLocale(
        QtCore.QLocale.Language.English,
        QtCore.QLocale.Country.UnitedStates
    ))

    if issubclass(Window, MainWindow):
        kwargs.update(**instantiate(config.Qt.MainWindow))

    elif issubclass(Window, ExperimentWindow):
        kwargs.update(**instantiate(config.Qt.ExperimentWindow))

    window = Window(*args, **kwargs)
    splash.finish(window)
    window.show()
    app.exec()
    remove_empty_data()
    sys.exit()


def display_experiment(cls: type[Procedure], title: str = ''):
    """Wrapper around display_window for ExperimentWindow.
    TODO: Remove this function and use display_window directly.
    """
    display_window(ExperimentWindow, cls, title)


def get_dark_palette():
    palette = QtGui.QPalette()
    palette_dict = {
        'Window': (50, 50, 50),
        'WindowText': (200, 200, 200),
        'Text': (200, 200, 200),
        'Button': (30, 30, 30),
        'ButtonText': (200, 200, 200),
        'Base': (35, 35, 35),
        'AlternateBase': (45, 45, 45),
        'Link': (42, 130, 218),
        'Highlight': (42, 130, 218),
        'HighlightedText': (240, 240, 240),
    }

    for role, color in palette_dict.items():
        palette.setColor(
            getattr(QtGui.QPalette.ColorRole, role), QtGui.QColor(*color)
        )
    return palette


def main():
    display_window(MainWindow)
