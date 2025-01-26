import logging
from pathlib import Path
import shutil

from ..display.Qt import QtWidgets
from ..config import DefaultPaths, config

log = logging.getLogger(__name__)


def init_config(parent=None, verbose=True):
    """Initiliaze the configuration files by copying the template files to the
    selected directory.
    """
    save_path = Path(config._session['save_path'])
    if config._session['config_path_used'] != 'default':
        if verbose:
            log.info(f'Config found at {save_path}. Skipping initialization.')

        return save_path

    title = 'Create new config?'
    desc = 'No configuration found. Create new config directory?'

    if parent is not None:
        create_config = parent.question_box(title, desc)
    else:
        log.info(desc)
        create_config = (input(f'{title} (y/n): ').lower() == 'y')
        _ = QtWidgets.QApplication([])

    if not create_config:
        log.warning('Cannot edit settings without a config file.')
        return

    save_path.parent.mkdir(parents=True, exist_ok=True)

    _save_path = QtWidgets.QFileDialog.getExistingDirectory(
        caption='Select config directory', directory=str(save_path.parent),
        **(parent and {'parent': parent} or {})
    )
    save_path = Path(_save_path)

    # Copy the files in the assets folder to it
    for file in DefaultPaths.config.parent.iterdir():
        shutil.copy(file, save_path)

    log.info(f'Copied config files to {save_path}')
    return save_path / 'config.yaml'


def main():
    init_config(parent=None)


if __name__ == "__main__":
    main()
