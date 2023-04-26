"""
This Script is used to measure the time-dependent current of the device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
TODO: add Laser functionality
"""
import logging
import configparser
import sys
import time
from lib.devices import TENMA, vg_ramp, SONGS

import numpy as np
from pymeasure.instruments.keithley import Keithley2450
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import (
    Procedure, FloatParameter, IntegerParameter, unique_filename, Results, Parameter
)

config = configparser.ConfigParser()
config.read('config.ini')

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class It():
    pass