"""
This module contains the display functions for the GUI.
"""
import sys
import requests
from typing import Type

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import unique_filename, Results, Procedure
from PyQt6.QtCore import QLocale

from lib import config, log
from lib.utils import remove_empty_data

class MainWindow(ManagedWindow):
    """The main window for the GUI. It is used to display a
    `pymeasure.experiment.Procedure`, and allows for the experiment to be run
    from the GUI, by queuing it in the manager. It also allows for existing
    data to be loaded and displayed.
    """
    def __init__(self, cls: Type[Procedure], title: str = ''):
        self.cls = cls
        sequencer_kwargs = dict(
            sequencer = hasattr(cls, 'SEQUENCER_INPUTS'),
            sequencer_inputs = cls.SEQUENCER_INPUTS if hasattr(cls, 'SEQUENCER_INPUTS') else None,
            # sequence_file = f'sequences/{cls.SEQUENCER_INPUTS[0]}_sequence.txt' if hasattr(cls, 'SEQUENCER_INPUTS') else None,
        )
        super().__init__(
            procedure_class=cls,
            inputs=cls.INPUTS,
            displays=cls.INPUTS,
            x_axis=cls.DATA_COLUMNS[0],
            y_axis=cls.DATA_COLUMNS[1],
            inputs_in_scrollarea=True,
            **sequencer_kwargs,
        )
        self.setWindowTitle(title)

    def queue(self, procedure: Type[Procedure] = None):
        if procedure is None:
            procedure = self.make_procedure()

        directory = config['Filename']['directory']
        filename = unique_filename(
            directory,
            prefix=self.cls.__name__,
            dated_folder=True,
            )
        log.info(f"Saving data to {filename}.")
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


def display_experiment(cls: Type[Procedure], title: str = ''):
    """Displays the experiment for the given class. Allows for the
    experiment to be run from the GUI, by queuing it in the manager.
    It also allows for existing data to be loaded and displayed.
    """
    app = QtWidgets.QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    window = MainWindow(cls, title)
    window.show()
    app.exec()
    remove_empty_data()
    sys.exit()

def send_telegram_alert(message: str):
    """Sends a message to all valid Telegram chats on config['Telegram'].
    """
    if 'TOKEN' not in config['Telegram']:
        log.warning("Telegram token not specified in config.")
        return

    TOKEN = config['Telegram']['token']
    chats = [c for c in config['Telegram'] if c != 'token']

    if len(chats) == 0:
        log.warning("No chats specified in config.")
        return
    
    for chat in chats:
        chat_id = config['Telegram'][chat]
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url)
        log.info(f"Sent '{message}' to {chat}.")
