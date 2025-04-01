from .config import CONFIG, instantiate
from .display.app import display_window
from .parser import get_args


def main():
    args = get_args()

    CONFIG._session.args = vars(args)

    if args.procedure is None:
        display_window()

    elif args.procedure in CONFIG.procedures:
        display_window(instantiate(
            CONFIG.procedures._types[args.procedure], level=1
        ))

    elif args.procedure in CONFIG.scripts:
        func = instantiate(CONFIG.scripts[args.procedure].target, level=1)
        if callable(func):
            func()

    else:
        # This should never happen
        raise ValueError(f"Invalid argument: {args.procedure}")


if __name__ == '__main__':
    main()
