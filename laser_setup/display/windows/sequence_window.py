import logging
import time
from functools import partial
from typing import Type

from pymeasure.display.widgets import InputsWidget

from ...config import config, instantiate
from ...procedures import BaseProcedure
from ..Qt import QtCore, QtGui, QtWidgets
from .experiment_window import ExperimentWindow, ProgressBar

log = logging.getLogger(__name__)


class SequenceWindow(QtWidgets.QMainWindow):
    """Window to set up a sequence of procedures. It manages the parameters
    for the sequence, and displays an ExperimentWindow for each procedure.
    The common_procedure class attribute is used to group parameters that are
    common to all procedures in the sequence. To avoid this behavior for a
    specific parameter, add it to the inputs_ignored list.

    :attr abort_timeout: int: Timeout for the abort message box.
    :attr inputs_ignored: list[str]: List of inputs to ignore when grouping parameters.
    :attr common_procedure: type[BaseProcedure]: Class to group common parameters.
    """
    status_labels = []
    aborted: bool = False

    def __init__(
        self,
        procedure_list: list[Type[BaseProcedure]],
        title: str = '',
        abort_timeout: int = 30,
        common_procedure: Type[BaseProcedure] = BaseProcedure,
        inputs_ignored: list[str] = [],
        **kwargs
    ):
        super().__init__(**kwargs)
        self.procedure_list = procedure_list
        self.abort_timeout = int(abort_timeout)
        self.common_procedure = common_procedure
        self.inputs_ignored = inputs_ignored

        self.resize(200*(len(procedure_list)+1), 480)
        self.setWindowTitle(title + f" ({', '.join((proc.__name__ for proc in procedure_list))})")

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(self._get_procedure_vlayout(title))

        base_inputs = [i for i in self.common_procedure.INPUTS if i not in self.inputs_ignored]

        widget = InputsWidget(self.common_procedure, inputs=base_inputs)
        widget.layout().setSpacing(10)
        widget.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget, 1)
        for proc in procedure_list:
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
            layout.addWidget(widget, 1)

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
        pixmap = QtGui.QPixmap(20, 20)
        pixmap.fill(QtGui.QColor(color))
        self.status_labels[index + 1].setPixmap(pixmap)

    def queue(self):
        log.info("Queueing the procedures.")
        self.set_status(-1, 'yellow')
        for i in range(len(self.procedure_list)):
            self.set_status(i, 'white')
        self.queue_button.setEnabled(False)
        inputs = self.findChildren(InputsWidget)
        base_parameters = inputs[0].get_procedure()._parameters
        base_parameters = {k: v for k, v in base_parameters.items() if k not in self.inputs_ignored}
        for i, proc in enumerate(self.procedure_list):
            # Spawn the corresponding ExperimentWindow and queue it
            if proc.__name__ == 'Wait':
                wait_time = inputs[i+1].get_procedure().wait_time
                self.set_status(i, 'yellow')
                self.wait(wait_time)
                self.set_status(i, 'green')
                continue

            window_name = getattr(proc, 'name', proc.__name__)
            kwargs = {**instantiate(config.Qt.ExperimentWindow)}
            kwargs['title'] = window_name
            window = ExperimentWindow(proc, **kwargs)
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
            window.manager.running.connect(partial(self.set_status, i, 'yellow'))
            window.manager.finished.connect(partial(self.set_status, i, 'green'))
            window.manager.failed.connect(partial(self.set_status, i, 'red'))
            window.manager.aborted.connect(partial(self.set_status, i, 'red'))

            # Window managing
            window.manager.aborted.connect(partial(self.aborted_procedure, window))
            window.manager.failed.connect(partial(self.failed_procedure, window))
            window.manager.finished.connect(window.close)

            # Non-blocking wait for the procedure to finish
            loop = QtCore.QEventLoop()
            window.manager.aborted.connect(loop.quit)
            window.manager.failed.connect(loop.quit)
            window.manager.finished.connect(loop.quit)
            loop.exec()

            if self.aborted:
                break

        self.common_procedure.instruments.shutdown_all()
        self.queue_button.setEnabled(True)
        if not self.aborted:
            log.info("Sequence finished.")

        self.set_status(-1, 'red' if self.aborted else 'green')
        self.aborted = False

    @QtCore.Slot()
    def aborted_procedure(self, window: ExperimentWindow, close_window=True):
        t_text = 'Abort (continuing in %d s)'
        t_iter = iter(range(self.abort_timeout-1, -1, -1))

        window.abort_button.setEnabled(False)

        reply = QtWidgets.QMessageBox(self)
        reply.setWindowTitle(t_text % self.abort_timeout)
        reply.setText('This experiment was aborted. Do you want to abort the rest of the sequence?')
        reply.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        reply.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        reply.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        reply.setWindowModality(QtCore.Qt.WindowModality.NonModal)

        # Create a QTimer to update the title every second
        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: reply.setWindowTitle(t_text % next(t_iter)))
        timer.start(1000)

        # Close the message box after timeout
        QtCore.QTimer.singleShot(self.abort_timeout*1000, reply.close)

        result = reply.exec()
        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            log.warning("Sequence aborted.")
            self.aborted = True

        if close_window:
            window.close()

    @QtCore.Slot()
    def failed_procedure(self, window: ExperimentWindow):
        log.error(f"Procedure {window.cls.__name__} failed to execute")
        self.aborted_procedure(window, close_window=False)

    def wait(self, wait_time: float, progress_bar: bool = True):
        """Waits for a given amount of time. Creates a progress bar."""
        log.info(f"Waiting for {wait_time} seconds.")
        if progress_bar:
            self.progress = ProgressBar(self, text="Waiting for the next procedure.")
            self.progress.start(wait_time)
            self.progress.exec()

        else:
            time.sleep(wait_time)
