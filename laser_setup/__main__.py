import sys

from .display import MainWindow, display_window, display_experiment
from .procedures import *
from .cli import setup_adapters, console, find_dp_script

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

def main():
    if len(sys.argv) <= 1:
        display_window(MainWindow, Sequences, Experiments, Scripts)

    elif sys.argv[1] in [cls.__name__ for cls in Experiments.keys()]:
        display_experiment(eval(sys.argv[1]), title=Experiments[eval(sys.argv[1])])

    elif sys.argv[1] in [func.__module__.split('.')[-1] for func in Scripts.keys()]:
        Scripts[eval(f"Scripts.{sys.argv[1]}")]()

    else:
        raise ValueError(f"Invalid argument: {sys.argv[1]}")


if __name__ == '__main__':
    main()
