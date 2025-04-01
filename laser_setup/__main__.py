from .config import CONFIG, instantiate, setup
from .display.app import display_window


def main():
    setup()

    args = CONFIG._session.args
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
