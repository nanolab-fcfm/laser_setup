import os
import sys
import logging
from IPython import embed
from pymeasure.adapters import FakeAdapter
from .. import config
from ..procedures import *
from ..utils import *
from ..display import *
from ..instruments import *

log = logging.getLogger(__name__)


def launch(workspace_path: str, header: str = '', user_ns: dict = None):
    if not os.path.exists(workspace_path):
        raise FileNotFoundError(f'Directory "{workspace_path}" not found.')

    os.chdir(workspace_path)

    embed(
        banner1='',
        banner2=header,
        colors='lightBG',
        user_ns=user_ns,
        )


def main(parent=None):
    header = "Interactive console. To instantiate an instrument, use the 'instruments.connect' method."
    if '-d' in sys.argv or '--debug' in sys.argv:
        header += "\nDebug mode (the InstrumentManager will use a FakeAdapter if it can't connect to an instrument)."
    workspace_path = os.path.abspath('.')

    instruments = InstrumentManager()

    if parent is not None:
        parent.lock_window('This will lock the current Window. To keep using it, close the console (Type `exit`)')

    launch(workspace_path, header=header, user_ns=globals() | locals())
    log.info('Console closed.')

    if parent is not None:
        parent.setEnabled(True)


if __name__ == "__main__":
    main()
