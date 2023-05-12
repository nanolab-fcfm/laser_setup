"""
This Script is used to measure the IV characteristics of a device.
It uses a Keithley 2450 as meter and two TENMA Power Supplies.
"""
import sys
import time
import numpy as np

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import (
    Procedure, FloatParameter, IntegerParameter, unique_filename, Results, Parameter
)
from lib.utils import gate_sweep_ramp, log, config
from lib.devices import BasicIVgProcedure


class IVg(BasicIVgProcedure):
    """
    Measures a gate sweep with a Keithley 2450. The gate voltage is
    controlled by two TENMA sources.
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
    N_avg = IntegerParameter('N_avg', default=2)
    vg_step = FloatParameter('VG step', units='V', default=0.2)
    step_time = FloatParameter('Step time', units='s', default=0.01)

    INPUTS = ['chip', 'sample', 'comment', 'vds', 'vg_start', 'vg_end', 'Irange', 'N_avg', 'vg_step', 'step_time']
    DATA_COLUMNS = ['Vg (V)', 'I (A)']

    def execute(self):
        log.info("Starting the measurement")

        # Set the Vds
        self.meter.source_voltage = self.vds

        # Set the Vg ramp and the measuring loop
        self.vg_ramp = gate_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        data_array = np.zeros((len(self.vg_ramp), len(self.DATA_COLUMNS)))
        for i, vg in enumerate(self.vg_ramp):
            self.emit('progress', 100 * i / len(self.vg_ramp))

            if vg >= 0:
                self.negsource.voltage = 0.
                self.possource.voltage = vg
            elif vg < 0:
                self.possource.voltage = 0.
                self.negsource.voltage = -vg

            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            avg_array = np.zeros(self.N_avg)
            for j in range(self.N_avg):
                avg_array[j] = self.meter.current

            data_array[i] = [vg, np.mean(avg_array)]

            self.emit('results', dict(zip(self.DATA_COLUMNS, data_array[i])))


class MainWindow(ManagedWindow):

    def __init__(self, cls=IVg):
        self.cls = cls
        super().__init__(
            procedure_class=cls,
            inputs=cls.INPUTS,
            displays=cls.INPUTS,
            x_axis=cls.DATA_COLUMNS[0],
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
