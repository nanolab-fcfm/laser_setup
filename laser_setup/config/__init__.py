from omegaconf import OmegaConf

from .handler import ConfigHandler
from .main import DefaultPaths  # noqa: F401
from .Qt import QtConfig
from .utils import instantiate, load_yaml, safeget, save_yaml  # noqa: F401

OmegaConf.register_new_resolver(
    "class", lambda x: {'_target_': 'hydra.utils.get_class', 'path': x}
)
OmegaConf.register_new_resolver(
    "function", lambda x: {'_target_': 'hydra.utils.get_method', 'path': x}
)

config = ConfigHandler.load_config()
Qt_config = load_yaml(config.Dir.Qt_file, struct=QtConfig)
