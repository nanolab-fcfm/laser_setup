import logging

from ..config import ConfigHandler, config

log = logging.getLogger(__name__)


def init_config(parent=None, verbose=True):
    """Initiliaze the configuration files by copying the template files to the
    selected directory.
    """
    config_handler = ConfigHandler(parent=parent, config=config)
    config_handler.init_config(verbose=verbose)


def main():
    init_config(parent=None)


if __name__ == "__main__":
    main()
