import logging

from pymeasure.experiment import Procedure

from ..utils import send_telegram_alert
from ..instruments import InstrumentManager, PendingInstrument
from ..parameters import Parameters, overrides

log = logging.getLogger(__name__)


class BaseProcedure(Procedure):
    """Base procedure for all measurements. It defines basic
    parameters that have to be present in all procedures.
    """
    # Instrument Manager
    instruments = InstrumentManager()

    procedure_version = Parameters.Base.procedure_version
    show_more = Parameters.Base.show_more
    info = Parameters.Base.info

    # Chained Execution
    chained_exec = Parameters.Base.chained_exec
    startup_executed = False

    # Metadata
    start_time = Parameters.Base.start_time

    INPUTS = ['show_more', 'chained_exec', 'info']

    def update_parameters(self):
        """Function to update the parameters after the initialization,
        but before startup. It is useful for creating dynamic parameters that
        depend on others, can only be determined after initialization, or
        change type. At the BaseProcedure level, it sets the parameters
        from the overrides file.
        """
        cls_name = self.__class__.__name__
        lower_params = {key.lower(): key for key in self._parameters.keys()}
        if overrides.has_section(cls_name):
            for key, value in overrides[cls_name].items():
                if key in lower_params:
                    key = lower_params[key]
                    self._parameters[key].value = value
                    setattr(self, key, self._parameters[key].value)

    def connect_instruments(self):
        """Takes all PendingInstruments and connects them to the
        InstrumentManager, replacing the PendingInstrument with the
        connected instrument.
        """
        log.info("Setting up instruments")
        all_attrs = {**self.__class__.__dict__, **self.__dict__}
        for key, instrument in all_attrs.items():
            if isinstance(instrument, PendingInstrument):
                setattr(self, key, self.instruments.connect(**instrument.config))

    def shutdown(self):
        if not self.should_stop() and self.status >= self.RUNNING and self.chained_exec:
            log.info("Skipping shutdown")
            return

        self.instruments.shutdown_all()
        self.__class__.startup_executed = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_parameters()


class ChipProcedure(BaseProcedure):
    """Base procedure for all device-related measurements. It defines
    parameters that involve a chip.
    """
    # Chip Parameters
    chip_group = Parameters.Chip.chip_group
    chip_number = Parameters.Chip.chip_number
    sample = Parameters.Chip.sample

    INPUTS = BaseProcedure.INPUTS + ['chip_group', 'chip_number', 'sample']

    def shutdown(self):
        if not self.should_stop() and self.status >= self.RUNNING:
            send_telegram_alert(
                f"Finished {self.__class__.__name__} measurement for Chip {self.chip_group} {self.chip_number}, Sample {self.sample}!"
            )

            if self.chained_exec:
                log.info("Skipping shutdown")
                return

        self.instruments.shutdown_all()
        self.__class__.startup_executed = False
