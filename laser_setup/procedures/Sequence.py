import logging
from collections.abc import MutableMapping
from typing import Any, ClassVar

from pymeasure.experiment import Procedure

from ..config import CONFIG, instantiate
from ..parser import configurable
from ..patches import Status

log = logging.getLogger(__name__)


@configurable('sequences', on_definition=False)
class Sequence:
    """Provides the base class for procedure sequences.

    A sequence defines a series of procedures that should be executed
    together. It can be used to group procedures that are commonly run
    together, or to define a specific measurement routine.

    :param name: Display name of the sequence
    :param description: Description of the sequence
    :param common_procedure: Procedure type to use as base for all procedures
    :param abort_timeout: Seconds to wait after abort before continuing
    :param inputs_ignored: Parameters from common_procedure to exclude
    :param procedures: List of procedures to include in the sequence, as
        procedure names, classes or configurations
    """
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    common_procedure: ClassVar[type[Procedure]] = Procedure
    inputs_ignored: ClassVar[list[str]] = []
    procedures: list[type[Procedure]] = []
    procedures_config: list[MutableMapping[str, Any]] = []
    queue: list[Procedure] = []

    def __init__(self, **kwargs):
        """Initialize a sequence instance.

        :param parameters: Dictionary of procedure-specific parameters
        :param kwargs: Additional configuration attributes
        """
        self.status = Status.QUEUED
        self._queue_procedures()

    @classmethod
    def configure_class(cls, config_dict: MutableMapping[str, Any]):
        procedures: list = config_dict.pop('procedures', {})
        cls.procedures = []
        for item in procedures:
            if isinstance(item, MutableMapping):
                for proc_name, proc_params in item.items():
                    cls.add_procedure(proc_name, proc_params)

            elif (isinstance(item, type) and issubclass(item, Procedure)) or isinstance(item, str):
                cls.add_procedure(item, None)

        for key, value in config_dict.items():
            setattr(cls, key, value)

    @classmethod
    def add_procedure(
        cls,
        procedure: str | type[Procedure],
        procedure_config: MutableMapping[str, Any] | None = None,
        types_dict: dict[str, type[Procedure]] = instantiate(CONFIG.procedures._types)
    ) -> None:
        """Process a procedure item and add it to the sequence.

        :param procedure: Procedure name, class or configuration
        :param procedure_config: Configuration for the procedure
        :param types_dict: Dictionary mapping procedure names to classes.
            Default is the procedures dictionary from the config.
        """
        if isinstance(procedure, str):
            if procedure not in types_dict:
                log.warning(f"Procedure {procedure} not found in types dict. Skipping.")
                return

            procedure_class = types_dict[procedure]

            if not (isinstance(procedure_class, type) and issubclass(procedure_class, Procedure)):
                log.warning(
                    f"Value types_dict['{procedure}'] is not a subclass of Procedure. Skipping."
                )
                return

        elif issubclass(procedure, Procedure):
            procedure_class = procedure

        else:
            log.error(f"Invalid procedure type: {procedure}")
            return

        cls.procedures.append(procedure_class)
        cls.procedures_config.append(procedure_config or {})

    def _queue_procedures(self):
        """Queue all procedures in the sequence."""
        for proc_class, proc_config in zip(self.procedures, self.procedures_config):
            procedure = proc_class(**proc_config)
            self.queue.append(procedure)

    def __contains__(self, item):
        return item in self.queue

    def __iter__(self):
        return iter(self.queue)

    def __len__(self):
        return len(self.queue)

    def __repr__(self) -> str:
        return f"<Sequence {self.name} ({len(self)} procedures queued)>"

    def __str__(self) -> str:
        return self.name
