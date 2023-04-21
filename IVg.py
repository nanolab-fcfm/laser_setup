"""
This Script is used to measure the IV characteristics of a device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
import logging
import configparser
import sys
import time
import numpy as np

from lib.devices import TENMA, vg_ramp
from pymeasure.instruments.keithley import Keithley2450
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import (
    Procedure, FloatParameter, IntegerParameter, unique_filename, Results
)

config = configparser.ConfigParser()
config.read('config.ini')

log = logging.getLogger('')
log.addHandler(logging.NullHandler())


class IVg(Procedure):
    """
    Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by a TENMA source.
    """
    # Important Parameters
    vds = FloatParameter('VDS', units='V', default=0.075)
    vg_start = FloatParameter('VG start', units='V', default=-35.)
    vg_end = FloatParameter('VG end', units='V', default=35.)

    # Optional Parameters, preferably don't change
    N_avg = IntegerParameter('N_avg', default=2)
    Irange = FloatParameter('Irange', units='A', default=0.001)
    vg_step = FloatParameter('VG step', units='V', default=1)
    step_time = FloatParameter('Step time', units='s', default=0.5)
    
    INPUTS = ['vds', 'vg_start', 'vg_end', 'N_avg', 'Irange', 'vg_step', 'step_time']
    DATA_COLUMNS = ['Vds (V)', 'Vg (V)', 'I (A)']

    def startup(self):
        log.info("Setting up instruments")
        self.meter = Keithley2450(config['Adapters']['Keithley2450'])
        self.meter.reset()
        # self.meter.use_front_terminals()
        self.meter.apply_voltage(
            voltage_range=max(abs(self.vg_start), abs(self.vg_end)),
            compliance_current=self.Irange
            )
        self.meter.voltage = 0
        self.meter.measure_current(current=self.Irange, auto_range=False)

        # TENMA sources (TODO: check if this works)
        self.negsource = TENMA(config['Adapters']['TenmaNeg'])
        self.negsource.timeout = 1.
        self.negsource.current = 0.05
        time.sleep(0.1)
        self.negsource.voltage = 0.

        self.possource = TENMA(config['Adapters']['TenmaPos'])
        self.possource.timeout = 1.
        self.possource.current = 0.05
        time.sleep(0.1)
        self.possource.voltage = 0.

        # Turn on the outputs
        self.meter.enable_source()
        time.sleep(0.5)
        self.negsource.output = True
        time.sleep(1.)
        self.possource.output = True
        time.sleep(1.)

    def execute(self):
        # Set the Vds
        self.meter.source_voltage = self.vds

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = vg_ramp(self.vg_start, self.vg_end, self.vg_step)
        data_array = np.zeros((len(self.vg_ramp), 3))
        for i, vg in enumerate(self.vg_ramp):
            self.emit('progress', 100 * i / len(self.vg_ramp))

            if self.vg_start > 0:
                self.possource.voltage = vg
            else:
                self.negsource.voltage = -vg
            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            avg_array = np.zeros(self.N_avg)
            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            data_array[i] = [self.vds, vg, np.mean(avg_array)]      # FIXME: check if this is correct, because averaging over only the second half of the data could be better.

            self.emit('results', dict(zip(self.DATA_COLUMNS, data_array[i])))
            
    def shutdown(self):
        self.meter.shutdown()
        # Assuming that their voltages are ~0
        self.negsource.output = False
        self.possource.output = False
        log.info("Finished!")


class MainWindow(ManagedWindow):

    def __init__(self, cls=IVg):
        self.cls = cls
        super().__init__(
            procedure_class=cls,
            inputs=cls.INPUTS,
            displays=cls.INPUTS,
            x_axis=cls.DATA_COLUMNS[1],
            y_axis=cls.DATA_COLUMNS[-1],
        )
        self.setWindowTitle('I vs Vg Measurement')

    def queue(self):
        directory = config['Dir']['DataDir']
        filename = unique_filename(
            directory,
            prefix=self.cls.__name__,
            dated_folder=True,
            )
        procedure = self.make_procedure()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
