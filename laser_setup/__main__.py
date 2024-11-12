import argparse

from .display import MainWindow, ExperimentWindow, display_window
from .procedures import *
from .cli import setup_adapters, console, find_dp_script, get_updates

Sequences = {
    MainSequence: 'Sequence',
}

Experiments = {
    IV: 'I vs V',
    IVg: 'I vs Vg',
    It: 'I vs t',
    ItVg: 'I vs t (Vg)',
    ITt: 'I,T vs t',
    IVgT: 'I,T vs Vg',
    Tt: 'T vs t',
    Pt: 'P vs t',
    LaserCalibration: 'Calibrate Laser',
}

Scripts = {
    setup_adapters.setup: 'Set up Adapters',
    console.main: 'Console',
    find_dp_script.main: 'Find Dirac Point',
    get_updates.main: 'Get Updates',
}

def main():
    experiment_list = [cls.__name__ for cls in Experiments.keys()]
    script_list = [func.__module__.split('.')[-1] for func in Scripts.keys()]

    parser = argparse.ArgumentParser(description='Laser Setup')
    parser.add_argument('procedure', nargs='?', help='Procedure to run', choices=experiment_list + script_list)
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='Enable debug mode')
    args = parser.parse_args()

    if args.procedure is None:
        display_window(MainWindow, Sequences, Experiments, Scripts)

    elif args.procedure in experiment_list:
        display_window(
            ExperimentWindow, eval(args.procedure), title=Experiments[eval(args.procedure)]
        )

    elif args.procedure in script_list:
        eval(args.procedure).main()

    else:
        raise ValueError(f"Invalid argument: {args.procedure}")


if __name__ == '__main__':
    main()
