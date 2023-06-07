"""
This module contains the display functions for the GUI.
"""
import sys
import requests
from typing import Type

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import unique_filename, Results, Procedure

from .utils import config

class MainWindow(ManagedWindow):
    """The main window for the GUI. It is used to display a
    `BasicIVgProcedure`, and allows for the experiment to be run from the GUI,
    by queuing it in the manager. It also allows for existing data to be loaded
    and displayed.
    """
    def __init__(self, cls: Type[Procedure], title: str = ''):
        self.cls = cls
        super().__init__(
            procedure_class=cls,
            inputs=cls.INPUTS,
            displays=cls.INPUTS,
            x_axis=cls.DATA_COLUMNS[0],
            y_axis=cls.DATA_COLUMNS[1],
        )
        self.setWindowTitle(title)

    def queue(self):
        directory = config['Dir']['DataDir']
        filename = unique_filename(
            directory,
            prefix=self.cls.__name__,
            dated_folder=True,
            )
        procedure = self.make_procedure()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


def display_experiment(cls: Type[Procedure], title: str = ''):
    """Displays the experiment for the given class. Allows for the
    experiment to be run from the GUI, by queuing it in the manager.
    It also allows for existing data to be loaded and displayed.
    """
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(cls, title)
    window.show()
    sys.exit(app.exec())

def send_telegram_alert(chat: str, procedure: Type[Procedure] = Procedure):
    """Sends a message to the specified telegram chat, alerting the user
    that the experiment has finished.
    """
    CHATS = {
    "Benja": "735989705",
    }

    chat_id = CHATS[chat]
    TOKEN = "6127232691:AAG62NWTpFwJ-MXLdh9SunoQy9crJKinePA"
    message = f"Your experiment ({procedure.__name__}) has finished!"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url)
