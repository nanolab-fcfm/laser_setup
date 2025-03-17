from omegaconf import OmegaConf

from .defaults import DefaultPaths  # noqa: F401
from .handler import ConfigHandler
from .parameters import ParameterCatalog
from .utils import instantiate, load_yaml, safeget, save_yaml  # noqa: F401

OmegaConf.register_new_resolver(
    "class", lambda x: {'_target_': 'hydra.utils.get_class', 'path': x}
)
OmegaConf.register_new_resolver(
    "function", lambda x: {'_target_': 'hydra.utils.get_method', 'path': x}
)

config = ConfigHandler.load_config()
config.parameters = load_yaml(
    config.Dir.parameters_file, ParameterCatalog, flags={'allow_objects': True}
)
config.procedures = load_yaml(config.Dir.procedures_file, flags={'allow_objects': True})
config.sequences = load_yaml(config.Dir.sequences_file, flags={'allow_objects': True})
