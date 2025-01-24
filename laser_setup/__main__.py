from .config import Qt_config, instantiate
from .parser import experiment_list, parser, script_list


def main():
    args = parser.parse_args()

    if args.procedure is None:
        from .display import MainWindow, display_window
        display_window(MainWindow)

    elif args.procedure in experiment_list:
        from .display import ExperimentWindow, display_window
        idx = experiment_list.index(args.procedure)
        display_window(ExperimentWindow, instantiate(
            Qt_config.MainWindow.procedures[idx].target, level=1
        ))

    elif args.procedure in script_list:
        idx = script_list.index(args.procedure)
        instantiate(Qt_config.MainWindow.scripts[idx].target, level=1)()

    else:
        # This should never happen
        raise ValueError(f"Invalid argument: {args.procedure}")


if __name__ == '__main__':
    main()
