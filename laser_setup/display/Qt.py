"""
Module to ensure compatibility with any Qt version. By default,
pyqtgraph.Qt from pymeasure.display.Qt is used.
"""
from importlib import import_module
from typing import TYPE_CHECKING

from pyqtgraph.Qt import QT_LIB
from pymeasure.display.Qt import QtGui, QtWidgets, QtCore


if not TYPE_CHECKING:
    # Import Qt modules from the current Qt library
    QtSql = import_module(f'{QT_LIB}.QtSql')

else:
    # For type checking, PyQt6 is used
    from PyQt6 import QtSql


class Worker(QtCore.QObject):
    """Worker class to run a function in a separate thread. The result
    is emitted as a signal. If the thread is specified, the worker is
    moved to that thread, and the thread is stopped when the worker is
    done.
    """
    finished = QtCore.pyqtSignal(object)
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

    def run(self):
        result = self.func(**self.kwargs)
        self.finished.emit(result)
