"""This script compares Keithley time with time.time()"""
import time
import numpy as np

from pymeasure.instruments.keithley import Keithley2450
from pymeasure.experiment import Procedure, FloatParameter

from lib import log, config
from lib.display import display_experiment

np.random.seed(2)

class Time(Procedure):
    """Docstring"""
    total_time = FloatParameter('Total Time', units='s', default=20.)
    INPUTS = ['total_time']
    DATA_COLUMNS = ['Keithley Time (s)', 'Time.time (s)', 'Error']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.meter = Keithley2450(config['Adapters']['keithley2450'])
        except ValueError:
            log.error("Could not connect to instruments")
            raise

        # Keithley 2450 meter
        self.meter.reset()
        self.meter.write(':TRACe:MAKE "IVBuffer", 100000')

        time.sleep(0.5)

    def execute(self):
        tf = self.total_time
        t_base = time.time()
        keithley_t = float(self.meter.ask(':READ? "IVBuffer", REL')[:-1])
        while tf > keithley_t:
            self.emit('progress', 100 * (keithley_t) / tf)

            time_time = time.time() - t_base
            keithley_t = float(self.meter.ask(':READ? "IVBuffer", REL')[:-1])
            print(keithley_t, end='\r')

            self.emit('results', dict(zip(self.DATA_COLUMNS, [keithley_t, time_time, (time_time - keithley_t) / keithley_t])))

    def shutdown(self):
        if not hasattr(self, 'meter'):
            log.info("No instruments to shutdown.")
            return

        self.meter.shutdown()

if __name__ == "__main__":
    display_experiment(Time, 'Time meas')
