"""Module that includes the instruments used in the experiments.
"""
from pymeasure.adapters import FakeAdapter
from pymeasure.instruments import Instrument
from pymeasure.instruments.thorlabs import ThorlabsPM100USB

from .instrument_manager import InstrumentManager, PendingInstrument
from .bentham import Bentham
from .keithley import Keithley2450, Keithley6517B
from .serial import PT100SerialSensor
from .tenma import TENMA

Instruments: list[type[Instrument]] = [
    Instrument,
    Keithley2450,
    Keithley6517B,
    PT100SerialSensor,
    TENMA,
    Bentham,
    ThorlabsPM100USB
]
