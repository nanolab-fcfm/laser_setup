from laser_setup.display import MainWindow, display_window
from laser_setup.procedures import *
from Scripts.MainSequence import MainSequence
from Scripts import setup_adapters, console, find_dp_script

Sequences = {
    MainSequence: 'Sequence',
}

Experiments = {
    IV: 'I vs V',
    IVg: 'I vs Vg',
    It: 'I vs t',
    Pt: 'P vs t',
    LaserCalibration: 'Calibrate Laser',
}

Scripts = {
    setup_adapters.setup: 'Set up Adapters',
    console.keithley_console: 'Console',
    find_dp_script.main: 'Find Dirac Point',
}


if __name__ == '__main__':
    display_window(MainWindow, Sequences, Experiments, Scripts)
