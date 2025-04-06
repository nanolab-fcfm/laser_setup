"""
Module to ensure compatibility with any Qt version. By default,
pyqtgraph.Qt from pymeasure.display.Qt is used.
"""
import sys

from pyqtgraph.console import ConsoleWidget  # noqa: F401
from qtpy import QtCore, QtGui, QtSql, QtWidgets  # noqa: F401


class Worker(QtCore.QObject):
    """Worker class to run a function in a separate thread. The result
    is emitted as a signal. If the thread is specified, the worker is
    moved to that thread, and the thread is stopped when the worker is
    done.
    """
    finished = QtCore.Signal(object)

    def __init__(
        self,
        func: callable,
        thread: QtCore.QThread = None,
        **kwargs
    ):
        super().__init__()
        self.func = func
        self.kwargs = kwargs
        if thread is not None:
            self.moveToThread(thread)
            thread.started.connect(self.run)
            thread.finished.connect(self.deleteLater)
            thread.finished.connect(thread.deleteLater)
            self.finished.connect(thread.quit)

    def run(self):
        result = self.func(**self.kwargs)
        self.finished.emit(result)


def make_app():
    """Make a Qt Application."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    return app
