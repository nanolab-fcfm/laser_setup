"""
Module that includes the K2450 class to communicate with the Keithleys,
as well as some functions that make voltage sequences for the Keithleys.
"""
import time
import numpy as np

from pymeasure.instruments.keithley import Keithley2450
from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import truncated_range, strict_discrete_set
from pymeasure.experiment import Procedure, FloatParameter, Parameter

from lib.utils import log, config, SONGS


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


class BasicIVgProcedure(Procedure):
    """
    Basic procedure for measuring current with a Keithley 2450 and two TENMA
    sources. Modify the `execute` method to run a specific
    :class:`pymeasure.experiment.Procedure`.

    :param chip: The chip name.
    :param sample: The sample name.
    :param comment: A comment to add to the data file.
    :param vds: The drain-source voltage in Volts.
    :param vg_start: The starting gate voltage in Volts.
    :param vg_end: The ending gate voltage in Volts.

    :ivar meter: The Keithley 2450 meter.
    :ivar negsource: The negative TENMA source.
    :ivar possource: The positive TENMA source.
    """
    #Device Parameters
    chip = Parameter('Chip', default='Unknown')
    sample = Parameter('Sample', default='Unknown')
    comment = Parameter('Comment', default='-')

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg_start = FloatParameter('VG start', units='V', default=-35.)
    vg_end = FloatParameter('VG end', units='V', default=35.)

    # Optional Parameters, preferably don't change
    Irange = FloatParameter('Irange', units='A', default=0.001)

    INPUTS = ['chip', 'sample', 'comment', 'vds', 'vg_start', 'vg_end', 'Irange']
    DATA_COLUMNS = ['Vg (V)', 'I (A)']

    def startup(self):
        log.info("Setting up instruments")
        self.meter = Keithley2450(config['Adapters']['Keithley2450'])
        self.negsource = TENMA(config['Adapters']['TenmaNeg'])
        self.possource = TENMA(config['Adapters']['TenmaPos'])

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.write(':TRACe:MAKE "IVBuffer", 100000')
        # self.meter.use_front_terminals()
        self.meter.apply_voltage(
            voltage_range=max(abs(self.vg_start), abs(self.vg_end)),
            compliance_current=self.Irange
            )
        self.meter.measure_current(current=self.Irange, auto_range=False)

        # TENMA sources
        self.negsource.apply_voltage(0.)
        self.possource.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.negsource.output = True
        time.sleep(1.)
        self.possource.output = True
        time.sleep(1.)

    def execute(self):
        pass

    def shutdown(self):
        if not hasattr(self, 'meter'):
            log.info("No instruments to shutdown.")
            return

        for freq, t in SONGS['ready']:
            self.meter.beep(freq, t)
            time.sleep(t)

        self.meter.shutdown()
        self.negsource.shutdown()
        self.possource.shutdown()
        log.info("Finished!")
