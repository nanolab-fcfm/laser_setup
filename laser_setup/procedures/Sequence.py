from .. import config
from ..procedures import *


class MetaProcedure(BaseProcedure):
    """Manages a multiple procedures to be executed in sequence. It is used to
    run a sequence of procedures, such as a burn-in followed by an IVg and
    It measurements. Performs a unique startup, executes the procedures in
    sequence, and performs a unique shutdown.
    """
    procedures: list[BaseProcedure] = []


class MainSequence(MetaProcedure):
    """Manages a sequence of procedures. They can be edited
    in the procedures list. The procedures are executed in
    the order they are listed.
    """
    procedures = list(eval(config['Sequences']['MainSequence']))
