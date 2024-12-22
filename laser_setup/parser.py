"""Module to parse configuration files"""
import yaml
from pathlib import Path
from functools import partial
from typing import TypeVar

from pymeasure.experiment import Parameter, FloatParameter, IntegerParameter, BooleanParameter, ListParameter, Metadata

AnyParameter = TypeVar('AnyParameter', bound=Parameter)

default_config_path = Path(__file__).parent / 'default_config.yml'


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
                config.update(load_yaml(config_path))
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


class ParameterParser:
    """Class to parse parameters from a YAML file."""
    parameter_tag = '!Parameter'
    bool_tag = '!BooleanParameter'
    int_tag = '!IntegerParameter'
    float_tag = '!FloatParameter'
    list_tag = '!ListParameter'
    metadata_tag = '!Metadata'

    def get_loader(self):
        """Returns a YAML loader with the custom constructors."""
        loader = yaml.SafeLoader
        loader.add_constructor(self.parameter_tag, partial(self.parameter_constructor, Parameter))
        loader.add_constructor(self.bool_tag, partial(self.parameter_constructor, BooleanParameter))
        loader.add_constructor(self.int_tag, partial(self.parameter_constructor, IntegerParameter))
        loader.add_constructor(self.float_tag, partial(self.parameter_constructor, FloatParameter))
        loader.add_constructor(self.list_tag, partial(self.parameter_constructor, ListParameter))
        loader.add_constructor(self.metadata_tag, partial(self.parameter_constructor, Metadata))

        return loader

    @staticmethod
    def parameter_constructor(
        param_cls: type[AnyParameter],
        loader: yaml.SafeLoader,
        node: yaml.nodes.MappingNode
    ) -> Parameter:
        data = loader.construct_mapping(node, deep=True)
        data.pop('description', None)   # description not implemented yet
        data.pop('hidden', None)        # hidden not implemented yet

        return param_cls(**data)

    def read(self, file_path: str|Path) -> dict:
        """Read a YAML file with parameters and return them as a dictionary.

        :param file_path: Path to the YAML file with the parameters.
        :return: Dictionary with the parameters.
        """
        loader = self.get_loader()
        return load_yaml(file_path, loader)


if __name__ == '__main__':
    parser = ParameterParser()
    parameters = parser.read('config/parameters.yml')
    print(parameters)
    breakpoint()