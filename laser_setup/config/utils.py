import logging
import os
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

from hydra.utils import instantiate as hydra_instantiate
from omegaconf import DictConfig, OmegaConf

from .main import AppConfig, DefaultPaths

log = logging.getLogger(__name__)
T = TypeVar('T')


def safeget(dic: dict | DictConfig, *keys, default: Any = None) -> Any:
    """Safely get a value from a dictionary with a list of keys.

    :param dic: Dictionary to get the value from.
    :param keys: List of keys to traverse the dictionary.
    :param default: Default value to return if a key is not found.
    :return: Value of the last key in the list.
    """
    for key in keys:
        if not isinstance(dic, (dict, DictConfig)) or key not in dic:
            return default
        dic = dic[key]
    return dic


def load_config(
    config_env: str = 'CONFIG',
    lookup: list[tuple[str, str]] = DefaultPaths.default_config_lookup,
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


def load_yaml(
    file_path: str | Path,
    struct: Optional[Type[T]] = None,
    flags: Optional[dict[str, bool]] = None,
    _instantiate: bool = False,
    **kwargs,
    ) -> T | DictConfig:
    """Load a YAML file and return its contents as a dictionary.

    :param file_path: Path to the YAML file.
    :param struct: Optional dataclass to structure the dictionary.
    :param instantiate: Whether to instantiate with `hydra.utils.instantiate`.
    :param kwargs: Additional arguments for `instantiate`.
    :return: Dictionary with the contents of the YAML file.
    """
    file_path = Path(file_path)
    try:
        data = OmegaConf.load(file_path)
    except FileNotFoundError:
        log.warning(f"File not found: {file_path}. Returning an empty dictionary.")
        data = OmegaConf.create(flags=flags)

    if struct is not None:
        config_struct = OmegaConf.structured(struct, flags=flags)
        data = OmegaConf.merge(config_struct, data)

    if _instantiate:
        data = instantiate(data, **kwargs)

    return data


def save_yaml(dictionary: dict | DictConfig, file_path: str | Path, **kwargs):
    """Save a dictionary to a YAML file.

    :param dictionary: Dictionary to save.
    :param file_path: Path to the YAML file.
    :param kwargs: Additional arguments for `OmegaConf.save
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    OmegaConf.save(dictionary, file_path, **kwargs)


def instantiate(config: DictConfig, level: int = 2) -> Any:
    """Instantiate a dictionary with `hydra.utils.instantiate`.

    :param config: Dictionary with the configuration.
    :param level: Number of times to instantiate the dictionary. Default is 2
        to resolve interpolations the first time.
    :return: Instantiated dictionary.
    """
    for _ in range(level):
        config = hydra_instantiate(config)
    return config
