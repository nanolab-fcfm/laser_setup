import time

from pymeasure.instruments.keithley import Keithley2450
from pymeasure.experiment import Procedure, FloatParameter, IntegerParameter, Parameter, BooleanParameter, ListParameter

from lib import config, log
from .utils import SONGS
from .display import send_telegram_alert
from .instruments import TENMA


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
    :ivar tenma_neg: The negative TENMA source.
    :ivar tenma_pos: The positive TENMA source.
    """
    #Device Parameters
    chip = ListParameter('Chip', choices=['Margarita', 'Miguel', 'Pepe (no ALD)'])
    chip_number = IntegerParameter('Chip number', default=1)
    sample = ListParameter('Sample', choices=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'])
    info = Parameter('Information', default='None')

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg_start = FloatParameter('VG start', units='V', default=-35.)
    vg_end = FloatParameter('VG end', units='V', default=35.)

    # Laser Parameters
    laser_toggle = BooleanParameter('Laser toggle', default=False)
    laser_wl = FloatParameter('Laser wavelength', units='nm', default=0., group_by='laser_toggle')
    laser_v = FloatParameter('Laser voltage', units='V', default=0., group_by='laser_toggle')
    
    # Optional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2)
    vg_step = FloatParameter('VG step', units='V', default=0.2)
    step_time = FloatParameter('Step time', units='s', default=0.01)
    Irange = FloatParameter('Irange', units='A', default=0.001)

    INPUTS = ['chip', 'chip_number', 'sample', 'info', 'vds', 'vg_start', 'vg_end', 'N_avg', 'vg_step', 'step_time', 'laser_toggle', 'laser_wl', 'laser_v']
    DATA_COLUMNS = ['Vg (V)', 'I (A)']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
            self.tenma_neg = TENMA(config['Adapters']['tenma_neg'])
            self.tenma_pos = TENMA(config['Adapters']['tenma_pos'])
            if self.laser_toggle:
                self.tenma_laser = TENMA(config['Adapters']['tenma_laser'])
        except ValueError:
            log.error("Could not connect to instruments")
            raise

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.write(':TRACe:MAKE "IVBuffer", 100000')
        # self.meter.use_front_terminals()
        self.meter.measure_current(current=self.Irange, auto_range=False)

        # TENMA sources
        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)
        if self.laser_toggle:
            self.tenma_laser.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        if self.laser_toggle:
            self.tenma_laser.output = True
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
        self.tenma_neg.shutdown()
        self.tenma_pos.shutdown()
        if self.laser_toggle:
            self.tenma_laser.shutdown()
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
    :ivar tenma_neg: The negative TENMA source.
    :ivar tenma_pos: The positive TENMA source.
    :ivar tenma_laser: The laser TENMA source.
    """
    #Device Parameters
    chip = ListParameter('Chip', choices=['Margarita', 'Miguel', 'Pepe (no ALD)'])
    chip_number = IntegerParameter('Chip number', default=1)
    sample = ListParameter('Sample', choices=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'])
    info = Parameter('Information', default='None')

    # Important Parameters
    laser_wl = FloatParameter('Laser wavelength', units='nm', default=0.)
    laser_T = FloatParameter('Laser ON+OFF period', units='s', default=360.)
    laser_v = FloatParameter('Laser voltage', units='V', default=0.)
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg = FloatParameter('VG', units='V', default=0.)

    # Optional Parameters, preferably don't change
    sampling_t = FloatParameter('Sampling time (excluding Keithley)', units='s', default=0.)
    N_avg = IntegerParameter('N_avg', default=2)
    Irange = FloatParameter('Irange', units='A', default=0.001)

    INPUTS = ['chip', 'sample', 'info', 'laser_wl', 'laser_T', 'laser_v', 'vds', 'vg', 'sampling_t', 'N_avg']
    DATA_COLUMNS = ['t (s)', 'I (A)', 'VL (V)']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
            self.tenma_neg = TENMA(config['Adapters']['tenma_neg'])
            self.tenma_pos = TENMA(config['Adapters']['tenma_pos'])
            self.tenma_laser = TENMA(config['Adapters']['tenma_laser'])
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
        self.tenma_neg.apply_voltage(0.)
        self.tenma_pos.apply_voltage(0.)
        self.tenma_laser.apply_voltage(0.)

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        time.sleep(1.)
        self.tenma_pos.output = True
        time.sleep(1.)
        self.tenma_laser.output = True
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
        self.tenma_neg.shutdown()
        self.tenma_pos.shutdown()
        self.tenma_laser.shutdown()
        log.info("Instruments shutdown.")

        send_telegram_alert(
            f"Finished It measurement for Chip {self.chip}, Sample {self.sample}!"
        )
