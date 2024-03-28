from .It import It
from .IV import IV
from .IVg import IVg
from .Pt import Pt
from .calibrate_laser import LaserCalibration
from .setup_adapters import main as setup_adapters_main
from .find_dp_script import main as find_dp_script_main

Apps = {
    'I vs V': IV,
    'I vs Vg': IVg,
    'I vs t': It,
    'P vs t': Pt,
    'Calibrate Laser': LaserCalibration,
}

Scripts = {
    'Set up Adapters': setup_adapters_main,
    'Find Dirac Point': find_dp_script_main,
}
