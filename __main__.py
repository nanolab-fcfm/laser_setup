from lib.display import MainWindow, display_window
from Scripts import *

Sequences = {
    'Main Sequence': MainSequence.MainSequence,
}

Experiments = {
    'I vs V': IV.IV,
    'I vs Vg': IVg.IVg,
    'I vs t': It.It,
    'P vs t': Pt.Pt,
    'Calibrate Laser': calibrate_laser.LaserCalibration,
}

Scripts = {
    'Set up Adapters': setup_adapters.main,
    'Console': console.main,
    'Find Dirac Point': find_dp_script.main,
}


if __name__ == '__main__':
    display_window(MainWindow, Sequences, Experiments, Scripts)