from omegaconf import OmegaConf

from .defaults import DefaultPaths
from .handler import ConfigHandler
from .parameters import ParameterCatalog
from .utils import get_type, instantiate, load_yaml, safeget, save_yaml

OmegaConf.register_new_resolver(
    "class", lambda x: {'_target_': 'hydra.utils.get_class', 'path': x}
)
OmegaConf.register_new_resolver(
    "function", lambda x: {'_target_': 'hydra.utils.get_method', 'path': x}
)
OmegaConf.register_new_resolver(
    "sequence", lambda x: {
        '_target_': 'laser_setup.config.get_type',
        'name': x,
        'bases': ({
            '_target_': 'hydra.utils.get_class',
            'path': 'laser_setup.procedures.Sequence'
        },),
        'module': 'laser_setup.sequences'
    }
)

CONFIG = ConfigHandler.load_config()
CONFIG.parameters = load_yaml(
    CONFIG.Dir.parameters_file, ParameterCatalog, flags={'allow_objects': True}
)
CONFIG.procedures = load_yaml(CONFIG.Dir.procedures_file, flags={'allow_objects': True})
CONFIG.sequences = load_yaml(CONFIG.Dir.sequences_file, flags={'allow_objects': True})
