import sys
from pathlib import Path

from pymeasure.experiment import Procedure

from .. import __version__
from ..config import config, instantiate, DefaultPaths
from ..utils import remove_empty_data
from .Qt import QtCore, QtGui, QtWidgets, make_app

_app_id = "NanoLabFCFM.LaserSetup.v" + __version__


class ShortcutFilter(QtCore.QObject):
    """Event filter for the application to handle shortcuts.
    """
    fontsize_range = range(8, 32)
    zoom_in_keys = (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal)
    zoom_out_keys = (QtCore.Qt.Key.Key_Minus, QtCore.Qt.Key.Key_Underscore)
    maximize_keys = (QtCore.Qt.Key.Key_F11,)
    close_keys = (QtCore.Qt.Key.Key_W,)

    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.app = app

    def eventFilter(self, obj, event: QtCore.QEvent) -> bool:
        window = self.app.activeWindow()
        if isinstance(event, QtGui.QKeyEvent) and event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                if key in self.close_keys and window is not None:
                    window.close()
                    return True
                elif key in self.zoom_in_keys:
                    self.app_zoom(1)
                    return True
                elif key in self.zoom_out_keys:
                    self.app_zoom(-1)
                    return True

            if key in self.maximize_keys:
                if window:
                    if window.isMaximized():
                        window.showNormal()
                    else:
                        window.showMaximized()

                return True

        return super().eventFilter(obj, event)

    def app_zoom(self, factor: int = 1):
        """Zooms the whole application in or out by the given factor."""
        font: QtGui.QFont = self.app.font()
        if not (new_size := font.pointSize() + factor) in self.fontsize_range:
            return

        font.setPointSize(new_size)
        self.app.setFont(font)


def get_dark_palette():
    palette = QtGui.QPalette()
    palette_dict = {
        'Window': (50, 50, 50),
        'WindowText': (200, 200, 200),
        'Text': (200, 200, 200),
        'Button': (30, 30, 30),
        'ButtonText': (200, 200, 200),
        'Base': (35, 35, 35),
        'AlternateBase': (45, 45, 45),
        'Link': (42, 130, 218),
        'Highlight': (42, 130, 218),
        'HighlightedText': (240, 240, 240),
    }

    for role, color in palette_dict.items():
        palette.setColor(
            getattr(QtGui.QPalette.ColorRole, role), QtGui.QColor(*color)
        )
    return palette


def display_window(procedure: type[Procedure] | None = None, **kwargs):
    """If no procedure is given, display the main window. Otherwise, display
    the experiment window with the given procedure.

    The window style and palette are set according to the configuration file.
    A splash screen is shown while the window is loading.

    :param procedure: The procedure to display in the experiment window.
    :param kwargs: Additional keyword arguments to pass to the window.
    """
    _patch_taskbar_icon()
    app = make_app()
    shortcut_filter = ShortcutFilter(app)
    app.installEventFilter(shortcut_filter)

    if not (splash_image := Path(config.Qt.GUI.splash_image)).is_file():
        splash_image = DefaultPaths.splash
    pixmap = QtGui.QPixmap(splash_image.as_posix())
    pixmap = pixmap.scaledToHeight(480)
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()

    # Get available styles with QtWidgets.QStyleFactory.keys()
    app.setStyle(config.Qt.GUI.style)
    if config.Qt.GUI.dark_mode:
        app.setPalette(get_dark_palette())
    QtCore.QLocale.setDefault(QtCore.QLocale(
        QtCore.QLocale.Language.English,
        QtCore.QLocale.Country.UnitedStates
    ))
    font = app.font()
    if config.Qt.GUI.font:
        font.setFamily(config.Qt.GUI.font)
    font.setPointSize(config.Qt.GUI.font_size)
    app.setFont(font)

    if procedure is None:
        from .windows.main_window import MainWindow
        kwargs.update(**instantiate(config.Qt.MainWindow))
        Window = MainWindow

    elif issubclass(procedure, Procedure):
        from .windows.experiment_window import ExperimentWindow
        Window = ExperimentWindow
        kwargs.update(**instantiate(config.Qt.ExperimentWindow))
        kwargs['cls'] = procedure

    else:
        raise ValueError(f"Invalid procedure: {procedure}")

    window = Window(**kwargs)

    splash.finish(window)
    window.show()
    app.exec()
    remove_empty_data()


def _patch_taskbar_icon():
    """Patches the taskbar icon for Windows to show the application icon."""
    if sys.platform != 'win32':
        return

    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_app_id)
