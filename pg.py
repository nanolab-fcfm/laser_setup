import logging
import sys
import time
import numpy as np

from pymeasure.instruments.keithley import Keithley2450
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import (
    Procedure, FloatParameter, IntegerParameter, unique_filename, Results
)

log = logging.getLogger('')
log.addHandler(logging.NullHandler())

KEITHLEY_ADDRESS = "USB0::1510::9296::04448997::0::INSTR"
TENMA1_ADDRESS = "COM3"
TENMA2_ADDRESS = "COM4"


class TEST(Procedure):
    """Blank Test that just adds logs and saves some data"""
    test_arg = FloatParameter('Test Argument', units='V', default=0.1)
    INPUTS = ['test_arg']
    DATA_COLUMNS = ['Test Argument', 'Another Argument']

    def startup(self):
        log.info("Setting up instruments")

    def execute(self):
        log.info("Executing procedure")
        self.emit('results', {
            'test_arg': [self.test_arg]*10,
            'another': [self.test_arg]*10
        })
        self.emit('progress', 50)
        time.sleep(1)
        self.emit('progress', 100)
    
    def shutdown(self):
        log.info("Shutting down procedure")


# Create a procedure that measures a gate sweep with a Keithley 2450
class I_T(Procedure):
    """
    Measures current as a function of time with a Keithley 2450.
    """
    # Parameters are defined as class attributes
    vds = FloatParameter('VDS', units='V', default=0.075)
    vgs_start = FloatParameter('VG start', units='V', default=-35.)
    vgs_end = FloatParameter('VG end', units='V', default=35.)
    vgs_step = FloatParameter('VG step', units='V', default=5)
    time_on = FloatParameter('Time on', units='s', default=360)
    alpha = FloatParameter('alpha')
    samples = IntegerParameter('Samples', default=1000)

    INPUTS = ['vds', 'vgs_start', 'vgs_end', 'vgs_step', 'time_on', 'alpha', 'samples']
    DATA_COLUMNS = ['Time (s)', 'Vds (V)', 'Vgs (V)', 'I (A)']

    def startup(self):
        log.info("Setting up instruments")
        self.meter = Keithley2450("USB0::1510::9296::04448997::0::INSTR")
        # self.meter.use_front_terminals()
        self.meter.reset()
        self.meter.apply_voltage(compliance_current=0.001)
        self.meter.measure_current(nplc=1, current=0.001)

        # As sources, we have 2 TENMAs.
        # TODO: Add the TENMAs as sources, and fix the meter.

    def execute(self):
        # This is all wrong, TODO fix it.
        # Create the sequence of voltages for the gate
        vgs_array = np.arange(self.vgs_start, self.vgs_end, self.vgs_step)

        self.emit('progress', 0)
        for i, vgs in enumerate(vgs_array):
            self.meter.source_voltage = vgs
            self.emit('progress', 100 * i / len(vgs_array))
            self.emit('results', {
                'Vds': self.vds,
                'Vgs': vgs,
                'I': self.meter.voltage
            })
            self.emit('sleep', 0.1)

    def shutdown(self):
        self.meter.shutdown()
        log.info("Finished!")

class MainWindow(ManagedWindow):

    def __init__(self):
        super().__init__(
            procedure_class=I_T,
            inputs=I_T.INPUTS,
            displays=I_T.INPUTS,
            x_axis=I_T.DATA_COLUMNS[0],
            y_axis=I_T.DATA_COLUMNS[-1],
        )
        self.setWindowTitle('I vs T Measurement')

    def queue(self):
        directory = "./data/"
        filename = unique_filename(
            directory,
            prefix='I_T',
            dated_folder=True
            )
        procedure = self.make_procedure()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


class MainWindow(ManagedWindow):
    
        def __init__(self):
            super().__init__(
                procedure_class=TEST,
                inputs=TEST.INPUTS,
                displays=TEST.INPUTS,
                x_axis=TEST.DATA_COLUMNS[0],
                y_axis=TEST.DATA_COLUMNS[-1],
            )
            self.setWindowTitle('I vs T Measurement')
    
        def queue(self):
            directory = "./data/"
            filename = unique_filename(
                directory,
                prefix='TEST',
                dated_folder=True
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
