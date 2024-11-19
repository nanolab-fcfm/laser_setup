from .BaseProcedure import BaseProcedure, ChipProcedure, Procedure
from .FakeProcedure import FakeProcedure
from .IVg import IVg
from .It import It
from .ItVg import ItVg
from .IV import IV
from .Pt import Pt
from .Tt import Tt
from .ITt import ITt
from .IVgT import IVgT
from .Wait import Wait
from .LaserCalibration import LaserCalibration

Experiments: list[tuple[Procedure, str]] = [
    (IV, 'I vs V'),
    (IVg, 'I vs Vg'),
    (It, 'I vs t'),
    (ItVg, 'I vs t (Vg)'),
    (ITt, 'I,T vs t'),
    (IVgT, 'I,T vs Vg'),
    (Tt, 'T vs t'),
    (Pt, 'P vs t'),
    (LaserCalibration, 'Calibrate Laser'),
]

experiment_list = [cls.__name__ for cls, desc in Experiments]


def from_str(s: str) -> list[Procedure] | Procedure:
    """Evaluates a string and returns the output"""
    return eval(s)
