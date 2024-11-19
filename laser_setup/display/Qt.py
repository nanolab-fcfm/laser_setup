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
