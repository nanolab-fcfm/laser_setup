from .config import config, instantiate
from .display.app import display_window
from .parser import parser, procedures, scripts


def main():
    args, _ = parser.parse_known_args()
    config._session['args'] = vars(args)

    if args.procedure is None:
        display_window()

    elif args.procedure in procedures:
        idx = procedures[args.procedure]
        display_window(instantiate(
            config.Qt.MainWindow.procedures[idx].target, level=1
        ))

    elif args.procedure in scripts:
        idx = scripts[args.procedure]
        func = instantiate(config.Qt.MainWindow.scripts[idx].target, level=1)
        if callable(func):
            func()

    else:
        # This should never happen
        raise ValueError(f"Invalid argument: {args.procedure}")


if __name__ == '__main__':
    main()
