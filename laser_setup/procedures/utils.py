from copy import deepcopy

from omegaconf import DictConfig

from ..config import CONFIG, instantiate


class DeepCopyDictConfig(DictConfig):
    """Deepcopy of the DictConfig class. It allows to deepcopy the
    parameters when they are accessed.
    """
    def __getitem__(self, key):
        item = super().__getitem__(key)
        if isinstance(item, DictConfig):
            return DeepCopyDictConfig(item)
        return deepcopy(item)

    def __getattr__(self, key):
        item = super().__getattr__(key)
        if isinstance(item, DictConfig):
            return DeepCopyDictConfig(item)
        return deepcopy(item)


Instruments = instantiate(CONFIG.instruments)
Parameters = DeepCopyDictConfig(instantiate(CONFIG.parameters))
