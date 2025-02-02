import logging
import time
from functools import partial
from typing import Type

from pymeasure.display.widgets import InputsWidget, PlotFrame, PlotWidget
from pymeasure.display.widgets.dock_widget import DockWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import Procedure, Results, unique_filename

from ..config import config, instantiate
from ..procedures import BaseProcedure
from ..Qt import QtCore, QtGui, QtWidgets
from .widgets import LogWidget, ProgressBar, TextWidget

log = logging.getLogger(__name__)


class ExperimentWindow(ManagedWindowBase):
    """The main window for an experiment. It is used to display a
    `pymeasure.experiment.Procedure`, and allows for the experiment to be run
    from the GUI, by queuing it in the manager. It also allows for existing
    data to be loaded and displayed.
    """
    def __init__(
        self,
        cls: Type[Procedure],
        title: str = '',
        inputs_in_scrollarea: bool = True,
        enable_file_input: bool = False,
        dock_plot_number: int = 2,
        icon: str = None,
        info_file: str = None,
        **kwargs
    ):
        self.cls = cls

        if config.Qt.GUI.dark_mode:
            PlotFrame.LABEL_STYLE['color'] = '#AAAAAA'

        if not hasattr(cls, 'DATA_COLUMNS') or len(cls.DATA_COLUMNS) < 2:
            raise AttributeError(
                f"Procedure {cls.__name__} must define DATA_COLUMNS with at least 2 columns."
            )

        self.x_axis = cls.DATA_COLUMNS[0]
        self.y_axis = cls.DATA_COLUMNS[1]
        self.log_widget = LogWidget("Experiment Log")
        self.plot_widget = PlotWidget("Results Graph", cls.DATA_COLUMNS, self.x_axis,
                                      self.y_axis)
        self.plot_widget.setMinimumSize(100, 200)

        self.text_widget = TextWidget('Information', file=info_file)
        self.dock_widget = DockWidget(
            'Dock', cls,
            x_axis_labels=[self.x_axis,],
            y_axis_labels=cls.DATA_COLUMNS[1:dock_plot_number+1],
        )
        if config.Qt.GUI.dark_mode:
            for plot_widget in (self.plot_widget, *self.dock_widget.plot_frames):
                plot_widget.setAutoFillBackground(True)
                plot_widget.plot_frame.setStyleSheet('background-color: black;')
                plot_widget.plot_frame.plot_widget.setBackground('k')

        widget_list = (self.plot_widget, self.log_widget, self.text_widget, self.dock_widget)

        super().__init__(
            procedure_class=cls,
            widget_list=widget_list,
            inputs=getattr(cls, 'INPUTS', []),
            displays=getattr(cls, 'INPUTS', []),
            inputs_in_scrollarea=inputs_in_scrollarea,
            enable_file_input=enable_file_input,
            sequencer=hasattr(cls, 'SEQUENCER_INPUTS'),
            sequencer_inputs=getattr(cls, 'SEQUENCER_INPUTS', None),
            sequence_file=getattr(cls, 'SEQUENCE_FILE', None),
            **kwargs
        )
        self.setWindowTitle(title or getattr(cls, 'name', cls.__name__) or cls.__name__)
        self.setWindowIcon(
            icon or self.style().standardIcon(
                QtWidgets.QStyle.StandardPixmap.SP_TitleBarMenuButton
            )
        )
        # Add a shutdown all button if the procedure is a BaseProcedure
        if issubclass(self.procedure_class, BaseProcedure):
            self.shutdown_button = QtWidgets.QPushButton('&Shutdown', self)
            self.shutdown_button.clicked.connect(self.procedure_class.instruments.shutdown_all)
            self.shutdown_button.setToolTip('Shutdown all instruments')
            self.abort_button.parent().layout().children()[0].insertWidget(2, self.shutdown_button)

        self.abort_button.setText('&Abort')
        self.queue_button.setText('&Queue')

        self.browser_widget.browser.measured_quantities.update([self.x_axis, self.y_axis])

        self.log = logging.getLogger()
        self.log.addHandler(self.log_widget.handler)
        self.log.setLevel(config.Logging.console_level)
        self.log.info(f"{self.__class__.__name__} connected to logging")

    def queue(self, procedure: Type[Procedure] = None):
        if procedure is None:
            procedure = self.make_procedure()

        filename_kwargs: dict = dict(config.Filename).copy()
        prefix = filename_kwargs.pop('prefix', '') or procedure.__class__.__name__
        filename = unique_filename(config.Dir.data_dir,
                                   prefix=prefix, **filename_kwargs)
        log.info(f"Saving data to {filename}.")

        if hasattr(procedure, 'pre_startup'):
            procedure.pre_startup()

        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self.manager.is_running():
            reply = QtWidgets.QMessageBox.question(
                self, 'Abort Experiment',
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

        self.log_widget._blinking_stop(self.log_widget.tab_index)
        self.log.removeHandler(self.log_widget.handler)
        if self.use_estimator:
            self.estimator.update_thread.join()
            del self.estimator.update_thread

        super().closeEvent(event)


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
        layout.addWidget(widget)
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
