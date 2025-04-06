import logging

from ..config import ConfigHandler, CONFIG

log = logging.getLogger(__name__)


def ask_create_config(parent=None) -> bool:     # Not used at the moment
    """Ask the user if they want to create a new configuration directory.
    """
    title = 'Create new config?'
    desc = 'No configuration found. Create new config directory?'

    if hasattr(parent, 'question_box') and callable(parent.question_box):
        create_config = parent.question_box(title, desc)
    else:
        log.info(desc)
        create_config = (input(f'{title} (Y/n): ').lower() in ['y', ''])

    if not create_config:
        log.error('Cannot edit settings without a config file.')

    return bool(create_config)


def init_config(parent=None):
    """Initiliaze the configuration files by copying the template files to the
    selected directory.
    """
    config_handler = ConfigHandler(parent=parent, config=CONFIG)
    config_handler.init_templates()
    config_handler.init_config(exist_ok=False)


def main():
    init_config(parent=None)


if __name__ == "__main__":
    main()
