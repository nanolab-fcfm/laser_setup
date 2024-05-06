import logging

from laser_setup.procedures import *
from laser_setup.display import MetaProcedureWindow, display_window

log = logging.getLogger(__name__)


if __name__ == '__main__':
    display_window(MetaProcedureWindow, MainSequence, 'Main Sequence')
