from pymeasure.display.log import LogHandler
from pymeasure.display.widgets import LogWidget
from pymeasure.display.widgets.log_widget import HTMLFormatter

from ..Qt import QtGui, QtWidgets


class LogWidget(LogWidget):
    fmt = '%(asctime)s: %(message)s (%(name)s, %(levelname)s)'
    datefmt = '%I:%M:%S %p'

    tab_widget: QtWidgets.QTabWidget | None = None
    tab_index: int | None = None
    _original_color = None

    def _blink(self):
        if self.tab_index is None or self._blink_color is None or \
           self._original_color is None:
            return

        self.tab_widget.tabBar().setTabTextColor(
            self.tab_index,
            self._original_color if self._blink_state else QtGui.QColor(self._blink_color)
        )
        self._blink_state = not self._blink_state

    def _blinking_start(self, message):
        tab_index_unset = self.tab_index is None
        super()._blinking_start(message)
        if tab_index_unset and self.tab_index is not None:
            self._original_color = self.tab_widget.tabBar().tabTextColor(self.tab_index)

    def _blinking_stop(self, index):
        super()._blinking_stop(index)
        if index == self.tab_index:
            # For some reason this fixes _blink_color being None at the wrong time
            # self._blink_color = ''
            pass


class LogsWidget(QtWidgets.QWidget):
    fmt = '%(asctime)s: %(message)s (%(name)s, %(levelname)s)'
    datefmt = '%I:%M:%S %p'

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self._setup_ui()
        self._layout()

    def _setup_ui(self):
        self.view = QtWidgets.QPlainTextEdit(self)
        self.view.setReadOnly(True)
        self.handler = LogHandler()
        self.handler.setFormatter(HTMLFormatter(fmt=self.fmt, datefmt=self.datefmt))
        self.handler.connect(self.view.appendHtml)

    def _layout(self):
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)
