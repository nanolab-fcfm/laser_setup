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
        self.save_path = Path(self.config._session.save_path)
        self.config_path_used = self.config._session.config_path_used

        self.app = make_app()
        if parent is None:
            parent = QtWidgets.QWidget()

        self.parent = parent

    def config_exists(self) -> bool:
        """Check if the configuration file exists.

        :return: True if the configuration file exists locally.
        """
        return self.config_path_used != 'default'

    @staticmethod
    def load_config(
        lookup: list[tuple[str, str]] | None = None,
    ) -> AppConfig | DictConfig:
        """Load the configuration files appropiately. By default, it loads the
        files in the following order:
        1. Default configuration file.
        2. Global configuration file (if it exists), with its path defined in the
        default config, and overwritten with the environment variable `config_env`.
        3. Local configuration file (if it exists), with its path defined in the
        global config.

        :param lookup: List of tuples with the keys to look for the configuration files.
        :return: The parsed configuration
        """
        config: AppConfig = OmegaConf.structured(AppConfig, flags={'allow_objects': True})
        config_path_used: str | Path = 'default'

        if lookup is None:
            lookup = ConfigHandler.lookup

        for section, key in lookup:
            if config_path := safeget(config, section, key):
                config_path = Path(config_path)
                if config_path.is_file():
                    new_config = OmegaConf.load(config_path)
                    config = OmegaConf.merge(config, new_config)
                    config_path_used = config_path

        config._session.config_path_used = config_path_used
        config._session.save_path = config_path

        return config

    def init_templates(self) -> None:
        """Paste the template files to the config directory."""
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        templates_dir = self.save_path.parent / 'templates'
        shutil.copytree(
            DefaultPaths.templates, templates_dir, dirs_exist_ok=True
        )
        log.info(f'Copied templates to {templates_dir}')

    def init_config(self, exist_ok: bool = True) -> Path | None:
        """Initiliaze the configuration files by copying the template files to the
        selected directory.

        :param verbose: Whether to print information messages or not.
        """
        if self.config_exists():
            if not exist_ok:
                log.info(f'Config found at {self.save_path}. Skipping.')

            return self.save_path

        shutil.copy(DefaultPaths.new_config, self.save_path)
        log.info(f'Copied config files to {self.save_path.parent}')

        return self.save_path / 'config.yaml'

    def edit_config(self):
        save_path = self.init_config(exist_ok=True)
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
        _yaml['Dir']['local_config_file'] = load_path
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

        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        save_yaml(config_container, self.save_path, **kwargs)
        log.info(f'Config saved to {self.save_path}')
