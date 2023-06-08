import os
import logging
from typing import Dict, List, Tuple

from pymeasure.experiment import get_config
from pymeasure.log import setup_logging

import numpy as np

config = get_config('default_config.ini')

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if 'filename' in config['Logging']:
    os.makedirs(os.path.dirname(config['Logging']['filename']), exist_ok=True)

setup_logging(log, **config['Logging'])

# Songs for the Keithley to play when it's done with a measurement.
SONGS: Dict[str, List[Tuple[float, float]]] = dict(
    washing = [(1318.5102276514797, 0.284375), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1760.0, 0.008125), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1318.5102276514797, 0.008125), (1318.5102276514797, 0.854375), (1318.5102276514797, 0.045625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.284375), (1244.5079348883237, 0.015625), (1244.5079348883237, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.854375), (1318.5102276514797, 0.045625), (1318.5102276514797, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.141875), (2349.31814333926, 0.008125), (2349.31814333926, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.854375), (1760.0, 0.045625), (1760.0, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.854375), (1760.0, 0.045625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.141875), (1760.0, 0.008125), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1760.0, 0.008125), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.854375)],
    ready = [(6/4*1000, 0.25), (5/4*1000, 0.25), (1000, 0.25)],
    A = [(440, 0.2)]
)


def gate_sweep_ramp(vg_start: float, vg_end: float, vg_step: float) -> np.ndarray:
    """This function returns an array with the voltages to be applied to the
    gate for a gate sweep. It goes from 0 to vg_start, then to vg_end, then to
    vg_start, and finally back to 0.

    :param vg_start: The starting voltage of the sweep
    :param vg_end: The ending voltage of the sweep
    :param vg_step: The step size of the sweep
    :return: An array with the voltages to be applied to the gate
    """
    Vg_up = np.arange(vg_start, vg_end, vg_step)
    Vg_down = np.arange(vg_end, vg_start - vg_step, -vg_step)
    Vg_m = np.concatenate((Vg_up, Vg_down))

    vg_start_dir = 1 if vg_start > 0 else -1

    vg_i = np.arange(0, vg_start, vg_start_dir * vg_step)
    vg_f = np.flip(vg_i)
    Vg = np.concatenate((vg_i, Vg_m, vg_f))

    return Vg
