import time
import numpy as np

from pymeasure.experiment import Procedure, FloatParameter, ListParameter, IntegerParameter, Parameter, Metadata

from lib.instruments import TENMA, ThorlabsPM100USB
from lib.display import display_experiment
from lib import config, log


class LaserCalibration(Procedure):
    """Uses the Power Meter to calculate the effective power of the laser
    at a given voltage.
    """
    # Procedure version. When modified, increment
    # <parameter name>.<parameter property>.<procedure startup/shutdown>
    procedure_version = Parameter('Procedure version', default='1.1.1')
    fibers = list(eval(config['Laser']['fibers']))

    laser_wl = ListParameter('Laser wavelength', units='nm', choices=list(eval(config['Laser']['wavelengths'])))
    fiber = ListParameter('Optical fiber', choices=fibers)
    vl_start = FloatParameter('Laser voltage start', units='V', default=0.)
    vl_end = FloatParameter('Laser voltage end', units='V', default=5.)
    vl_step = FloatParameter('Laser voltage step', units='V', default=0.1)
    step_time = FloatParameter('Step time', units='s', default=2.)
    N_avg = IntegerParameter('N_avg', default=2)

    # Metadata
    start_time = Metadata('Start time', fget=time.time)
    sensor = Metadata('Sensor model', fget='power_meter.sensor_name')

    INPUTS = ['laser_wl', 'fiber', 'vl_start', 'vl_end', 'vl_step', 'step_time', 'N_avg']
    DATA_COLUMNS = ['VL (V)', 'Power (W)']

    def startup(self):
        log.info("Setting up instruments")
        try:
            self.power_meter = ThorlabsPM100USB(config['Adapters']['power_meter'])
            self.tenma_laser = TENMA(config['Adapters']['tenma_laser'])
        except:
            log.error("Could not connect to instruments")
            raise

        self.tenma_laser.apply_voltage(0.)
        self.tenma_laser.output = True
        time.sleep(1.)

        self.power_meter.wavelength = self.laser_wl

    def execute(self):
        log.info("Starting the measurement")

        self.vl_ramp = np.arange(self.vl_start, self.vl_end + self.vl_step, self.vl_step)
        avg_array = np.zeros(self.N_avg)

        for i, vl in enumerate(self.vl_ramp):
            if self.should_stop():
                break

            self.emit('progress', 100 * i / len(self.vl_ramp))

            self.tenma_laser.voltage = vl

            time.sleep(self.step_time)

            # Take the average of N_avg measurements
            for j in range(self.N_avg):
                avg_array[j] = self.power_meter.power

            self.emit('results', dict(zip(self.DATA_COLUMNS, [vl, np.mean(avg_array)])))
            avg_array[:] = 0.

    def shutdown(self):
        if not hasattr(self, 'power_meter'):
            log.info("No instruments to shutdown.")
            return
        
        self.power_meter.shutdown()
        self.tenma_laser.shutdown()
        log.info("Instruments shutdown.")


if __name__ == '__main__':
    display_experiment(LaserCalibration, 'Laser calibration')