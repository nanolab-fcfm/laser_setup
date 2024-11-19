import argparse

from .display import MainWindow, ExperimentWindow, display_window
from .cli import Scripts, script_list
from .procedures import Experiments, experiment_list


def main():
    parser = argparse.ArgumentParser(description='Laser Setup')
    parser.add_argument('procedure', nargs='?', help='Procedure to run', choices=experiment_list + script_list)
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='Enable debug mode')
    args = parser.parse_args()

    if args.procedure is None:
        display_window(MainWindow)

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
