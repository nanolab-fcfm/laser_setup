import time
from typing import Literal

from pymeasure.instruments.keithley import Keithley2450
from pymeasure.experiment import Procedure, FloatParameter, IntegerParameter, Parameter

from lib import config, log
from .utils import SONGS
from .display import send_telegram_alert
from .instruments import TENMA


class BaseProcedure(Procedure):
    """WIP: Base class for all procedures. It contains the basic parameters
    that all procedures should have.
    Basic procedure for measuring with a Keithley 2450 and any amount of TENMA
    sources.
    
    Modify the `execute` method to run a specific
    :class:`pymeasure.experiment.Procedure`. To add more parameters to the
    Procedure, or modify the existent ones, define a new
    `pymeasure.experiment.Parameter` as class attribute, and add it to INPUTS:
    `INPUTS = BaseProcedure.INPUTS + [parameter_name]`

    To add data columns, modify DATA_COLUMNS:
    `DATA_COLUMNS = BaseProcedure.DATA_COLUMNS + [column_name]`

    :param chip: The chip name.
    :param sample: The sample name.
    :param info: A comment to add to the data file.
    :param vds: The drain-source voltage in Volts.
    :param vg_start: The starting gate voltage in Volts.
    :param vg_end: The ending gate voltage in Volts.
    :param Irange: The current range in Ampere.

    :ivar meter: The Keithley 2450 meter.
    """
    #Device Parameters
    chip = Parameter('Chip', default='None')            # There must be a default value, otherwise it can't be read from the data file
    sample = Parameter('Sample', default='None')
    info = Parameter('Information', default='None')

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg_start = FloatParameter('VG start', units='V', default=-10.)
    vg_end = FloatParameter('VG end', units='V', default=10.)

    # Optional Parameters, preferably don't change
    Irange = FloatParameter('I range', units='A', default=1e-6)
    N_avg = IntegerParameter('N_avg', default=2)

    INPUTS = ['chip', 'sample', 'info', 'vds', 'vg_start', 'vg_end', 'N_avg']
    DATA_COLUMNS = ['Vg (V)', 'I (A)']
    TENMA_LIST: list[Literal['tenma_pos', 'tenma_neg', 'tenma_laser']] = ['tenma_pos', 'tenma_neg']

    def startup(self):
        """Initialize the Keithley 2450 and the TENMA sources."""
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
            for tenma in self.TENMA_LIST:
                setattr(self, tenma, TENMA(config['Adapters'][tenma]))
        except ValueError:
            log.error("Could not connect to instruments")
            raise

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
        for tenma in self.TENMA_LIST:
            getattr(self, tenma).apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        for tenma in self.TENMA_LIST:
            getattr(self, tenma).output = True

    def execute(self):
        """Placeholder for the actual procedure."""
        pass

    def shutdown(self):
        if not hasattr(self, 'meter'):
            log.info("No instruments to shutdown.")
            return

        for freq, t in SONGS['triad']:
            self.meter.beep(freq, t)
            time.sleep(t)

        self.meter.shutdown()
        for tenma in self.TENMA_LIST:
            getattr(self, tenma).shutdown()
        log.info("Instruments shutdown.")

        send_telegram_alert(
            f"Finished It measurement for Chip {self.chip}, Sample {self.sample}!"
        )


class IVgBaseProcedure(Procedure):
    """
    Basic procedure for measuring current over gate voltage with a Keithley
    2450 and two TENMA sources.
    
    Modify the `execute` method to run a specific
    :class:`pymeasure.experiment.Procedure`. To add more parameters to the
    Procedure, or modify the existent ones, define a new
    `pymeasure.experiment.Parameter` as class attribute, and add it to INPUTS:
    `INPUTS = BasicIVgProcedure.INPUTS + [parameter_name]`

    To add data columns, modify DATA_COLUMNS:
    `DATA_COLUMNS = BasicIVgProcedure.DATA_COLUMNS + [column_name]`

    :param chip: The chip name.
    :param sample: The sample name.
    :param info: A comment to add to the data file.
    :param vds: The drain-source voltage in Volts.
    :param vg_start: The starting gate voltage in Volts.
    :param vg_end: The ending gate voltage in Volts.
    :param N_avg: The number of measurements to average.
    :param vg_step: The step size of the gate voltage.
    :param step_time: The time to wait between measurements.
    :param Irange: The current range in Ampere.

    :ivar meter: The Keithley 2450 meter.
    :ivar negsource: The negative TENMA source.
    :ivar possource: The positive TENMA source.
    """
    #Device Parameters
    chip = Parameter('Chip', default='None')            # There must be a default value, otherwise it can't be read from the data file
    sample = Parameter('Sample', default='None')
    info = Parameter('Information', default='None')

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg_start = FloatParameter('VG start', units='V', default=-35.)
    vg_end = FloatParameter('VG end', units='V', default=35.)

    # Optional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2)
    vg_step = FloatParameter('VG step', units='V', default=0.2)
    step_time = FloatParameter('Step time', units='s', default=0.01)
    Irange = FloatParameter('Irange', units='A', default=0.001)

    INPUTS = ['chip', 'sample', 'info', 'vds', 'vg_start', 'vg_end', 'N_avg', 'vg_step', 'step_time']
    DATA_COLUMNS = ['Vg (V)', 'I (A)']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
            self.negsource = TENMA(config['Adapters']['tenma_neg'])
            self.possource = TENMA(config['Adapters']['tenma_pos'])
        except ValueError:
            log.error("Could not connect to instruments")
            raise

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
        """Placeholder for the execution of the procedure."""
        pass

    def shutdown(self):
        if not hasattr(self, 'meter'):
            log.info("No instruments to shutdown.")
            return

        for freq, t in SONGS['triad']:
            self.meter.beep(freq, t)
            time.sleep(t)

        self.meter.shutdown()
        self.negsource.shutdown()
        self.possource.shutdown()
        log.info("Instruments shutdown.")

        send_telegram_alert(
            f"Finished It measurement for Chip {self.chip}, Sample {self.sample}!"
        )


class ItBaseProcedure(Procedure):
    """
    Basic procedure for measuring current over time with a Keithley 2450 and
    two TENMA sources.
    
    Modify the `execute` method to run a specific
    :class:`pymeasure.experiment.Procedure`. To add more parameters to the
    Procedure, or modify the existent ones, define a new
    `pymeasure.experiment.Parameter` as class attribute, and add it to INPUTS:
    `INPUTS = BasicItProcedure.INPUTS + [parameter_name]`

    To add data columns, modify DATA_COLUMNS:
    `DATA_COLUMNS = BasicItProcedure.DATA_COLUMNS + [column_name]`

    :param chip: The chip name.
    :param sample: The sample name.
    :param info: A comment to add to the data file.
    :param laser_freq: The laser frequency in Hz.
    :param laser_T: The laser ON+OFF period in seconds.
    :param laser_v: The laser voltage in Volts.
    :param vds: The drain-source voltage in Volts.
    :param vg: The gate voltage in Volts.
    :param Irange: The current range in Ampere.

    :ivar meter: The Keithley 2450 meter.
    :ivar negsource: The negative TENMA source.
    :ivar possource: The positive TENMA source.
    """
    # Device Parameters
    chip = Parameter('Chip', default='None')
    sample = Parameter('Sample', default='None')
    info = Parameter('Information', default='None')

    # Important Parameters
    laser_freq = FloatParameter('Laser frequency', units='Hz', default=0.)
    laser_T = FloatParameter('Laser ON+OFF period', units='s', default=360.)
    laser_v = FloatParameter('Laser voltage', units='V', default=0.)
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg = FloatParameter('VG', units='V', default=0.)
    sampling_t = FloatParameter('Sampling time', units='s', default=0.5)

    # Optional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2)
    Irange = FloatParameter('Irange', units='A', default=0.001)

    INPUTS = ['chip', 'sample', 'info', 'laser_freq', 'laser_T', 'laser_v', 'vds', 'vg', 'sampling_t', 'N_avg']
    DATA_COLUMNS = ['t (s)', 'I (A)']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
            self.negsource = TENMA(config['Adapters']['tenma_neg'])
            self.possource = TENMA(config['Adapters']['tenma_pos'])
            self.lasersource = TENMA(config['Adapters']['tenma_laser'])
        except ValueError:
            log.error("Could not connect to instruments")
            raise

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.write(':TRACe:MAKE "IVBuffer", 100000')
        # self.meter.use_front_terminals()
        self.meter.apply_voltage(
            voltage_range=1e-1,
            compliance_current=self.Irange
            )
        self.meter.measure_current(current=self.Irange, auto_range=False)

        # TENMA sources
        self.negsource.apply_voltage(0.)
        self.possource.apply_voltage(0.)
        self.lasersource.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.negsource.output = True
        time.sleep(1.)
        self.possource.output = True
        time.sleep(1.)
        self.lasersource.output = True
        time.sleep(1.)

    def execute(self):
        """Placeholder for the execution of the procedure."""
        pass

    def shutdown(self):
        if not hasattr(self, 'meter'):
            log.info("No instruments to shutdown.")
            return

        for freq, t in SONGS['triad']:
            self.meter.beep(freq, t)
            time.sleep(t)

        self.meter.shutdown()
        self.negsource.shutdown()
        self.possource.shutdown()
        self.lasersource.shutdown()
        log.info("Instruments shutdown.")

        send_telegram_alert(
            f"Finished It measurement for Chip {self.chip}, Sample {self.sample}!"
        )
