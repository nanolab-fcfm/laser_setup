"""Module to parse configuration files"""
import yaml
from pathlib import Path
from functools import partial
from collections.abc import Mapping

default_config_path = Path(__file__).parent / 'default_config.yml'


class YAMLParser:
    """Class to parse a dictionary from a YAML file with optional custom tags."""
    loader = yaml.SafeLoader
    tag_dict: dict = {}

    def get_loader(self) -> type[yaml.SafeLoader]:
        """Returns a YAML loader with custom constructors for defined tags."""
        for tag, cls in self.tag_dict.items():
            self.loader.add_constructor(tag, partial(self.get_constructor, cls))
        return self.loader

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


def load_yaml(file_path: str|Path, Loader: yaml.SafeLoader = yaml.SafeLoader) -> dict:
    """Load a YAML file and return its contents as a dictionary.

    :param file_path: Path to the YAML file.
    :return: Dictionary with the contents of the YAML file.
    """
    with open(file_path, 'r') as file:
        return yaml.load(file, Loader=Loader)


def load_config(
    keys: list[str] = ['global_config_file', 'local_config_file']
) -> tuple[dict, Path]:
    """Load the configuration files appropiately. By default, it loads the
    files in the following order:
    1. Default configuration file.
    2. Global configuration file (if it exists), with its path defined in the
    default config.
    3. Local configuration file (if it exists), with its path defined in the
    global config.

    :keys list[str]: List of keys to look for in the configuration
    :return: Tuple with the parsed configuration and the last file used.
    """
    config = load_yaml(default_config_path)
    config_file_used = default_config_path

    for config_key in keys:
        config_path = config.get('General', {}).get(config_key)
        if config_path:
            config_path = Path(config_path)
            if config_path.exists():
                config = merge_dicts(config, load_yaml(config_path))
                config_file_used = config_path

    return config, config_file_used


def save_yaml(
    dictionary: dict,
    file_path: str|Path,
    dumper: yaml.SafeDumper = yaml.SafeDumper,
    mode: str = 'w',
    sort_keys: bool = False,
    **kwargs
):
    """Save a dictionary to a YAML file.

    :param dictionary: Dictionary to save.
    :param file_path: Path to the YAML file.
    :param dumper: YAML dumper to use.
    :param mode: Mode to open the file.
    :param sort_keys: Sort the keys of the dictionary.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, mode) as file:
        yaml.dump(dictionary, file, Dumper=dumper, sort_keys=sort_keys, **kwargs)
