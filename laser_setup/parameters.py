"""Module for setting up the parameters for the laser setup.
Parameters should be defined here and imported in the procedures.
"""
import copy
import time
import configparser
from pathlib import Path
from functools import partial
from typing import TypeVar

import yaml
from pymeasure.experiment import IntegerParameter, Parameter, BooleanParameter, ListParameter, FloatParameter, Metadata

from . import config
from .parser import load_yaml

AnyParameter = TypeVar('AnyParameter', bound=Parameter)


class ParameterProvider:
    """Base class for Parameters objects. When a parameter is
    accessed, a copy of the parameter is returned to avoid
    modifying the original parameter.
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, dict):
                v = ParameterProvider(**v)

            setattr(self, k.replace(' ', '_'), v)

    def __getattribute__(self, name):
        attr = super().__getattribute__(name)

        # Check if the attribute is a Parameter or Metadata instance
        if isinstance(attr, (Parameter, Metadata)):
            return copy.deepcopy(attr)

        return attr

    def __getitem__(self, name: str):
        return getattr(self, name.replace(' ', '_'))

    def __setitem__(self, name: str, value: any):
        setattr(self, name, value)


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


parser = ParameterParser()
Parameters = ParameterProvider(**parser.read('laser_setup/parameters.yml'))
# Parameters = parser.read(config.get('General', 'parameter_file'))
breakpoint()