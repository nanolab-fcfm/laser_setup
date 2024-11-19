import time
import logging
from typing import Type

from pymeasure.experiment import unique_filename, Results, Procedure
from pymeasure.display.widgets import InputsWidget, PlotFrame
from pymeasure.display.windows import ManagedWindow
from pymeasure.display.Qt import QtGui, QtWidgets, QtCore

from .. import config
from .widgets import TextWidget, ProgressBar
from ..procedures import BaseProcedure, ChipProcedure

log = logging.getLogger(__name__)


class ExperimentWindow(ManagedWindow):
    """The main window for an experiment. It is used to display a
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
        if bool(eval(config['GUI']['dark_mode'])):
            PlotFrame.LABEL_STYLE['color'] = '#AAAAAA'

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
        self.setWindowIcon(
            self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)
        )

        if issubclass(self.procedure_class, BaseProcedure):
            self.shutdown_button = QtWidgets.QPushButton('Shutdown', self)
            self.shutdown_button.clicked.connect(self.procedure_class.instruments.shutdown_all)
            self.abort_button.parent().layout().children()[0].insertWidget(2, self.shutdown_button)

        widget = TextWidget('Information', parent=self, file=config['GUI']['info_file'])
        self.widget_list += (widget,)
        self.tabs.addTab(widget, widget.name)

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

        if hasattr(procedure, 'pre_startup'):
            procedure.pre_startup()
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
            if issubclass(self.procedure_class, BaseProcedure):
                self.procedure_class.instruments.shutdown_all()
            time.sleep(0.5)
        self.log_widget._blink_qtimer.stop()
        super().closeEvent(event)


class SequenceWindow(QtWidgets.QMainWindow):
    """Window to set up a sequence of procedures. It manages the parameters
    for the sequence, and displays an ExperimentWindow for each procedure.
    """
    aborted: bool = False
    status_labels = []
    inputs_ignored = ['show_more', 'chained_exec']

    def __init__(self, procedure_list: list[Type[Procedure]], title: str = '', **kwargs):
        super().__init__(**kwargs)
        self.procedure_list = procedure_list

        self.resize(200*(len(procedure_list)+1), 480)
        self.setWindowTitle(title + f" ({', '.join((proc.__name__ for proc in procedure_list))})")

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(self._get_procedure_vlayout(title))

        base_inputs = [i for i in ChipProcedure.INPUTS if i not in self.inputs_ignored]

        widget = InputsWidget(ChipProcedure, inputs=base_inputs)
        widget.layout().setSpacing(10)
        widget.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget)
        for i, proc in enumerate(procedure_list):
            layout.addLayout(self._get_procedure_vlayout(proc.__name__))
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

    def _get_procedure_vlayout(self, class_name: str):
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.setSpacing(0)
        vlayout.addWidget(QtWidgets.QLabel(class_name + '\n→'))
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
        for i in range(len(self.procedure_list)):
            self.set_status(i, 'white')()
        self.queue_button.setEnabled(False)
        inputs = self.findChildren(InputsWidget)
        base_parameters = inputs[0].get_procedure()._parameters
        base_parameters = {k: v for k, v in base_parameters.items() if k not in self.inputs_ignored}
        for i, proc in enumerate(self.procedure_list):
            # Spawn the corresponding ExperimentWindow and queue it
            if proc.__name__ == 'Wait':
                wait_time = inputs[i+1].get_procedure().wait_time
                self.set_status(i, 'yellow')()
                self.wait(wait_time)
                self.set_status(i, 'green')()
                continue

            window = ExperimentWindow(proc, title=proc.__name__)
            procedure_parameters = inputs[i+1].get_procedure()._parameters
            parameters = procedure_parameters | base_parameters
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

        BaseProcedure.instruments.shutdown_all()
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
