import logging

from .BaseProcedure import BaseProcedure
from .utils import Parameters
from ..utils import send_telegram_alert

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ChipProcedure(BaseProcedure):
    """Base procedure for all device-related measurements. It defines
    parameters that involve a chip.
    """
    # Chip Parameters
    chip_group: str = Parameters.Chip.chip_group
    chip_number: int = Parameters.Chip.chip_number
    sample: str = Parameters.Chip.sample

    INPUTS = BaseProcedure.INPUTS + ['chip_group', 'chip_number', 'sample']

    def shutdown(self):
        if not self.should_stop() and self.status >= self.RUNNING:
            send_telegram_alert(
                f"Finished {type(self).__name__} measurement for Chip "
                f"{self.chip_group} {self.chip_number}, Sample {self.sample}!"
            )

        super().shutdown()
