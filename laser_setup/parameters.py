"""Module for setting up the parameters for the laser setup.
Parameters should be defined here and imported in the procedures.
"""
from copy import deepcopy

from omegaconf import DictConfig

from .config import config, load_yaml
from .config.parameters import ParameterCatalog


class DeepCopyDictConfig(DictConfig):
    """Deepcopy of the DictConfig class. It allows to deepcopy the
    parameters when they are accessed.
    """
    def __getitem__(self, key):
        item = super().__getitem__(key)
        return deepcopy(item)

    def __getattr__(self, key):
        item = super().__getattr__(key)
        return deepcopy(item)


class ParametersMeta(type):
    """Metaclass for Parameters. It is used to set attributes
    and the default `Parameters` sections in the class definition.
    """
    def __new__(cls: type, name: str, bases: tuple, dct: dict):
        for key, value in dct['_dict'].items():
            if key.startswith('_'):
                continue

            dct[key] = DeepCopyDictConfig(value)

        return super().__new__(cls, name, bases, dct)


class Parameters(ParameterCatalog, metaclass=ParametersMeta):
    """Parameter catalog. Returns a deepcopy of the parameter when accessed.
    """
    # There's probably a better way to do this, but at least it works.
    _dict = load_yaml(
        config.Dir.parameters_file,
        ParameterCatalog,
        flags={'allow_objects': True},
        _instantiate=True
    )
