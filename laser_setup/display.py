"""
This module contains the display functions for the GUI.
"""
import os
import sys
import time
import logging
from importlib.metadata import metadata
from typing import Type

from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import unique_filename, Results, Procedure
from pymeasure.display.widgets import InputsWidget
from pymeasure.display.manager import Experiment
from PyQt6.QtGui import QColor, QPalette, QPixmap
from PyQt6.QtCore import QLocale
from PyQt6.QtWidgets import QApplication, QStyle, QMainWindow, QWidget, QGridLayout, QPushButton, QTextEdit, QMessageBox, QHBoxLayout
from PyQt6 import QtWidgets, QtCore

from . import config, config_path, _config_file_used
from .utils import remove_empty_data
from .procedures import MetaProcedure, BaseProcedure

log = logging.getLogger(__name__)


class ProgressBar(QtWidgets.QDialog):
    """A simple progress bar dialog."""
    def __init__(self, parent=None, title="Waiting", text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(self)
        self.label.setText(text)
        self.progress = QtWidgets.QProgressBar(self)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.progress)
        self.setLayout(self._layout)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_progress)

    def start(self, wait_time, fps=30):
        self.wait_time = wait_time
        self.fps = fps
        self.frames = int(self.fps * wait_time)
        self.i = 0
        self.progress.setRange(0, self.frames)
        self.show()
        self.timer.start(max(1, round(1000/self.fps)))

    def update_progress(self):
        self.i += 1
        self.progress.setValue(self.i)
        self.progress.setFormat(f"{self.i/self.fps:.0f} / {self.wait_time:.0f} s")
        self.progress.repaint()
        if self.i >= self.frames:
            self.timer.stop()
            self.close()


class ExperimentWindow(ManagedWindow):
    """The main window for the GUI. It is used to display a
    `pymeasure.experiment.Procedure`, and allows for the experiment to be run
    from the GUI, by queuing it in the manager. It also allows for existing
    data to be loaded and displayed.
    """
    def __init__(self, cls: Type[Procedure], title: str = '', **kwargs):
        self.cls = cls
        sequencer_kwargs = dict(
            sequencer = hasattr(cls, 'SEQUENCER_INPUTS'),
            sequencer_inputs = cls.SEQUENCER_INPUTS if hasattr(cls, 'SEQUENCER_INPUTS') else None,
            # sequence_file = f'sequences/{cls.SEQUENCER_INPUTS[0]}_sequence.txt' if hasattr(cls, 'SEQUENCER_INPUTS') else None,
        )
        super().__init__(
            procedure_class=cls,
            inputs=cls.INPUTS,
            displays=cls.INPUTS,
            x_axis=cls.DATA_COLUMNS[0],
            y_axis=cls.DATA_COLUMNS[1],
            inputs_in_scrollarea=True,
            **sequencer_kwargs,
            **kwargs
        )
        self.setWindowTitle(title)

    def queue(self, procedure: Type[Procedure] = None):
        if procedure is None:
            procedure = self.make_procedure()

        directory = config['Filename']['directory']
        filename = unique_filename(
            directory,
            prefix=self.cls.__name__,
            dated_folder=True,
            )
        log.info(f"Saving data to {filename}.")
        if hasattr(procedure, 'update_parameters'):
            procedure.update_parameters()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)

    def closeEvent(self, event):
        if self.manager.is_running():
            reply = QMessageBox.question(self, 'Message',
                        'Do you want to close the window? This will abort the current experiment.',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            self.manager.abort()
            time.sleep(0.5)
        self.log_widget._blink_qtimer.stop()
        super().closeEvent(event)


class MetaProcedureWindow(QMainWindow):
    """Window to set up a sequence of procedures. It manages the parameters
    for the sequence, and displays an ExperimentWindow for each procedure.
    """
    aborted: bool = False
    status_labels = []
    def __init__(self, cls: Type[MetaProcedure], title: str = '', **kwargs):
        super().__init__(**kwargs)
        self.cls = cls

        self.resize(200*(len(cls.procedures)+1), 480)
        self.setWindowTitle(title + f" ({', '.join((proc.__name__ for proc in cls.procedures))})")

        layout = QHBoxLayout()
        layout.addLayout(self._get_procedure_vlayout(cls))
        widget = InputsWidget(BaseProcedure, inputs=BaseProcedure.INPUTS[1:])
        widget.layout().setSpacing(10)
        widget.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget)
        for i, proc in enumerate(cls.procedures):
            layout.addLayout(self._get_procedure_vlayout(proc))
            proc_inputs = list(proc.INPUTS)
            if BaseProcedure in proc.__mro__:
                for input in BaseProcedure.INPUTS:
                    proc_inputs.remove(input)

            widget = InputsWidget(proc, inputs=proc_inputs)
            widget.layout().setSpacing(10)
            widget.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QtWidgets.QScrollArea.Shape.NoFrame)

        inputs = QtWidgets.QWidget(self)
        inputs.setLayout(layout)
        inputs.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum,
                                QtWidgets.QSizePolicy.Policy.Fixed)
        scroll_area.setWidget(inputs)

        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(scroll_area, 1)

        self.queue_button = QtWidgets.QPushButton("Queue")
        vbox.addWidget(self.queue_button)
        self.queue_button.clicked.connect(self.queue)

        container = QWidget()
        container.setLayout(vbox)

        self.setCentralWidget(container)

    def _get_procedure_vlayout(self, proc: Type[Procedure]):
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.setSpacing(0)
        vlayout.addWidget(QtWidgets.QLabel(proc.__name__ + '\n→'))
        self.status_labels.append(QtWidgets.QLabel(self))
        pixmap = QPixmap(20, 20)
        pixmap.fill(QColor('white'))
        self.status_labels[-1].setPixmap(pixmap)
        vlayout.addWidget(self.status_labels[-1])
        vlayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        return vlayout

    def set_status(self, index: int, color: str):
        def func():
            pixmap = QPixmap(20, 20)
            pixmap.fill(QColor(color))
            self.status_labels[index + 1].setPixmap(pixmap)
        return func

    def queue(self):
        log.info("Queueing the procedures.")
        self.set_status(-1, 'yellow')()
        for i in range(len(self.cls.procedures)):
            self.set_status(i, 'white')()
        self.queue_button.setEnabled(False)
        inputs = self.findChildren(InputsWidget)
        base_parameters = inputs[0].get_procedure()._parameters
        for i, proc in enumerate(self.cls.procedures):
            # Spawn the corresponding ExperimentWindow and queue it
            if proc.__name__ == 'Wait':
                wait_time = inputs[i+1].get_procedure().wait_time
                self.set_status(i, 'yellow')()
                self.wait(wait_time)
                self.set_status(i, 'green')()

            else:
                window = ExperimentWindow(proc, title=proc.__name__)
                parameters = inputs[i+1].get_procedure()._parameters | base_parameters
                window.set_parameters(parameters)

                window.queue_button.hide()
                window.browser_widget.clear_button.hide()
                window.browser_widget.hide_button.hide()
                window.browser_widget.open_button.hide()
                window.browser_widget.show_button.hide()
                window.show()
                window.queue_button.click()

                # Update the status label
                window.manager.running.connect(self.set_status(i, 'yellow'))
                window.manager.finished.connect(self.set_status(i, 'green'))
                window.manager.failed.connect(self.set_status(i, 'red'))
                window.manager.aborted.connect(self.set_status(i, 'red'))

                # Window managing
                window.manager.aborted.connect(self.aborted_procedure(window))
                window.manager.failed.connect(self.failed_procedure(window))
                window.manager.finished.connect(window.close)

                # Non-blocking wait for the procedure to finish
                loop = QtCore.QEventLoop()
                window.manager.aborted.connect(loop.quit)
                window.manager.failed.connect(loop.quit)
                window.manager.finished.connect(loop.quit)
                loop.exec()

                if self.aborted:
                    break

        self.queue_button.setEnabled(True)
        if not self.aborted: log.info("Sequence finished.")
        self.set_status(-1, 'red' if self.aborted else 'green')()
        self.aborted = False

    @QtCore.pyqtSlot()
    def aborted_procedure(self, window: ExperimentWindow, close_window=True):
        def func():
            timeout = 30
            t_text = lambda t: f'Abort (continuing in {t} s)'
            t_iter = iter(range(timeout-1, -1, -1))

            window.abort_button.setEnabled(False)

            reply = QMessageBox(self)
            reply.setWindowTitle(t_text(timeout))
            reply.setText('This experiment was aborted. Do you want to abort the rest of the sequence?')
            reply.setIcon(QMessageBox.Icon.Warning)
            reply.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            reply.setDefaultButton(QMessageBox.StandardButton.No)
            reply.setWindowModality(QtCore.Qt.WindowModality.NonModal)

            # Create a QTimer to update the title every second
            timer = QtCore.QTimer()
            timer.timeout.connect(lambda: reply.setWindowTitle(t_text(next(t_iter))))
            timer.start(1000)

            # Close the message box after timeout
            QtCore.QTimer.singleShot(timeout*1000, reply.close)

            result = reply.exec()
            if result == QMessageBox.StandardButton.Yes:
                log.warning("Sequence aborted.")
                self.aborted = True

            if close_window:
                window.close()

        return func

    @QtCore.pyqtSlot()
    def failed_procedure(self, window: ExperimentWindow):
        def func():
            log.error(f"Procedure {window.cls.__name__} failed to execute")
            self.aborted_procedure(window, close_window=False)()
        return func

    def wait(self, wait_time: float, progress_bar: bool = True):
        """Waits for a given amount of time. Creates a progress bar."""
        log.info(f"Waiting for {wait_time} seconds.")
        if progress_bar:
            self.progress = ProgressBar(self, text="Waiting for the next procedure.")
            self.progress.start(wait_time)
            self.progress.exec()

        else:
            time.sleep(wait_time)


class MainWindow(QMainWindow):
    def __init__(
            self,
            sequences: dict[str, Type[MetaProcedure]],
            experiments: dict[str, Type[Procedure]],
            scripts: dict[str, callable],
            **kwargs
        ):
        super().__init__(**kwargs)
        self.setWindowTitle('Laser Setup')
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.resize(640, 480)
        self.setCentralWidget(QWidget())

        self.sequences = sequences
        self.experiments = experiments
        self.scripts = scripts
        self.gridx = max(len(experiments), len(scripts), 3)
        self.windows = {}

        # Experiment Buttons
        self._layout = QGridLayout(self.centralWidget())
        self.buttons = {}
        for i, (cls, name) in enumerate(experiments.items()):
            self.buttons[cls] = QPushButton(name)
            self.buttons[cls].clicked.connect(self.open_app(cls))
            self.buttons[cls].setToolTip(cls.__doc__)
            self._layout.addWidget(self.buttons[cls], 2, i)

        # README Widget
        readme = QTextEdit(readOnly=True)
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

        # Settings Button
        settings = QPushButton('Settings')
        settings.clicked.connect(self.edit_settings)
        self._layout.addWidget(settings, 0, 0)

        # Secuences Buttons
        for i, (cls, name) in enumerate(sequences.items()):
            self.buttons[cls] = QPushButton(name)
            self.buttons[cls].clicked.connect(self.open_sequence(cls))
            self.buttons[cls].setToolTip(cls.__doc__)
            self._layout.addWidget(self.buttons[cls], 0, 1+i)

        # Reload window button
        self.reload = QPushButton('Reload')
        self.reload.clicked.connect(lambda: os.execl(sys.executable, sys.executable, '.', *sys.argv[1:]))
        self._layout.addWidget(self.reload, 0, self.gridx-1)

        for i, (func, name) in enumerate(scripts.items()):
            self.buttons[func] = QPushButton(name)
            self.buttons[func].clicked.connect(self.run_script(func))
            self.buttons[func].setToolTip(func.__doc__)
            self._layout.addWidget(self.buttons[func], 3, i)

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
        error_dialog = QMessageBox()
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(f"An error occurred:\n{message}\nPlease reload the program.")
        error_dialog.setIcon(QMessageBox.Icon.Critical)
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


def display_window(Window: Type[QMainWindow], *args):
    """Displays the window for the given class. Allows for the
    window to be run from the GUI, by queuing it in the manager.
    It also allows for existing data to be loaded and displayed.

    :param Window: The Qt Window subclass to display.
    :param args: The arguments to pass to the window class.
    """
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setPalette(get_dark_palette())
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    window = Window(*args)
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
    palette = QPalette()

    # Set the background color
    palette.setColor(QPalette.ColorRole.Window, QColor(50, 50, 50))

    # Set the title text color
    palette.setColor(QPalette.ColorRole.WindowText, QColor(200, 200, 200))

    # Set the input text color
    palette.setColor(QPalette.ColorRole.Text, QColor(200, 200, 200))

    # Set the button color
    palette.setColor(QPalette.ColorRole.Button, QColor(30, 30, 30))

    # Set the button text color
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(200, 200, 200))

    # Set the base color
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))

    # Set the alternate background color
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))

    # Set the highlight color
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))

    # Set the highlighted text color
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(240, 240, 240))

    return palette

