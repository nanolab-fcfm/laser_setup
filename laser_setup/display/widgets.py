import time

from pymeasure.display.widgets import TabWidget
from .Qt import QtWidgets, QtCore, QtSql


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


class TextWidget(TabWidget, QtWidgets.QWidget):
    def __init__(self, name: str = None, parent=None, file: str = None):
        super().__init__(name, parent)
        self.view = QtWidgets.QTextEdit(self, readOnly=True)
        self.view.setReadOnly(True)
        self.view.setStyleSheet("""
            font-size: 12pt;
        """)
        try:
            with open(file, encoding='utf-8') as f:
                readme_text = f.read()
        except:
            readme_text = f'{file} not found :('
        self.view.setMarkdown(readme_text)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(0)

        vbox.addWidget(self.view)
        self.setLayout(vbox)
