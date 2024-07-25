"""
Module that includes the classes for the instruments used in the experiments.
It also includes some base procedures that can be used to build more complex
procedures.
"""
import sys
import time
import logging
from typing import TypeVar, Type
import bendev.exceptions
import numpy as np

import bendev
from pymeasure.adapters import FakeAdapter
from pymeasure.instruments import Instrument
from pymeasure.instruments.keithley import Keithley2450
from pymeasure.instruments.thorlabs import ThorlabsPM100USB
from pymeasure.instruments.validators import truncated_range, strict_discrete_set

log = logging.getLogger(__name__)
AnyInstrument = TypeVar('AnyInstrument', bound=Instrument)


class TENMA(Instrument):
    """This class implements the communication with a TENMA instrument. It is
    a subclass of Pymeasure's Instrument class.
    """
    current = Instrument.control(
        "ISET1?", "ISET1:%.2f", """Sets the current in Amps.""",
        validator=truncated_range,
        values=[0, 1]
    )

    voltage = Instrument.control(
        "VSET1?", "VSET1:%.2f", """Sets the voltage in Volts.""",
        validator=truncated_range,
        values=[-60., 60.]
    )

    output = Instrument.control(
        "OUT1?", "OUT1:%d", """Sets the output state.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    )

    timeout = Instrument.control(
        "Timeout?", "Timeout %d", """Sets the timeout in seconds."""
    )

    def __init__(self, adapter: str, name: str = None, includeSCPI=False, **kwargs):
        """Initializes the TENMA power supply instrument.

        :param adapter: The adapter to use for the communication.
        :param name: The name of the instrument.
        :param includeSCPI: Whether to include the SCPI commands in the help.
        :param kwargs: Additional keyword arguments to pass to the Instrument class
        """
        super().__init__(
            adapter, name or "TENMA Power Supply", includeSCPI=includeSCPI, **kwargs
        )

    def ramp_to_voltage(self, vg_end: float, vg_step=0.1, step_time=0.05):
        """Sets the voltage to vg_end with a ramp in V/s.

        :param vg_end: The voltage to ramp to in Volts.
        :param vg_step: The step size in Volts.
        :param step_time: The time between steps in seconds.
        """
        v = self.voltage
        while abs(vg_end - v) > vg_step:
            v += np.sign(vg_end - v) * vg_step
            self.voltage = v
            time.sleep(step_time)
        self.voltage = vg_end

    def apply_voltage(self, voltage, current=0.05, timeout=1.):
        """
        Configures the TENMA to apply a source voltage, after setting the
        compliance current and timeout.

        :param voltage: The voltage to apply in Volts.
        :param current: The compliance current in Amps.
        :param timeout: The timeout in seconds.
        """
        self.timeout = timeout
        self.current = current
        time.sleep(0.1)
        self.ramp_to_voltage(voltage)

    def shutdown(self):
        """
        Safely shutdowns the TENMA, setting the voltage to 0 and turning off
        the output.
        """
        self.ramp_to_voltage(0.)
        self.output = False
        super().shutdown()


class Bentham(Instrument):
    """Communication with the Bentham (TLS120Xe) light source using
    the PyMeasure Instrument class. Replaces the adapter with a
    bendev.Device object for the communication.
    """
    wavelength = Instrument.control(
        ":MONO:WAVE?", ":MONO:WAVE %.1f",
        """Sets the wavelength in nm. Gets the current and target wavelengths in nm.""",
        validator=truncated_range,
        values=[280., 1100.]
    )

    bandwidth = Instrument.measurement(
        ":BAND?", """Reads the bandwidth of the current wavelength in nm."""
    )

    move = Instrument.measurement(
        ":MONO:MOVE?", """Moves the monochromator to the specified wavelength."""
    )

    at_target = Instrument.measurement(
        ":OUTP:ATT?", """Checks if the monochromator is at the target wavelength."""
    )

    output = Instrument.control(
        ":OUTP?", ":OUTP %d", """Sets the output state.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    )

    lamp = Instrument.control(
        ":LAMP?", ":LAMP %d", """Sets the lamp state.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    )

    source_current = Instrument.control(
        ":SOUR:CURR?", ":SOUR:CURR %.2f", """Sets the source current in Amps.""",
        validator=truncated_range,
        values=[0., 7.2]
    )

    source_voltage = Instrument.control(
        ":SOUR:VOLT?", ":SOUR:VOLT %.2f", """Sets the source voltage in Volts.""",
        validator=truncated_range,
        values=[0., 15.]
    )

    current = Instrument.measurement(":CURR?", """Reads the current in Amps.""")

    photocurrent = Instrument.measurement(":PD?", """Reads the photocurrent in Amps.""")

    voltage = Instrument.measurement(":VOLT?", """Reads the voltage in Volts.""")

    power = Instrument.measurement(":POW?", """Reads the power in Watts.""")

    resistance = Instrument.measurement(":RES?", """Reads the resistance in Ohms.""")

    def __init__(self, adapter: str = None, name: str = None, includeSCPI=False, **kwargs):
        """Initializes the Bentham light source instrument.

        :param adapter: The adapter to use for the communication. If the adapter
            is a string or None, it replaces it with a bendev.Device object.
            Other instruments can use a self.adapter = None. However, this
            class will first try to connect to an available USB device.
        :param name: The name of the instrument.
        :param includeSCPI: Whether to include the SCPI commands in the help.
        :param kwargs: Additional keyword arguments to pass to the Instrument class.
        """
        temp_adapter = None if isinstance(adapter, str) else adapter
        super().__init__(
            temp_adapter,
            name or "Bentham TLS120Xe",
            includeSCPI=includeSCPI, **kwargs
        )

        if isinstance(adapter, str) or adapter is None:
            try:
                self.adapter = bendev.Device(adapter)

            except bendev.exceptions.ExternalDeviceNotFound:
                if adapter is not None:
                    raise

    def query(self, command, timeout: int = 0, read_interval: float = 0.05) -> str:
        return self.adapter.query(command, timeout, read_interval)

    def shutdown(self):
        self.adapter.close()
        super().shutdown()

    def reconnect(self):
        self.adapter.reconnect()


def setup_adapter(cls: Type[AnyInstrument], adapter: str, **kwargs) -> AnyInstrument:
    """Sets up the adapter for the given instrument class. If the setup fails,
    it raises an exception, unless debug mode is enabled (-d flag), in which
    case it replaces the adapter with a pymeasure.

    :param cls: The instrument class to set up.
    :param adapter: The adapter to use for the communication.
    :param kwargs: Additional keyword arguments to pass to the instrument class.
    :return: The instrument object.
    """
    try:
        instrument = cls(adapter, **kwargs)
    except Exception as e:
        if '-d' in sys.argv:
            log.warning(f"Could not connect to {cls.__name__}: {e}.\nUsing FakeAdapter")
            instrument = cls(FakeAdapter(), **kwargs)
        else:
            log.error(f"Could not connect to {cls.__name__}")
            raise
    return instrument
