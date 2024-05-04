import logging

from .IVg import IVg
from .It import It
from laser_setup.procedures import MetaProcedure, Wait, FakeProcedure
from laser_setup.display import MetaProcedureWindow, display_window

log = logging.getLogger(__name__)


class MainSequence(MetaProcedure):
    """Manages a sequence of procedures. They can be edited
    in the procedures list. The procedures are executed in
    the order they are listed.
    """
    procedures = [
        IVg,
        It,
        IVg,
        Wait,
        IVg,
    ]
    parameter_list = []

if __name__ == '__main__':
    display_window(MetaProcedureWindow, MainSequence, 'Main Sequence')
