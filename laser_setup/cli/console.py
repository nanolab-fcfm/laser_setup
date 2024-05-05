import os
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


def keithley_console(parent=None):
    header = "Debug console for Keithley 2450. Use the variable `K` to interact with the instrument."
    workspace_path = os.path.abspath('.')

    if parent is not None:
        parent.lock_window('This will lock the current Window. To keep using it, close the console (Type `exit`)')

    try:
        K = Keithley2450(config['Adapters']['keithley2450'])
    except:
        log.error(f"Keithley 2450 not found at {config['Adapters']['keithley2450']}. Using a FakeAdapter.")
        K = Keithley2450(FakeAdapter())

    launch(workspace_path, header=header, user_ns=globals() | locals())
    log.info('Console closed.')

    if parent is not None:
        parent.setEnabled(True)


def main():
    keithley_console(parent=None)


if __name__ == "__main__":
    main()
