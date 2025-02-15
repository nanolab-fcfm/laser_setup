from dataclasses import dataclass
from typing import TypeVar

from pymeasure.experiment import (BooleanParameter, FloatParameter,
                                  IntegerParameter, ListParameter, Metadata,
                                  Parameter)

AnyParameter = TypeVar('AnyParameter', Parameter, Metadata)


@dataclass
class BaseParameters:
    procedure_version: Parameter
    show_more: BooleanParameter
    info: Parameter
    chained_exec: BooleanParameter
    start_time: Metadata


@dataclass
class ChipParameters:
    chip_group: ListParameter
    chip_number: IntegerParameter
    sample: ListParameter


@dataclass
class LaserParameters:
    laser_toggle: BooleanParameter
    laser_wl: ListParameter
    laser_v: FloatParameter
    laser_T: FloatParameter
    burn_in_t: FloatParameter
    fiber: ListParameter
    wl_start: FloatParameter
    wl_end: FloatParameter
    wl_step: FloatParameter


@dataclass
class InstrumentParameters:
    N_avg: IntegerParameter
    Irange: FloatParameter
    NPLC: FloatParameter
    sensor: Metadata
    sense_T: BooleanParameter


@dataclass
class ControlParameters:
    sampling_t: FloatParameter
    vds: FloatParameter
    vg: FloatParameter
    vg_dynamic: Parameter
    step_time: FloatParameter
    vg_start: FloatParameter
    vg_end: FloatParameter
    vg_step: FloatParameter
    vsd_start: FloatParameter
    vsd_end: FloatParameter
    vsd_step: FloatParameter
    vl_start: FloatParameter
    vl_end: FloatParameter
    vl_step: FloatParameter


@dataclass
class ParameterCatalog:
    Base: BaseParameters
    Chip: ChipParameters
    Control: ControlParameters
    Instrument: InstrumentParameters
    Laser: LaserParameters
    _types: list[str]
