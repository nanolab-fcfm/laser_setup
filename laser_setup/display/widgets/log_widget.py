import logging

from pymeasure.display.log import LogHandler
from pymeasure.display.widgets import LogWidget
from pymeasure.display.widgets.log_widget import HTMLFormatter

from ..Qt import QtGui, QtWidgets


def get_log_config(
    fmt: str = '%(asctime)s: [%(levelname)s] %(message)s (%(name)s)',
    datefmt: str = '%I:%M:%S %p',
) -> tuple[str, str]:
    """Get the log format and dateformat for the log widgets.
    Defaults to this module's default formats.
    Falls back to the given arguments.

    :param fmt: Format string for the log messages.
    :param datefmt: Format string for the date in the log messages.
    :return: Tuple of format and dateformat strings.
    """
    logger = logging.getLogger(__name__)
    for handler in logger.handlers:
        if handler.formatter is not None:
            return handler.formatter._fmt, handler.formatter.datefmt

    return fmt, datefmt


class LogWidget(LogWidget):
    fmt, datefmt = get_log_config()

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
    fmt, datefmt = get_log_config()

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
