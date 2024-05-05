import logging

from . import config
from laser_setup.procedures import *
from laser_setup.display import MetaProcedureWindow, display_window

log = logging.getLogger(__name__)


class MainSequence(MetaProcedure):
    """Manages a sequence of procedures. They can be edited
    in the procedures list. The procedures are executed in
    the order they are listed.
    """
    procedures = list(eval(config['Sequences']['MainSequence']))


if __name__ == '__main__':
    display_window(MetaProcedureWindow, MainSequence, 'Main Sequence')
