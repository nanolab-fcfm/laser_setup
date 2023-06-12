import time

from pymeasure.instruments.keithley import Keithley2450
from pymeasure.experiment import Procedure, FloatParameter, Parameter

from lib import config, log
from .utils import SONGS
from .display import send_telegram_alert
from .instruments import TENMA


class BasicIVgProcedure(Procedure):
    """
    Basic procedure for measuring current with a Keithley 2450 and two TENMA
    sources.
    
    Modify the `execute` method to run a specific
    :class:`pymeasure.experiment.Procedure`. To add more parameters to the
    Procedure, or modify the existent ones, define a new
    `pymeasure.experiment.Parameter` as class attribute, and add it to INPUTS:
    `INPUTS = BasicIVgProcedure.INPUTS + [parameter_name]`

    To add data columns, modify DATA_COLUMNS:
    `DATA_COLUMNS = BasicIVgProcedure.DATA_COLUMNS + [column_name]`

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
    chip = Parameter('Chip', default='None')            # There must be a default value, otherwise it can't be read from the data file
    sample = Parameter('Sample', default='None')
    info = Parameter('Information', default='None')

    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg_start = FloatParameter('VG start', units='V', default=-35.)
    vg_end = FloatParameter('VG end', units='V', default=35.)

    # Optional Parameters, preferably don't change
    Irange = FloatParameter('Irange', units='A', default=0.001)

    INPUTS = ['chip', 'sample', 'info', 'vds', 'vg_start', 'vg_end', 'Irange']
    DATA_COLUMNS = ['Vg (V)', 'I (A)']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['Keithley2450'])
            self.negsource = TENMA(config['Adapters']['TenmaNeg'])
            self.possource = TENMA(config['Adapters']['TenmaPos'])
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

        message = f"Finished IVg measurement for Chip {self.chip}, Sample {self.sample}!"
        send_telegram_alert(message)
        log.info(f"Sent message via Telegram: '{message}'")
