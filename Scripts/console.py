"""
This Script is used to debug a Keithley 2450.
"""
import os
import time
import logging
import numpy as np
from IPython import embed
from pymeasure.instruments.keithley import Keithley2450
from pymeasure.adapters import FakeAdapter
from lib import config
from lib.procedures import *
from lib.utils import *
from lib.display import *

log = logging.getLogger(__name__)


def launch(workspace_path: str, header: str = '', user_ns=None):
    if not os.path.exists(workspace_path):
        raise FileNotFoundError(f'Directory "{workspace_path}" not found.')

    os.chdir(workspace_path)

    embed(
        banner1='',
        banner2=header,
        colors='lightBG',
        user_ns=user_ns,
        )


def main():
    # workspace_path is one level above this script's directory
    header = "Debug console for Keithley 2450. Use the variable `K` to interact with the instrument."
    workspace_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    try:
        K = Keithley2450(config['Adapters']['keithley2450'])
    except:
        log.error(f"Keithley 2450 not found at {config['Adapters']['keithley2450']}. Using a FakeAdapter.")
        K = Keithley2450(FakeAdapter())

    launch(workspace_path, header=header, user_ns=locals())


if __name__ == "__main__":
    main()