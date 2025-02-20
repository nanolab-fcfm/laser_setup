import logging
import time
from functools import partial
from typing import Type, Literal

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

    :attr status_dict: Dictionary with the status labels and colors.
    :attr is_running: Flag to indicate if the sequence is running.
    :attr is_aborted: Flag to indicate if the sequence was aborted.
    """
    status_dict: dict[str, dict[Literal['label', 'color'], str]] = {
        'queued': {'label': '🠞', 'color': ''},
        'running': {'label': '⏳', 'color': 'yellow'},
        'aborted': {'label': '⛔', 'color': 'red'},
        'finished': {'label': '✔', 'color': 'green'},
    }
    is_running: bool = False
    is_aborted: bool = False

    def __init__(
        self,
        procedure_list: list[Type[BaseProcedure]],
        title: str = '',
        abort_timeout: int = 30,
        common_procedure: Type[BaseProcedure] = BaseProcedure,
        inputs_ignored: list[str] = [],
        **kwargs
    ):
        """Initialize the SequenceWindow with the given procedure list.

        :param procedure_list: List of procedures to execute.
        :param title: Title of the window.
        :param abort_timeout: Timeout for the abort message box.
        :param common_procedure: Class to group common parameters.
        :param inputs_ignored: List of inputs to ignore when grouping parameters.
        :param kwargs: Additional keyword arguments to pass to the window.
        """
        super().__init__(**kwargs)
        self.procedure_list = procedure_list
        self.abort_timeout = int(abort_timeout)
        self.common_procedure = common_procedure
        self.inputs_ignored = inputs_ignored

        self.sequence_start_time = 0.0
        self.procedure_start_times: list[float] = []
        self.procedure_done: list[bool] = []
        self.item_data: list[dict[str, QtWidgets.QLabel]] = []

        self.resize(200*(len(procedure_list)+1), 480)
        self.setWindowTitle(title + f" ({', '.join((proc.__name__ for proc in procedure_list))})")

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(self._build_item_layout(title))
        self.item_data[0]['timer_proc'].setText("")
        self.item_data[0]['timer_cum'].setText("0:00")

        base_inputs = [i for i in self.common_procedure.INPUTS if i not in self.inputs_ignored]

        widget = InputsWidget(self.common_procedure, inputs=base_inputs)
        widget.layout().setSpacing(10)
        widget.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget, 1)
        for i, proc in enumerate(self.procedure_list):
            layout.addLayout(self._build_item_layout(proc.__name__, i))

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

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_timers)
        self.timer.start(1000)

        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.timeout.connect(self._rotate_status)
        self.animation_timer.start(250)

    def _set_font_factor(self, item: QtWidgets.QWidget, factor: float):
        font = item.font()
        font.setPointSizeF(font.pointSizeF() * factor)
        item.setFont(font)

    def _build_item_layout(self, class_name: str, idx: int = None) -> QtWidgets.QVBoxLayout:
        """Build a vertical layout with status label and two timers."""
        vlayout = QtWidgets.QVBoxLayout()

        number = QtWidgets.QLabel(f"{idx + 1}" if idx is not None else "")
        self._set_font_factor(number, 0.8)
        vlayout.addWidget(number)

        title = QtWidgets.QLabel(class_name)
        vlayout.addWidget(title)

        status = RotatingLabel(self.status_dict["queued"]["label"])

        self._set_font_factor(status, 2.0)
        vlayout.addWidget(status)

        timer_proc = QtWidgets.QLabel("+0:00")
        timer_cum = QtWidgets.QLabel("=0:00")
        self._set_font_factor(timer_proc, 0.8)
        self._set_font_factor(timer_cum, 0.8)
        vlayout.addWidget(timer_proc)
        vlayout.addWidget(timer_cum)

        for label in (title, number, status, timer_proc, timer_cum):
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vlayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.item_data.append({
            "status": status,
            "timer_proc": timer_proc,
            "timer_cum": timer_cum
        })
        return vlayout

    def set_status(self, idx: int, status: str):
        status_label: RotatingLabel = self.item_data[idx]["status"]
        status_label.setText(self.status_dict[status]["label"])
        status_label.setStyleSheet(f"color: {self.status_dict[status]['color']};")
        status_label.set_angle(0)

    def queue(self):
        log.info("Queueing the procedures.")
        self.sequence_start_time = time.time()
        self.is_running = True
        self.procedure_start_times = [self.sequence_start_time]*len(self.procedure_list)
        self.procedure_done = [False]*len(self.procedure_list)

        self.set_status(0, 'running')
        for i in range(len(self.procedure_list)):
            self.set_status(i+1, 'queued')

        self.queue_button.setEnabled(False)
        inputs = self.findChildren(InputsWidget)
        base_parameters: dict = inputs[0].get_procedure()._parameters
        base_parameters = {k: v for k, v in base_parameters.items() if k not in self.inputs_ignored}
        for i, proc in enumerate(self.procedure_list):
            if proc.__name__ == 'Wait':
                self.procedure_start_times[i] = time.time()
                wait_time = inputs[i+1].get_procedure().wait_time
                self.set_status(i+1, 'running')
                self.wait(wait_time)
                self.set_status(i+1, 'finished')
                self.procedure_done[i] = True
                continue

            window_name = getattr(proc, 'name', proc.__name__)
            kwargs = {**instantiate(config.Qt.ExperimentWindow)}
            kwargs['title'] = window_name
            window = ExperimentWindow(proc, **kwargs)
            procedure_parameters = inputs[i+1].get_procedure()._parameters
            parameters = procedure_parameters | base_parameters
            window.set_parameters(parameters)

            # Hide the buttons and disable the inputs, as they're not needed
            window.queue_button.hide()
            window.browser_widget.clear_button.hide()
            window.browser_widget.hide_button.hide()
            window.browser_widget.open_button.hide()
            window.browser_widget.show_button.hide()

            for name in window.inputs._inputs:
                getattr(window.inputs, name).setEnabled(False)

            window.show()
            window.queue_button.click()

            self.procedure_start_times[i] = time.time()
            self.procedure_done[i] = False

            window.manager.aborted.connect(partial(self.aborted_procedure, window))
            window.manager.failed.connect(partial(self.failed_procedure, window))
            window.manager.finished.connect(window.close)

            window.manager.running.connect(partial(self.set_status, i+1, 'running'))
            window.manager.finished.connect(partial(self.set_status, i+1, 'finished'))
            window.manager.failed.connect(partial(self.set_status, i+1, 'aborted'))
            window.manager.aborted.connect(partial(self.set_status, i+1, 'aborted'))

            window.manager.finished.connect(partial(self._finish_procedure, i))
            window.manager.aborted.connect(partial(self._finish_procedure, i))
            window.manager.failed.connect(partial(self._finish_procedure, i))

            loop = QtCore.QEventLoop()
            window.manager.aborted.connect(loop.quit)
            window.manager.failed.connect(loop.quit)
            window.manager.finished.connect(loop.quit)
            loop.exec()

            if self.is_aborted:
                break

        self.common_procedure.instruments.shutdown_all()
        self.queue_button.setEnabled(True)
        self.is_running = False
        if not self.is_aborted:
            log.info("Sequence finished")

        self.set_status(0, 'aborted' if self.is_aborted else 'finished')
        self.is_aborted = False

    def _update_timers(self):
        if not self.is_running:
            return

        now = time.time()
        total_elapsed = int(now) - int(self.sequence_start_time)
        self.item_data[0]["timer_cum"].setText("=" + self._format_time(total_elapsed))

        try:
            idx = next(i for i, done in enumerate(self.procedure_done) if not done)
        except (StopIteration, IndexError):
            return

        proc_elapsed = int(now - self.procedure_start_times[idx])
        self.item_data[idx+1]["timer_proc"].setText("+" + self._format_time(proc_elapsed))
        self.item_data[idx+1]["timer_cum"].setText("=" + self._format_time(total_elapsed))

    def _format_time(self, seconds: int) -> str:
        if seconds >= 3600:
            return time.strftime("%H:%M:%S", time.gmtime(seconds))

        under_10_min = int(seconds < 600)
        return time.strftime("%M:%S", time.gmtime(seconds))[under_10_min:]

    def _finish_procedure(self, i: int):
        self.procedure_done[i] = True

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

        timer = QtCore.QTimer()
        timer.timeout.connect(lambda: reply.setWindowTitle(t_text % next(t_iter)))
        timer.start(1000)

        QtCore.QTimer.singleShot(self.abort_timeout*1000, reply.close)

        result = reply.exec()
        if result == QtWidgets.QMessageBox.StandardButton.Yes:
            log.warning("Sequence aborted.")
            self.is_aborted = True

        if close_window:
            window.close()

    @QtCore.Slot()
    def failed_procedure(self, window: ExperimentWindow):
        log.error(f"Procedure {window.cls.__name__} failed to execute")
        self.aborted_procedure(window, close_window=False)

    def wait(self, wait_time: float, progress_bar: bool = True):
        log.info(f"Waiting for {wait_time} seconds.")
        if progress_bar:
            self.progress = ProgressBar(self, text="Waiting for the next procedure.")
            self.progress.start(wait_time)
            self.progress.exec()

        else:
            time.sleep(wait_time)

    def _rotate_status(self):
        try:
            idx = next(i for i, done in enumerate(self.procedure_done) if not done)
        except (StopIteration, IndexError):
            return

        status: RotatingLabel = self.item_data[idx+1]["status"]
        status.set_angle(status._angle + 15)


class RotatingLabel(QtWidgets.QLabel):
    """A QLabel that rotates its text."""
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self._angle = 0

    def set_angle(self, angle: int):
        self._angle = angle
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.save()
        center = self.rect().center()
        painter.translate(center)
        painter.rotate(self._angle)
        painter.translate(-center)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(QtGui.QPalette.ColorRole.WindowText))
        painter.drawText(self.rect(), self.alignment(), self.text())
        painter.restore()
