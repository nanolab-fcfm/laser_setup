import time
import logging

from pymeasure.experiment import Procedure, FloatParameter, IntegerParameter, Parameter, BooleanParameter, ListParameter, Metadata

from lib import config
from .utils import SONGS, send_telegram_alert, get_latest_DP
from .instruments import TENMA, Keithley2450, ThorlabsPM100USB

log = logging.getLogger(__name__)


class BaseProcedure(Procedure):
    """Base procedure for all device-related measurements. It defines the basic
    parameters that are common to all the measurements, such as chip
    parameters.
    """
    # Procedure version. When modified, increment
    # <parameter name>.<parameter property>.<procedure startup/shutdown>
    procedure_version = Parameter('Procedure version', default='1.4.0')

    # config 
    chip_names = list(eval(config['Chip']['names'])) + ['other']
    samples = list(eval(config['Chip']['samples']))

    # Chip Parameters
    show_more = BooleanParameter('Show more', default=False)
    chip_group = ListParameter('Chip group name', choices=chip_names)
    chip_number = IntegerParameter('Chip number', default=1, minimum=1)
    sample = ListParameter('Sample', choices=samples)
    info = Parameter('Information', default='None')

    # Metadata
    start_time = Metadata('Start time', fget=time.time)

    INPUTS = ['show_more', 'chip_group', 'chip_number', 'sample', 'info']
    
    def update_parameters(self):
        """Function to update the parameters after the initialization,
        but before startup. It is useful to modify the parameters
        based on the values of other parameters. It is called
        only by the ExperimentWindow.
        """
        pass

class FakeProcedure(BaseProcedure):
    """A fake procedure for testing purposes."""
    fake_parameter = FloatParameter('Fake parameter', units='V', default=1.0)
    total_time = FloatParameter('Total time', units='s', default=30.)
    INPUTS = BaseProcedure.INPUTS + ['total_time', 'fake_parameter']
    DATA_COLUMNS = ['t (s)', 'fake_data']
    def execute(self):
        log.info("Executing fake procedure.")
        t0 = time.time()
        tc = t0
        while tc - t0 < self.total_time:
            if self.should_stop():
                log.error('Measurement aborted')
                break

            self.emit('progress', (tc - t0)/self.total_time*100)
            data = self.fake_parameter + hash(tc-t0) % 1000 / 1000
            self.emit('results', dict(zip(self.DATA_COLUMNS, [tc - t0, data])))
            time.sleep(0.2)
            tc = time.time()
            
    def get_estimates(self):
        estimates = [
            ('Fake Estimate', f"{self.fake_parameter + hash(time.time()) % 1000 / 1000:.2f}")
        ]
        return estimates


class Wait(BaseProcedure):
    """Literally just waits for a specified amount of time."""
    wait_time = FloatParameter('Wait time', units='s', default=1.)
    INPUTS = BaseProcedure.INPUTS + ['wait_time']
    def execute(self):
        log.info(f"Waiting for {self.wait_time} seconds.")
        t0 = time.time()
        tc = t0
        while tc - t0 < self.wait_time:
            self.emit('progress', (tc - t0)/self.wait_time*100)
            tc = time.time()


class MetaProcedure(BaseProcedure):
    """Manages a multiple procedures to be executed in sequence. It is used to
    run a sequence of procedures, such as a burn-in followed by an IVg and
    It measurements. Performs a unique startup, executes the procedures in
    sequence, and performs a unique shutdown.
    """
    procedures: list[BaseProcedure] = []


class IVgBaseProcedure(BaseProcedure):
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

    :param chip_group: The chip group name.
    :param chip_number: The chip number.
    :param sample: The sample name.
    :param info: A comment to add to the data file.
    :param vds: The drain-source voltage in Volts.
    :param vg_start: The starting gate voltage in Volts.
    :param vg_end: The ending gate voltage in Volts.
    :laser_toggle: Whether to turn on the laser
    :laser_wl: The laser wavelength in nm.
    :laser_v: The laser voltage in Volts.
    :param N_avg: The number of measurements to average.
    :param vg_step: The step size of the gate voltage.
    :param step_time: The time to wait between measurements.
    :param Irange: The current range in Ampere.

    :ivar meter: The Keithley 2450 meter.
    :ivar tenma_neg: The negative TENMA source.
    :ivar tenma_pos: The positive TENMA source.
    """
    wavelengths = list(eval(config['Laser']['wavelengths']))

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg_start = FloatParameter('VG start', units='V', default=-35.)
    vg_end = FloatParameter('VG end', units='V', default=35.)

    # Laser Parameters
    laser_toggle = BooleanParameter('Laser toggle', default=False)
    laser_wl = ListParameter('Laser wavelength', units='nm', choices=wavelengths, group_by='laser_toggle')
    laser_v = FloatParameter('Laser voltage', units='V', default=0., group_by='laser_toggle')
    burn_in_t = FloatParameter('Burn-in time', units='s', default=60., group_by='laser_toggle')

    # Additional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2, group_by='show_more')
    vg_step = FloatParameter('VG step', units='V', default=0.2, group_by='show_more')
    step_time = FloatParameter('Step time', units='s', default=0.01, group_by='show_more')
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')

    INPUTS = BaseProcedure.INPUTS + ['vds', 'vg_start', 'vg_end', 'vg_step', 'step_time', 'N_avg', 'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'Irange']
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
        self.meter.measure_current(current=self.Irange, auto_range=not bool(self.Irange))

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
            f"Finished IVg measurement for Chip {self.chip_group} {self.chip_number}, Sample {self.sample}!"
        )


class ItBaseProcedure(BaseProcedure):
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

    :param chip_group: The chip group name.
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
    wavelengths = list(eval(config['Laser']['wavelengths']))

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075, decimals=10)
    #vg = FloatParameter('VG', units='V', default=0.)
    vg = Parameter('VG', default='DP + 0. V')
    laser_wl = ListParameter('Laser wavelength', units='nm', choices=wavelengths)
    laser_v = FloatParameter('Laser voltage', units='V', default=0.)
    laser_T = FloatParameter('Laser ON+OFF period', units='s', default=120.)

    # Additional Parameters, preferably don't change
    sampling_t = FloatParameter('Sampling time (excluding Keithley)', units='s', default=0., group_by='show_more')
    N_avg = IntegerParameter('N_avg', default=2, group_by='show_more')
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')

    INPUTS = BaseProcedure.INPUTS + ['vds', 'vg', 'laser_wl', 'laser_v', 'laser_T', 'sampling_t', 'N_avg', 'Irange']
    DATA_COLUMNS = ['t (s)', 'I (A)', 'VL (V)']
    
    def update_parameters(self):
        vg = str(self.vg)
        assert vg.endswith(' V'), "Gate voltage must be in Volts"
        vg = vg[:-2].replace('DP', f"{get_latest_DP(self.chip_group, self.chip_number, self.sample, max_files=3):.2f}")
        float_vg = float(eval(vg))
        assert -100 <= float_vg <= 100, "Gate voltage must be between -100 and 100 V"
        self.vg = float_vg
        self._parameters['vg'] = FloatParameter('VG', units='V', default=float_vg)
        self.refresh_parameters()

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
        self.meter.measure_current(current=self.Irange, auto_range=not bool(self.Irange))

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
            f"Finished It measurement for Chip {self.chip_group} {self.chip_number}, Sample {self.sample}!"
        )


class PtBaseProcedure(Procedure):
    """
    Basic procedure for measuring power over time with a thorlabs Powermeter and
    one TENMA Power Supply.
    
    Modify the `execute` method to run a specific
    :class:`pymeasure.experiment.Procedure`. To add more parameters to the
    Procedure, or modify the existent ones, define a new
    `pymeasure.experiment.Parameter` as class attribute, and add it to INPUTS:
    `INPUTS = BasicPtProcedure.INPUTS + [parameter_name]`

    To add data columns, modify DATA_COLUMNS:
    `DATA_COLUMNS = BasicPtProcedure.DATA_COLUMNS + [column_name]`

    :param info: A comment to add to the data file.
    :param laser_wl: The laser wavelength in nm.
    :param laser_T: The laser ON+OFF period in seconds.
    :param laser_v: The laser voltage in Volts.
    :param Irange: The current range in Ampere.

    :ivar tenma_laser: The laser TENMA source.
    """

    procedure_version = Parameter('Procedure version', default='0.1.1')
    
    wavelengths = list(eval(config['Laser']['wavelengths']))
    fibers = list(eval(config['Laser']['fibers']))

    # config
    show_more = BooleanParameter('Show more', default=False)
    info = Parameter('Information', default='None')

    # Metadata
    start_time = Metadata('Start time', fget=time.time)

    # Important Parameter
    laser_wl  = ListParameter('Laser wavelength', units='nm', choices=wavelengths)
    fiber     = ListParameter('Optical fiber', choices=fibers)
    laser_v   = FloatParameter('Laser voltage', units='V', default=0.)
    N_avg     = IntegerParameter('N_avg', default=2)
    laser_T   = FloatParameter('Laser ON+OFF period', units='s', default=20.)

    # Metadata
    sensor    = Metadata('Sensor model', fget='power_meter.sensor_name')

    # Additional Parameters, preferably don't change
    sampling_t = FloatParameter('Sampling time (excluding Keithley)', units='s', default=0., group_by='show_more')
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')
    INPUTS = ['show_more', 'info', 'laser_wl', 'fiber', 'laser_v', 'laser_T', 'N_avg', 'sampling_t', 'Irange']
    DATA_COLUMNS = ['t (s)', 'P (W)', 'VL (V)']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.power_meter = ThorlabsPM100USB(config['Adapters']['power_meter'])
            self.tenma_laser = TENMA(config['Adapters']['tenma_laser'])
        except ValueError:
            log.error("Could not connect to instruments")
            raise

        # TENMA sources
        self.tenma_laser.apply_voltage(0.)

        self.tenma_laser.output = True
        time.sleep(1.)
        self.power_meter.wavelength = self.laser_wl


    def execute(self):
        """Placeholder for the execution of the procedure."""
        pass

    def shutdown(self):
        if not hasattr(self, 'power_meter'):
            log.info("No instruments to shutdown.")
            return
        
        self.tenma_laser.shutdown()
        log.info("Instruments shutdown.")


class IVBaseProcedure(BaseProcedure):
    """
    Basic procedure for measuring current over source drain voltage with a Keithley
    2450 and two TENMA sources.
    
    Modify the `execute` method to run a specific
    :class:`pymeasure.experiment.Procedure`. To add more parameters to the
    Procedure, or modify the existent ones, define a new
    `pymeasure.experiment.Parameter` as class attribute, and add it to INPUTS:
    `INPUTS = BasicIVgProcedure.INPUTS + [parameter_name]`

    To add data columns, modify DATA_COLUMNS:
    `DATA_COLUMNS = BasicIVgProcedure.DATA_COLUMNS + [column_name]`

    :param chip_group: The chip group name.
    :param chip_number: The chip number.
    :param sample: The sample name.
    :param info: A comment to add to the data file.
    :param vds: The drain-source voltage in Volts.
    :param vsd_start: The starting source drain voltage in Volts.
    :param vsd_end: The ending source drain voltage in Volts.
    :laser_toggle: Whether to turn on the laser
    :laser_wl: The laser wavelength in nm.
    :laser_v: The laser voltage in Volts.
    :param N_avg: The number of measurements to average.
    :param vsd_step: The step size of the source drain voltage.
    :param step_time: The time to wait between measurements.
    :param Irange: The current range in Ampere.

    :ivar meter: The Keithley 2450 meter.
    :ivar tenma_neg: The negative TENMA source.
    :ivar tenma_pos: The positive TENMA source.
    """
    wavelengths = list(eval(config['Laser']['wavelengths']))

    # Important Parameters
    vg = FloatParameter('VG', units='V', default=0.0)
    vsd_start = FloatParameter('VSD start', units='V', default=-1.)
    vsd_end = FloatParameter('VSD end', units='V', default=1.)

    # Laser Parameters
    laser_toggle = BooleanParameter('Laser toggle', default=False)
    laser_wl = ListParameter('Laser wavelength', units='nm', choices=wavelengths, group_by='laser_toggle')
    laser_v = FloatParameter('Laser voltage', units='V', default=0., group_by='laser_toggle')
    burn_in_t = FloatParameter('Burn-in time', units='s', default=60., group_by='laser_toggle')

    # Additional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2, group_by='show_more')
    vsd_step = FloatParameter('VSD step', units='V', default=0.01, group_by='show_more')
    step_time = FloatParameter('Step time', units='s', default=0.01, group_by='show_more')
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')

    INPUTS = BaseProcedure.INPUTS + ['vg', 'vsd_start', 'vsd_end', 'vsd_step', 'step_time', 'N_avg', 'laser_toggle', 'laser_wl', 'laser_v', 'burn_in_t', 'Irange']
    DATA_COLUMNS = ['Vsd (V)', 'I (A)']

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
        self.meter.measure_current(current=self.Irange, auto_range=not bool(self.Irange))

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
            f"Finished IV measurement for Chip {self.chip_group} {self.chip_number}, Sample {self.sample}!"
        )