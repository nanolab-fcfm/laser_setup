from .handler import ConfigHandler
from .utils import load_and_merge

from omegaconf import OmegaConf

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
flags = {'allow_objects': True}
load_and_merge(
    CONFIG.Dir.parameters_file, CONFIG, 'parameters', flags=flags
)
load_and_merge(
    CONFIG.Dir.procedures_file, CONFIG, 'procedures', flags=flags
)
load_and_merge(
    CONFIG.Dir.sequences_file, CONFIG, 'sequences', flags=flags
)
load_and_merge(
    CONFIG.Dir.instruments_file, CONFIG, 'instruments', flags=flags
)
