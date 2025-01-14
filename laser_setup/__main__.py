import argparse

from . import __version__
from .cli import Scripts, script_list
from .display import ExperimentWindow, display_window
from .display.main_window import main as display_main
from .procedures import Experiments, experiment_list


def main():
    parser = argparse.ArgumentParser(description='Laser Setup')
    parser.add_argument('procedure', nargs='?', help='Procedure to run', choices=experiment_list + script_list)
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='Enable debug mode')

    args = parser.parse_args()

    if args.procedure is None:
        display_main()

    elif args.procedure in experiment_list:
        idx = experiment_list.index(args.procedure)
        display_window(
            ExperimentWindow, Experiments[idx][0], title=Experiments[idx][1]
        )

    elif args.procedure in script_list:
        idx = script_list.index(args.procedure)
        Scripts[idx][0]()

    else:
        raise ValueError(f"Invalid argument: {args.procedure}")


if __name__ == '__main__':
    main()
