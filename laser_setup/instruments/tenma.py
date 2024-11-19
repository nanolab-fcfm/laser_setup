import time
import logging
import numpy as np

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import truncated_range, strict_discrete_set

log = logging.getLogger(__name__)


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
