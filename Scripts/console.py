"""
This Script is used to debug a Keithley 2450.
"""
import os
import logging
from IPython import embed
from pymeasure.adapters import FakeAdapter
from lib import config
from lib.procedures import *
from lib.utils import *
from lib.display import *
from lib.instruments import Keithley2450

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
    # workspace_path is one level above this script's directory
    header = "Debug console for Keithley 2450. Use the variable `K` to interact with the instrument."
    workspace_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    try:
        K = Keithley2450(config['Adapters']['keithley2450'])
    except:
        log.error(f"Keithley 2450 not found at {config['Adapters']['keithley2450']}. Using a FakeAdapter.")
        K = Keithley2450(FakeAdapter())

    if parent is not None:
        parent.lock_window('This will lock the current Window. To keep using it, close the console (Type `exit`)')

    launch(workspace_path, header=header, user_ns=globals() | locals())
    log.info('Console closed.')
    

def main():
    keithley_console(parent=None)


if __name__ == "__main__":
    main()