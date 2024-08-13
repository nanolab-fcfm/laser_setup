"""Module for setting up the parameters for the laser setup.
Parameters should be defined here and imported in the procedures.
"""
import copy
import time
import configparser

from pymeasure.experiment import IntegerParameter, Parameter, BooleanParameter, ListParameter, FloatParameter, Metadata

from . import config

overrides = configparser.ConfigParser()
overrides.read(config.get('Procedures', 'parameter_file'))


class ParameterProvider:
    """Base class for Parameters objects. When a parameter is
    accessed, a copy of the parameter is returned to avoid
    modifying the original parameter.
    """
    def __getattribute__(self, name):
        # Use super to get the attribute
        attr = super().__getattribute__(name)

        # Check if the attribute is a Parameter or Metadata instance
        if isinstance(attr, (Parameter, Metadata)):
            return copy.deepcopy(attr)

        return attr


class BaseParameters(ParameterProvider):
    # Procedure version. When modified, increment
    # <parameter name>.<parameter property>.<procedure startup/shutdown>
    procedure_version = Parameter('Procedure version', default='1.5.0')
    show_more = BooleanParameter('Show more', default=False)
    info = Parameter('Information', default='None')

    # Chained Execution
    chained_exec = BooleanParameter('Chained execution', default=False)

    # Metadata
    start_time = Metadata('Start time', fget=time.time)


class ChipParameters(ParameterProvider):
    chip_names = list(eval(config['Chip']['names'])) + ['other']
    samples = list(eval(config['Chip']['samples'])) + ['other']

    chip_group = ListParameter('Chip group name', choices=chip_names, default='other')
    chip_number = IntegerParameter('Chip number', default=1, minimum=1)
    sample = ListParameter('Sample', choices=samples, default='other')


class LaserParameters(ParameterProvider):
    wavelengths = list(eval(config['Laser']['wavelengths']))
    fibers = list(eval(config['Laser']['fibers']))

    laser_toggle = BooleanParameter('Laser toggle', default=False)
    laser_wl = ListParameter('Laser wavelength', units='nm', choices=wavelengths)
    laser_v = FloatParameter('Laser voltage', units='V', default=0.)
    laser_T = FloatParameter('Laser ON+OFF period', units='s', default=120.)
    burn_in_t = FloatParameter('Burn-in time', units='s', default=60.)

    fiber = ListParameter('Optical fiber', choices=fibers)


class InstrumentParameters(ParameterProvider):
    N_avg = IntegerParameter('N_avg', default=2, group_by='show_more')  # deprecated
    Irange = FloatParameter('Irange', units='A', default=0.001, minimum=0, maximum=0.105, group_by='show_more')
    NPLC = FloatParameter('NPLC', default=1.0, minimum=0.01, maximum=10, group_by='show_more')

    sensor = Metadata('Sensor model', fget='power_meter.sensor_name')


class ControlParameters(ParameterProvider):
    sampling_t = FloatParameter('Sampling time (excluding Keithley)', units='s', default=0., group_by='show_more')
    vds = FloatParameter('VDS', units='V', default=0.075, decimals=10)
    vg = FloatParameter('VG', units='V', default=0., minimum=-100., maximum=100.)
    vg_dynamic = Parameter('VG', default='DP + 0. V')

    # Voltage ramps
    step_time = FloatParameter('Step time', units='s', default=0.01, group_by='show_more')

    vg_start = FloatParameter('VG start', units='V', default=-35.)
    vg_end = FloatParameter('VG end', units='V', default=35.)
    vg_step = FloatParameter('VG step', units='V', default=0.2, group_by='show_more')

    vsd_start = FloatParameter('VSD start', units='V', default=-1.)
    vsd_end = FloatParameter('VSD end', units='V', default=1.)
    vsd_step = FloatParameter('VSD step', units='V', default=0.01, group_by='show_more')

    vl_start = FloatParameter('Laser voltage start', units='V', default=0.)
    vl_end = FloatParameter('Laser voltage end', units='V', default=5.)
    vl_step = FloatParameter('Laser voltage step', units='V', default=0.1)


class Parameters:
    """Class to define all the parameters for the laser setup."""
    Base = BaseParameters()
    Chip = ChipParameters()
    Laser = LaserParameters()
    Instrument = InstrumentParameters()
    Control = ControlParameters()
