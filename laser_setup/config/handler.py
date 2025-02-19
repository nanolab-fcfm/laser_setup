"""Handler for the configuration I/O operations."""
import logging
import os
import shutil
from pathlib import Path

from omegaconf import DictConfig, OmegaConf

from ..display.Qt import QtWidgets, make_app
from .defaults import AppConfig, DefaultPaths
from .utils import load_yaml, safeget, save_yaml

log = logging.getLogger(__name__)


class ConfigHandler:
    """Handler for the configuration I/O operations. It allows to load, edit and
    import configuration files.

    :param parent: Parent widget for the file dialogs.
    :param config: Configuration file to use. If not provided, it will load the
        configuration files from the default paths.
    """
    lookup: list[tuple[str, str]] = [
        ('Dir', 'global_config_file'),
        ('Dir', 'local_config_file')
    ]

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        config: AppConfig | DictConfig | None = None
    ):
        self.config = config or self.load_config()
        self.save_path = Path(self.config._session['save_path'])
        self.config_path_used = self.config._session['config_path_used']

        self.app = make_app()
        if parent is None:
            parent = QtWidgets.QWidget()

        self.parent = parent

    @staticmethod
    def load_config(
        config_env: str = 'CONFIG',
        lookup: list[tuple[str, str]] = lookup,
    ) -> AppConfig | DictConfig:
        """Load the configuration files appropiately. By default, it loads the
        files in the following order:
        1. Default configuration file.
        2. Global configuration file (if it exists), with its path defined in the
        default config, and overwritten with the environment variable `config_env`.
        3. Local configuration file (if it exists), with its path defined in the
        global config.

        :param config_env: Environment variable to look for the global configuration file.
        :param lookup: List of tuples with the keys to look for the configuration files.
        :return: The parsed configuration
        """
        config: AppConfig = OmegaConf.structured(AppConfig)
        config_path_used: str | Path = 'default'

        if config_env_path := os.getenv(config_env):
            config[lookup[0][0]][lookup[0][1]] = config_env_path

        for section, key in lookup:
            if config_path := safeget(config, section, key):
                config_path = Path(config_path)
                if config_path.is_file():
                    new_config = OmegaConf.load(config_path)
                    config = OmegaConf.merge(config, new_config)
                    config_path_used = config_path

        config._session = {
            'config_path_used': config_path_used,
            'save_path': config_path
        }
        return config

    def init_config(self, verbose=True):
        """Initiliaze the configuration files by copying the template files to the
        selected directory.

        :param verbose: Whether to print information messages or not.
        """
        if self.config_path_used != 'default':
            if verbose:
                log.info(f'Config found at {self.save_path}. Skipping initialization.')

            return self.save_path

        title = 'Create new config?'
        desc = 'No configuration found. Create new config directory?'

        try:
            create_config = self.parent.question_box(title, desc)
        except AttributeError:
            log.info(desc)
            create_config = (input(f'{title} (y/n): ').lower() == 'y')

        if not create_config:
            log.warning('Cannot edit settings without a config file.')
            return

        self.save_path.parent.mkdir(parents=True, exist_ok=True)

        _save_path = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self.parent,
            caption='Select config directory',
            directory=str(self.save_path.parent),
        )
        save_path = Path(_save_path)

        # Copy the files in the assets folder to it
        for file in DefaultPaths.config.parent.iterdir():
            shutil.copy(file, save_path)

        log.info(f'Copied config files to {save_path}')
        return save_path / 'config.yaml'

    def edit_config(self):
        save_path = self.init_config(verbose=False)
        try:
            if os.name == 'nt':
                os.startfile(save_path)
            elif os.name == 'posix':
                os.system(f'xdg-open {save_path}')
            else:
                log.warning(f'Your OS ({os.name}) is not supported.')
        except Exception as e:
            log.error(f'Error opening the config file: {e}')
        try:
            self.parent.suggest_reload()
        except AttributeError:
            pass

    def import_config(self):
        load_path = Path(self.config.Dir.local_config_file)
        _load_path = QtWidgets.QFileDialog.getOpenFileName(
            self.parent, 'Open config file', str(load_path), DefaultPaths.allowed_files,
        )[0]
        load_path = Path(_load_path)
        if not load_path.is_file():
            if str(load_path) != '.':
                log.warning(f'Config file {load_path} not found.')
            return

        global_config_path = Path(self.config.Dir.global_config_file)
        if not global_config_path.is_file():
            log.warning(
                'Loading a config file is not possible without a global config file. '
                f'Creating one at {global_config_path}'
            )
            text = DefaultPaths.config.read_text()
            global_config_path.write_text(text)

        _yaml = load_yaml(global_config_path)
        _yaml['Dir']['local_config_file'] = load_path.as_posix()
        save_yaml(_yaml, global_config_path)
        log.info(f'Switched to config file {load_path}')

        try:
            self.parent.reload.click()
        except AttributeError:
            pass

    def save_config(
        self,
        config: AppConfig | DictConfig | dict = None,
        save_path: Path | str = None,
        **kwargs
    ):
        """Save the configuration to the selected path.

        :param config: Configuration to save. If not provided, it will save the
            current configuration.
        :param save_path: The save patth. If not provided, it will use stored one
            in the session.
        :param kwargs: Additional arguments for `save_yaml`.
        """
        if config is not None:
            self.config = OmegaConf.merge(self.config, config)

        if save_path is not None:
            self.save_path = Path(save_path)

        config_container = OmegaConf.to_container(self.config)
        config_container.pop('_session', None)

        save_yaml(config_container, self.save_path, **kwargs)
        log.info(f'Config saved to {self.save_path.as_posix()}')
