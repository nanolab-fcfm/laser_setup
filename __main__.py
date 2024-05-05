from laser_setup.display import MainWindow, display_window
from laser_setup.procedures import *
from Scripts.MainSequence import MainSequence
from Scripts import setup_adapters, console, find_dp_script

Sequences = {
    'Sequence': MainSequence,
}

Experiments = {
    'I vs V': IV,
    'I vs Vg': IVg,
    'I vs t': It,
    'P vs t': Pt,
    'Calibrate Laser': LaserCalibration,
}

Scripts = {
    'Set up Adapters': setup_adapters.setup,
    'Console': console.keithley_console,
    'Find Dirac Point': find_dp_script.main,
}


if __name__ == '__main__':
    display_window(MainWindow, Sequences, Experiments, Scripts)
