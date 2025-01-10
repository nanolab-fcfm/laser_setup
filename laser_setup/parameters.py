"""Module for setting up the parameters for the laser setup.
Parameters should be defined here and imported in the procedures.
"""
import copy
from typing import TypeVar

import yaml
from pymeasure.experiment import IntegerParameter, Parameter, BooleanParameter, ListParameter, FloatParameter, Metadata

from . import config
from .parser import YAMLParser

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


class ParameterParser(YAMLParser):
    """Class to parse parameters from a YAML file."""
    tag_dict = {
        '!Parameter': Parameter,
        '!BooleanParameter': BooleanParameter,
        '!IntegerParameter': IntegerParameter,
        '!FloatParameter': FloatParameter,
        '!ListParameter': ListParameter,
        '!Metadata': Metadata
    }

    @staticmethod
    def get_constructor(
        param_cls: type[AnyParameter],
        loader: type[yaml.SafeLoader],
        node: yaml.nodes.MappingNode
    ) -> Parameter:
        data: dict = loader.construct_mapping(node, deep=True)
        data.pop('description', None)   # description not implemented yet

        return param_cls(**data)


parser = ParameterParser()
Parameters = ParameterProvider(**parser.read(config['General']['parameters_file'], {}))

procedure_config = parser.read(config['General']['procedure_config_file'], {})
