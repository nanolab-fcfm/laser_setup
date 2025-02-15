import logging
import time

from pymeasure.display.widgets import PlotFrame, PlotWidget
from pymeasure.display.widgets.dock_widget import DockWidget
from pymeasure.display.windows import ManagedWindowBase
from pymeasure.experiment import Procedure, Results, unique_filename

from ...config import config
from ...procedures import BaseProcedure
from ..Qt import QtCore, QtGui, QtWidgets
from ..widgets import LogWidget, TextWidget

log = logging.getLogger(__name__)


class ExperimentWindow(ManagedWindowBase):
    """The main window for an experiment. It is used to display a
    `pymeasure.experiment.Procedure`, and allows for the experiment to be run
    from the GUI, by queuing it in the manager. It also allows for existing
    data to be loaded and displayed.
    """
    def __init__(
        self,
        cls: type[Procedure],
        title: str = '',
        inputs_in_scrollarea: bool = True,
        enable_file_input: bool = False,
        dock_plot_number: int = 2,
        icon: str | None = None,
        info_file: str | None = None,
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
            QtGui.QIcon(icon) if icon else self.style().standardIcon(
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

    def queue(self, procedure: type[Procedure] | None = None):
        if procedure is None:
            procedure = self.make_procedure()

        filename_kwargs: dict = dict(config.Filename).copy()
        prefix = filename_kwargs.pop('prefix', '') or procedure.__class__.__name__
        filename = unique_filename(config.Dir.data_dir,
                                   prefix=prefix, **filename_kwargs)
        log.info(f"Saving data to {filename}.")

        if hasattr(procedure, 'pre_startup') and callable(procedure.pre_startup):
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
        self.timer.timeout.connect(self._update_progress)

    def start(self, wait_time: float, fps: float = 30., decimals: int = 0):
        self.wait_time = wait_time
        self.frame_interval = 1 / fps
        self.total_frames = int(fps * wait_time)
        self.start_time = time.perf_counter()
        self.progress.setRange(0, self.total_frames)
        self.show()
        self.timer.start(max(1, round(1000 / fps)))
        self.d = decimals

    def _update_progress(self):
        elapsed_time = time.perf_counter() - self.start_time
        current_frame = int(elapsed_time / self.frame_interval)

        if current_frame >= self.total_frames:
            self.progress.setValue(self.total_frames)
            self.progress.setFormat(
                f"{self.wait_time:.{self.d}f} / {self.wait_time:.{self.d}f} s"
            )
            self.timer.stop()
            self.close()
        else:
            self.progress.setValue(current_frame)
            self.progress.setFormat(
                f"{elapsed_time:.{self.d}f} / {self.wait_time:.{self.d}f} s"
            )
