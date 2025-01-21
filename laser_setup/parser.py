"""Module to parse configuration files"""
import os
from collections.abc import Mapping
from functools import partial
from pathlib import Path

import yaml


class Paths:
    """Enum with the default paths for the configuration files."""
    default_config_lookup: list[tuple[str, str]] = [
        ('General', 'global_config_file'),
        ('General', 'local_config_file')
    ]
    _parent = Path(__file__).parent
    allowed_files: str = 'YAML files (*.yaml)'
    default_config: Path = _parent / 'config' / 'default_config.yaml'
    default_parameters: Path = _parent / 'config' / 'parameters.yaml'
    default_procedures: Path = _parent / 'config' / 'procedures.yaml'
    default_splash: Path = _parent / 'assets' / 'img' / 'splash.png'


class YAMLParser:
    """Class to parse a dictionary from a YAML file with optional custom tags."""
    loader = yaml.SafeLoader
    tag_dict: dict = {}

    def get_loader(self) -> type[yaml.SafeLoader]:
        """Returns a YAML loader with custom constructors for defined tags."""
        for tag, cls in self.tag_dict.items():
            self.loader.add_constructor(tag, partial(self.get_constructor, cls))
        self.loader.add_constructor('!include', self.include_constructor)
        return self.loader

    def include_constructor(self, loader, node: yaml.nodes.ScalarNode) -> str:
        """Constructor for the `!include` YAML tag."""
        file_path = Path(node.value)
        return self.read(file_path, {})

    @staticmethod
    def get_constructor(
        cls: type,
        loader: yaml.SafeLoader,
        node: yaml.nodes.MappingNode
    ) -> any:
        """Generic constructor for custom YAML tags."""
        return cls(**loader.construct_mapping(node, deep=True))

    def read(self, file_path: str | Path, fallback: dict = None) -> dict:
        """Reads a YAML file and returns a parsed dictionary.

        :param file_path: Path to the YAML file.
        :param fallback: Fallback dictionary if the file is not found.
        :return: Parsed dictionary or the fallback.
        :raises FileNotFoundError: If the file is not found and no fallback is provided.
        """
        try:
            return load_yaml(file_path, self.get_loader())
        except FileNotFoundError:
            if fallback is not None:
                return fallback

            raise FileNotFoundError(f"File {file_path} not found")


def merge_dicts(dict1: dict, dict2: dict) -> dict:
    """Merge two dictionaries recursively.

    :param dict1: First dictionary.
    :param dict2: Second dictionary.
    :return: Merged dictionary.
    """
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, Mapping):
            dict1[key] = merge_dicts(dict1[key], value)
        else:
            dict1[key] = value
    return dict1


def safeget(dic: dict, *keys, default: any = None) -> any:
    """Safely get a value from a dictionary with a list of keys.

    :param dic: Dictionary to get the value from.
    :param keys: List of keys to traverse the dictionary.
    :param default: Default value to return if a key is not found.
    :return: Value of the last key in the list.
    """
    for key in keys:
        if not isinstance(dic, dict) or key not in dic:
            return default
        dic = dic[key]
    return dic


def load_yaml(file_path: str|Path, loader: yaml.SafeLoader = yaml.SafeLoader) -> dict:
    """Load a YAML file and return its contents as a dictionary.

    :param file_path: Path to the YAML file.
    :return: Dictionary with the contents of the YAML file.
    """
    file_path = Path(file_path)
    return yaml.load(file_path.read_text(), Loader=loader) or {}


def load_config(
    config_env: str = 'CONFIG',
    lookup: list[tuple[str, str]] = Paths.default_config_lookup
) -> dict:
    """Load the configuration files appropiately. By default, it loads the
    files in the following order:
    1. Default configuration file.
    2. Global configuration file (if it exists), with its path defined in the
    default config, and overwritten with the environment variable `config_env`.
    3. Local configuration file (if it exists), with its path defined in the
    global config.

    :param config_env: Environment variable to look for the global configuration file.
    :param lookup: List of tuples with the keys to look for the configuration files.
    :return: Tuple with the parsed configuration and the last file used.
    """
    config = load_yaml(Paths.default_config)
    config_path_used = Paths.default_config

    if config_env_path := os.getenv(config_env):
        config[lookup[0][0]][lookup[0][1]] = config_env_path

    parser = YAMLParser()
    for section, key in lookup:
        if config_path := safeget(config, section, key):
            config_path = Path(config_path)
            if config_path.exists():
                _yaml = parser.read(config_path, {})
                config = merge_dicts(config, _yaml)
                config_path_used = config_path

    config['_session'] = {'config_path_used': config_path_used}
    config['_session']['save_path'] = config_path
    return config


def save_yaml(dictionary: dict, file_path: str|Path,
              dumper: yaml.SafeDumper = yaml.SafeDumper,
              sort_keys: bool = False, **kwargs):
    """Save a dictionary to a YAML file.

    :param dictionary: Dictionary to save.
    :param file_path: Path to the YAML file.
    :param dumper: YAML dumper to use.
    :param mode: Mode to open the file.
    :param sort_keys: Sort the keys of the dictionary.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    dictionary.pop('_session', None)
    yaml_str = yaml.dump(
        dictionary, Dumper=dumper, sort_keys=sort_keys, **kwargs
    )
    file_path.write_text(yaml_str)
