import logging
import sys
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

from hydra.utils import instantiate as hydra_instantiate
from omegaconf import DictConfig, ListConfig, OmegaConf

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


def load_yaml(
    file_path: str | Path,
    struct: type[T] | None = None,
    flags: dict[str, bool] | None = None,
    _instantiate: bool = False,
    **kwargs,
) -> T | DictConfig | ListConfig:
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
    except PermissionError:
        log.debug(f"Permission denied: {file_path}.")
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
    :param kwargs: Additional arguments for `OmegaConf.save`.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    OmegaConf.save(dictionary, file_path, **kwargs)


def instantiate(
    config: T | DictConfig | ListConfig,
    level: int = 2
) -> Any | T | DictConfig | ListConfig:
    """Instantiate a dictionary with `hydra.utils.instantiate`.

    :param config: Dictionary with the configuration.
    :param level: Number of times to instantiate the dictionary. Default is 2
        to resolve interpolations the first time.
    :return: Instantiated dictionary.
    """
    for _ in range(level):
        config = hydra_instantiate(config)
    return config


def load_and_merge(
    file_path: str | Path,
    config: T,
    section: str,
    **kwargs,
) -> None:
    """Load a YAML file and merge it with an existing configuration.

    :param file_path: Path to the YAML file.
    :param config: Existing configuration to merge with.
    :param section: Section to merge the configuration into.
    :param kwargs: Additional arguments for `load_yaml`.
    :return: Merged configuration.
    """
    loaded_config = load_yaml(file_path, **kwargs)
    config[section] = OmegaConf.merge(config[section], loaded_config)


def get_type(
    name: str,
    bases: tuple[type[T], ...],
    namespace: Mapping[str, Any] | None = None,
    module: str | None = '__main__',
    **kwargs,
) -> type[T]:
    """Create a new type dynamically.

    :param name: Name of the new type.
    :param bases: Tuple of base classes.
    :param namespace: Namespace for the new type.
    :param module: Module name for the new type.
    :param kwargs: Additional arguments for `type`.
    :return: New type.
    """
    namespace = deepcopy(namespace) if namespace else {}
    if module not in sys.modules:
        sys.modules[module] = ModuleType(module)

    namespace['__module__'] = module
    namespace['__doc__'] = namespace.get('__doc__', '')
    return type(name, tuple(bases), namespace or {}, **kwargs)
