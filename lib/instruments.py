"""
Module that includes the classes for the instruments used in the experiments.
It also includes some base procedures that can be used to build more complex
procedures.
"""
import time
import numpy as np

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import truncated_range, strict_discrete_set

class TENMA(Instrument):
    """
    This class implements the communication with the TENMA sources. It is
    based on the pymeasure library. It is a subclass of the Instrument class
    from pymeasure.

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
        self.voltage = voltage

    def ramp_to_voltage(self, vg_end: float, vg_step=0.2, step_time=0.05):
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

    def shutdown(self):
        """
        Safely shutdowns the TENMA, setting the voltage to 0 and turning off
        the output.
        """
        self.ramp_to_voltage(0.)
        self.output = False
