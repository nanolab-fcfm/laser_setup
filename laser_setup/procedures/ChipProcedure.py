import logging

from ..utils import get_latest_DP, send_telegram_alert
from .BaseProcedure import BaseProcedure
from .utils import Parameters

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


class LaserMixin:
    """Mixin class for procedures that use the laser_v parameter.
    """
    def patch_parameters(self) -> None:
        if not getattr(self, 'laser_toggle', True):
            self._parameters['laser_v'].value = 0.
            self.laser_v = 0.
        super().patch_parameters()


class VgMixin:
    """Mixin class for procedures that use the vg_dynamic parameter.
    """
    def patch_parameters(self) -> None:
        if getattr(self, 'vg_toggle', True):
            vg = str(self.vg).removesuffix('V')
            if 'DP' in vg:
                latest_DP = get_latest_DP(
                    self.chip_group, self.chip_number, self.sample, max_files=20
                )
                vg = vg.replace('DP', f"{latest_DP:.2f}")

            new_vg = float(eval(vg))
        else:
            new_vg = 0.

        self._parameters['vg'] = Parameters.Control.vg
        self._parameters['vg'].value = new_vg
        self.vg = new_vg
        super().patch_parameters()
