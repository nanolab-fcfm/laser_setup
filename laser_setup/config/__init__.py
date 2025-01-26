from omegaconf import OmegaConf

from .defaults import DefaultPaths  # noqa: F401
from .handler import ConfigHandler
from .utils import instantiate, load_yaml, safeget, save_yaml  # noqa: F401

OmegaConf.register_new_resolver(
    "class", lambda x: {'_target_': 'hydra.utils.get_class', 'path': x}
)
OmegaConf.register_new_resolver(
    "function", lambda x: {'_target_': 'hydra.utils.get_method', 'path': x}
)

config = ConfigHandler.load_config()
