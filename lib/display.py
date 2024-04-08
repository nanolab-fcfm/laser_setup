"""
This module contains the display functions for the GUI.
"""
import os
import sys
import time
import logging
from typing import Type

from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import unique_filename, Results, Procedure
from pymeasure.display.widgets import InputsWidget
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import QLocale
from PyQt6.QtWidgets import QApplication, QStyle, QMainWindow, QWidget, QGridLayout, QPushButton, QTextEdit, QMessageBox, QHBoxLayout
from PyQt6 import QtWidgets, QtCore

from . import config, _config_file_used
from .utils import remove_empty_data
from .procedures import MetaProcedure, BaseProcedure

log = logging.getLogger(__name__)


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
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


class MetaProcedureWindow(QMainWindow):
    """Window to set up a sequence of procedures. It manages the parameters
    for the sequence, and displays an ExperimentWindow for each procedure.
    """
    def __init__(self, cls: Type[MetaProcedure], title: str = '', **kwargs):
        super().__init__(**kwargs)
        self.cls = cls
        self.resize(200*(len(cls.procedures)+1), 480)
        self.setWindowTitle(title + f" ({', '.join((proc.__name__ for proc in cls.procedures))})")

        layout = QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel(cls.__name__ + '\n→'))
        widget = InputsWidget(BaseProcedure, inputs=BaseProcedure.INPUTS[1:])
        widget.layout().setSpacing(10)
        widget.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget)
        for i, proc in enumerate(cls.procedures):
            layout.addWidget(QtWidgets.QLabel(proc.__name__ + '\n→'))
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

    def queue(self):
        log.info("Queueing the procedures.")
        self.queue_button.setEnabled(False)
        inputs = self.findChildren(InputsWidget)
        base_parameters = inputs[0].get_procedure()._parameters
        for i, proc in enumerate(self.cls.procedures):
            # Spawn the corresponding ExperimentWindow and queue it
            if proc.__name__ == 'Wait':
                wait_time = inputs[i+1].get_procedure().wait_time
                self.wait(wait_time)

            else:
                window = ExperimentWindow(proc, title=proc.__name__)
                parameters = inputs[i+1].get_procedure()._parameters | base_parameters
                window.set_parameters(parameters)

                window.queue_button.hide()
                window.browser_widget.clear_button.hide()
                window.browser_widget.hide_button.hide()
                window.browser_widget.open_button.hide()
                window.browser_widget.show_button.hide()
                window.abort_button.clicked.disconnect()
                window.abort_button.clicked.connect(self.abort_current(window))
                window.show()
                window.queue_button.click()
                
                # Wait for the procedure to finish
                while window.manager.is_running() and window.isVisible():
                    QtWidgets.QApplication.processEvents()
                    log.debug(f"Waiting for {proc.__name__} to finish.")
                    time.sleep(0.1)

                if window.manager.is_running():
                    window.manager.abort()
                    
                window.close()
    

        self.close()
        
    def abort_current(self, window: ExperimentWindow):
        def func():
            window.manager.abort()
            window.close()
            reply = QMessageBox.question(self, 'Abort', 'Do you want to abort the rest of the sequence?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.close()
                sys.exit()

        return func

    def wait(self, wait_time: float, progress_bar: bool = True):
        """Waits for a given amount of time. Creates a progress bar."""
        log.info(f"Waiting for {wait_time} seconds.")
        if progress_bar:
            progress = QtWidgets.QProgressBar()
            progress.setWindowTitle("Waiting")
            progress.setRange(0, 1000)
            progress.setValue(0)
            progress.show()
            for i in range(1000):
                progress.setValue(i+1)
                progress.setFormat(f"{i/1000*wait_time:.0f} s")
                QtWidgets.QApplication.processEvents()
                time.sleep(wait_time/1000)
            progress.hide()
        
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
        self.layout = QGridLayout(self.centralWidget())
        self.buttons = {}
        for i, (name, cls) in enumerate(experiments.items()):
            self.buttons[name] = QPushButton(name)
            self.buttons[name].clicked.connect(self.open_app(name))
            self.buttons[name].setToolTip(cls.__doc__)
            self.layout.addWidget(self.buttons[name], 2, i)

        # README Widget
        readme = QTextEdit(readOnly=True)
        readme.setStyleSheet("""
            font-size: 12pt;
        """)
        with open('README.md') as f:
            readme.setMarkdown(f.read())
        self.layout.addWidget(readme, 1, 0, 1, self.gridx)
        
        # Settings Button
        settings = QPushButton('Settings')
        settings.clicked.connect(self.edit_settings)
        self.layout.addWidget(settings, 0, 0)
        
        # Secuences Button
        meta_procedure = QPushButton('Sequence')
        meta_procedure.clicked.connect(self.open_sequence('Main Sequence'))
        meta_procedure.setToolTip(MetaProcedure.__doc__)
        self.layout.addWidget(meta_procedure, 0, 1)
        
        
        # Reload window button
        self.reload = QPushButton('Reload')
        self.reload.clicked.connect(lambda: os.execl(sys.executable, sys.executable, *sys.argv))
        self.layout.addWidget(self.reload, 0, self.gridx-1)
        
        for i, (name, func) in enumerate(scripts.items()):
            button = QPushButton(name)
            button.clicked.connect(self.run_script(name))
            button.setToolTip(func.__doc__)
            self.layout.addWidget(button, 3, i)
            
    def open_sequence(self, name: str):
        def func():
            self.windows[name] = MetaProcedureWindow(self.sequences[name], title=name, parent=self)
            self.windows[name].show()
        return func

    def open_app(self, name: str):
        def func():
            self.windows[name] = ExperimentWindow(self.experiments[name], title=name, parent=self)
            self.windows[name].show()
        return func
    
    def run_script(self, name: str):
        def func():
            try:
                self.scripts[name](parent=self)
            except TypeError:
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

