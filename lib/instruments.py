"""
Module that includes the classes for the instruments used in the experiments.
It also includes some base procedures that can be used to build more complex
procedures.
"""
import time
import numpy as np

from pymeasure.instruments import Instrument
from pymeasure.instruments.keithley import Keithley2450
from pymeasure.instruments.thorlabs import ThorlabsPM100USB
from pymeasure.instruments.validators import truncated_range, strict_discrete_set


class TENMA(Instrument):
    """
    This class implements the communication with the TENMA sources. It is
    a subclass of Pymeasure's Instrument class.

    :param adapter: The adapter to use for the communication.
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
    
    def __init__(self, adapter: str, **kwargs):
        super(TENMA, self).__init__(
            adapter, "TENMA Power Supply", **kwargs
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


class TLS120Xe(Instrument):
    """Communication with the Bentham TLS120-Xe light source. 
    """
    wavelength = Instrument.control(
        ":MONO:WAVE?", ":MONO:WAVE %.1f",
        """Sets the wavelength in nm. Gets the current and target wavelengths in nm.""",
        validator=truncated_range,
        values=[280., 1100.]
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
        values=[0., 5.]
    )
    
    source_voltage = Instrument.control(
        ":SOUR:VOLT?", ":SOUR:VOLT %.2f", """Sets the source voltage in Volts.""",
        validator=truncated_range,
        values=[0., 20.]
    )

    current = Instrument.measurement(
        ":CURR?", """Reads the current in Amps.""")
    
    voltage = Instrument.measurement(":VOLT?", """Reads the voltage in Volts.""")
    
    power = Instrument.measurement(":POW?", """Reads the power in Watts.""")
    
    resistance = Instrument.measurement(":RES?", """Reads the resistance in Ohms.""")
