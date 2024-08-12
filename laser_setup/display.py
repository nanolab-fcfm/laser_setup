"""
This module contains the display functions for the GUI.
"""
import os
import sys
import time
import logging
from importlib.metadata import metadata
from typing import Type

from pymeasure.experiment import unique_filename, Results, Procedure
from pymeasure.display.widgets import InputsWidget
from pymeasure.display.windows import ManagedWindow
from pymeasure.display.Qt import QtGui, QtWidgets, QtCore

from . import config, config_path, _config_file_used
from .utils import remove_empty_data
from .procedures import MetaProcedure, ChipProcedure

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
            sequencer_inputs = getattr(cls, 'SEQUENCER_INPUTS', None),
            # sequence_file = f'sequences/{cls.SEQUENCER_INPUTS[0]}_sequence.txt' if hasattr(cls, 'SEQUENCER_INPUTS') else None,
        )
        super().__init__(
            procedure_class=cls,
            inputs=getattr(cls, 'INPUTS', []),
            displays=getattr(cls, 'INPUTS', []),
            x_axis=cls.DATA_COLUMNS[0],
            y_axis=cls.DATA_COLUMNS[1],
            inputs_in_scrollarea=True,
            enable_file_input=False,        # File Input incompatible with PyQt6
            **sequencer_kwargs,
            **kwargs
        )
        if bool(eval(config['GUI']['dark_mode'])):
            self.plot_widget.plot_frame.setStyleSheet('background-color: black;')
            self.plot_widget.plot_frame.plot_widget.setBackground('k')

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

        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)

    def closeEvent(self, event):
        if self.manager.is_running():
            reply = QtWidgets.QMessageBox.question(self, 'Message',
                        'Do you want to close the window? This will abort the current experiment.',
                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                    )

            if reply == QtWidgets.QMessageBox.StandardButton.No:
                event.ignore()
                return

            self.manager.abort()
            self.procedure_class.instruments.shutdown_all()
            time.sleep(0.5)
        self.log_widget._blink_qtimer.stop()
        super().closeEvent(event)


class MetaProcedureWindow(QtWidgets.QMainWindow):
    """Window to set up a sequence of procedures. It manages the parameters
    for the sequence, and displays an ExperimentWindow for each procedure.
    """
    aborted: bool = False
    status_labels = []
    inputs_ignored = ['show_more', 'chained_exec']

    def __init__(self, cls: Type[MetaProcedure], title: str = '', **kwargs):
        super().__init__(**kwargs)
        self.cls = cls

        self.resize(200*(len(cls.procedures)+1), 480)
        self.setWindowTitle(title + f" ({', '.join((proc.__name__ for proc in cls.procedures))})")

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(self._get_procedure_vlayout(cls))

        base_inputs = [i for i in ChipProcedure.INPUTS if i not in self.inputs_ignored]

        widget = InputsWidget(ChipProcedure, inputs=base_inputs)
        widget.layout().setSpacing(10)
        widget.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget)
        for i, proc in enumerate(cls.procedures):
            layout.addLayout(self._get_procedure_vlayout(proc))
            proc_inputs = list(proc.INPUTS)
            for input in base_inputs:
                try:
                    proc_inputs.remove(input)
                except ValueError:
                    pass

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

        container = QtWidgets.QWidget()
        container.setLayout(vbox)

        self.setCentralWidget(container)

    def _get_procedure_vlayout(self, proc: Type[Procedure]):
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.setSpacing(0)
        vlayout.addWidget(QtWidgets.QLabel(proc.__name__ + '\n→'))
        self.status_labels.append(QtWidgets.QLabel(self))
        pixmap = QtGui.QPixmap(20, 20)
        pixmap.fill(QtGui.QColor('white'))
        self.status_labels[-1].setPixmap(pixmap)
        vlayout.addWidget(self.status_labels[-1])
        vlayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        return vlayout

    def set_status(self, index: int, color: str):
        def func():
            pixmap = QtGui.QPixmap(20, 20)
            pixmap.fill(QtGui.QColor(color))
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
                parameters = base_parameters | inputs[i+1].get_procedure()._parameters
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

        self.cls.instruments.shutdown_all()
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

            reply = QtWidgets.QMessageBox(self)
            reply.setWindowTitle(t_text(timeout))
            reply.setText('This experiment was aborted. Do you want to abort the rest of the sequence?')
            reply.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            reply.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
            reply.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
            reply.setWindowModality(QtCore.Qt.WindowModality.NonModal)

            # Create a QTimer to update the title every second
            timer = QtCore.QTimer()
            timer.timeout.connect(lambda: reply.setWindowTitle(t_text(next(t_iter))))
            timer.start(1000)

            # Close the message box after timeout
            QtCore.QTimer.singleShot(timeout*1000, reply.close)

            result = reply.exec()
            if result == QtWidgets.QMessageBox.StandardButton.Yes:
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


class MainWindow(QtWidgets.QMainWindow):
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

        self.sequences = sequences
        self.experiments = experiments
        self.scripts = scripts
        self.gridx = max(len(experiments), len(scripts), 3)
        self.windows = {}

        # Experiment Buttons
        self._layout = QtWidgets.QGridLayout(self.centralWidget())
        self.buttons = {}
        for i, (cls, name) in enumerate(experiments.items()):
            self.buttons[cls] = QtWidgets.QPushButton(name)
            self.buttons[cls].clicked.connect(self.open_app(cls))
            self.buttons[cls].setToolTip(cls.__doc__)
            self._layout.addWidget(self.buttons[cls], 2, i)

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

        # Settings Button
        settings = QtWidgets.QPushButton('Settings')
        settings.clicked.connect(self.edit_settings)
        self._layout.addWidget(settings, 0, 0)

        # Secuences Buttons
        for i, (cls, name) in enumerate(sequences.items()):
            self.buttons[cls] = QtWidgets.QPushButton(name)
            self.buttons[cls].clicked.connect(self.open_sequence(cls))
            self.buttons[cls].setToolTip(cls.__doc__)
            self._layout.addWidget(self.buttons[cls], 0, 1+i)

        # Reload window button
        self.reload = QtWidgets.QPushButton('Reload')
        self.reload.clicked.connect(
            lambda: os.execl(sys.executable, sys.executable, '.', *sys.argv[1:])
        )
        self._layout.addWidget(self.reload, 0, self.gridx-1)

        for i, (func, name) in enumerate(scripts.items()):
            self.buttons[func] = QtWidgets.QPushButton(name)
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

