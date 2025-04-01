"""Module to parse CLI arguments"""
import argparse
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Protocol, TypeVar, runtime_checkable

from omegaconf import DictConfig, OmegaConf

from . import __version__
from .config import CONFIG, instantiate

log = logging.getLogger(__name__)


@dataclass
class Arguments:
    """Dataclass to hold command line arguments."""
    procedure: str | None = None
    debug: bool = False
    version: str | None = None


def get_parser():
    parser = argparse.ArgumentParser(description='Laser Setup')
    parser.add_argument('procedure', nargs='?', help='Procedure to run',
                        choices={*CONFIG.procedures} | {*CONFIG.scripts})
    parser.add_argument(
        '-v', '--version', action='version', version=f'%(prog)s {__version__}'
    )
    parser.add_argument('-d', '--debug', action='store_true',
                        default=False, help='Enable debug mode')

    return parser


def get_args() -> Arguments:
    """Parse command line arguments and return them as a dataclass."""
    parser = get_parser()
    args, _ = parser.parse_known_args()
    return Arguments(**vars(args))


T = TypeVar('T')
C = TypeVar('C', bound='Configurable')


@runtime_checkable
class Configurable(Protocol):
    """Protocol defining the interface for configurable objects."""

    @classmethod
    def configure_class(cls, config_dict: dict[str, Any]) -> None:
        """Configure class attributes from a dictionary.

        :param config_dict: Dictionary with configuration values
        """
        for key, value in config_dict.items():
            setattr(cls, key, value)

    def configure_instance(self, config_dict: dict[str, Any]) -> None:
        """Configure instance attributes from a dictionary.

        :param config_dict: Dictionary with configuration values
        """
        for key, value in config_dict.items():
            setattr(self, key, value)


def configurable(
    config_key: str,
    on_definition: bool = True,
    subclasses: bool = True,
    instances: bool = False,
    instance_kwargs: bool = True,
    error_ok: bool = False
) -> Callable[[type[C]], type[C]]:
    """Decorator to make a class configurable from the specified configuration key
    in the global configuration.

    This decorator adds configuration capabilities to a class according
    to the specified options.

    :param config_key: Configuration type to load from (e.g., "procedures")
    :param on_definition: Whether to configure the class when it's defined
    :param subclasses: Whether to configure subclasses when they're defined
    :param instances: Whether to apply configuration to instances during __init__.
        Reads the configuration from the `config_dict` keyword argument.
    :param instance_kwargs: Whether to update the keyword arguments in __init__ with
        the corresponding config.
    :param error_ok: Whether to ignore errors when instantiating the configuration
    :return: Class decorator function
    """
    def class_decorator(cls: type[C]) -> type[C]:
        if not hasattr(cls, 'configure_class'):
            cls.configure_class = Configurable.configure_class

        if not hasattr(cls, 'configure_instance'):
            cls.configure_instance = Configurable.configure_instance

        if on_definition:
            config_dict = _get_config_dict(
                config_key, cls.__name__, default={}, error_ok=error_ok
            )
            cls.configure_class(config_dict.copy())

        if subclasses:
            original_init_subclass = cls.__init_subclass__

            @classmethod
            def configurable_init_subclass(klass: type[C], **kwargs):
                original_init_subclass(**kwargs)
                key: str = getattr(klass, '_CONFIG_KEY', None) or \
                    f'{config_key}.{klass.__name__}'

                config_dict = _get_config_dict(
                    key, klass.__name__, default={}, error_ok=error_ok
                )
                klass.configure_class(config_dict.copy())

            cls.__init_subclass__ = configurable_init_subclass

        if instances or instance_kwargs:
            original_init = cls.__init__

            @wraps(original_init)
            def configurable_init(self: C, *args, **kwargs):
                config_dict = kwargs.pop('config_dict', {})
                if instances:
                    self.configure_instance(config_dict)

                if instance_kwargs:
                    config_kwargs = _get_config_dict(
                        config_key, cls.__name__, default={}, error_ok=error_ok
                    )
                    kwargs.update(config_kwargs)

                original_init(self, *args, **kwargs)

            cls.__init__ = configurable_init

        return cls

    return class_decorator


def _get_config_dict(
    config_key: str, class_name: str, default: T = None, error_ok: bool = False
) -> dict | DictConfig | T:
    """Get configuration dictionary for a class.

    :param config_key: Base configuration key
    :param class_name: Name of the class
    :param default: Default value to return if not found
    :param error_ok: Whether to ignore errors during instantiation
    :return: Configuration dictionary
    """
    try:
        return instantiate(OmegaConf.select(CONFIG, config_key, default=default))

    except Exception as e:
        if error_ok:
            log.error(f"Error instantiating config for {class_name}: {e}")
            return default
        raise e
