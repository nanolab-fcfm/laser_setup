"""
Module that includes the K2450 class to communicate with the Keithleys,
as well as some functions that make voltage sequences for the Keithleys.
"""
import numpy as np

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import truncated_range, strict_discrete_set


class TENMA(Instrument):
    """
    This class implements the communication with the TENMA sources. It is
    based on the pymeasure library. It is a subclass of the Instrument class
    from pymeasure.
    """
    current = Instrument.control(
        "ISET1?", "ISET1:%g", """Sets the current in Amps.""",
        validator=truncated_range,
        values=[0, 1]
    ) # TODO: check if ISET1? is correct

    voltage = Instrument.control(
        "VSET1?", "VSET1:%g", """Sets the voltage in Volts.""",
        validator=truncated_range,
        values=[-60., 60.]
    ) # TODO: check if VSET1? is correct

    output = Instrument.control(
        "OUT1?", "OUT1:%d", """Sets the output state.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    ) # TODO: check if OUT1? is correct

    timeout = Instrument.control(
        "Timeout?", "Timeout %d", """Sets the timeout in seconds."""
    ) # TODO: check if Timeout? is correct
    
    def __init__(self, adapter, **kwargs):
        super(TENMA, self).__init__(
            adapter, "TENMA Power Supply", **kwargs
        )


def vg_ramp(vg_start: float, vg_end: float, vg_step: float) -> np.ndarray:
    """
    This function makes the vg ramp for an IV measurement.
    It goes from 0 to vg_start, then to vg_end, then to vg_start, and finally
    back to 0.
    """
    Vg_up = np.arange(vg_start, vg_end, vg_step)
    Vg_down = np.arange(vg_end, vg_start - vg_step, -vg_step)
    Vg_m = np.concatenate((Vg_up, Vg_down))

    vg_start_dir = 1 if vg_start > 0 else -1

    vg_i = np.arange(0, vg_start, vg_start_dir * vg_step)
    vg_f = np.flip(vg_i)
    Vg = np.concatenate((vg_i, Vg_m, vg_f))

    return Vg


def time_to_steps(s, NPLC=0.02):
    """Simple function that converts seconds to NPLC and uses that
    to return the steps

    Args:
        s (float): seconds to converto to steps
        NPLC (float, optional): Is the NPLC of the machine. Defaults to 0.02.

    Returns:
        int: steps to acomplish the time required
    """
    return int(s / NPLC)


def ramps_vds(vds, alpha):
    """This function makes the ramps from 0 to the desired vds (and vds to 0) taking into account
    the slope and returns two arrays with that information

    Args:
        vds (float): vds we want to reach
        alpha (float): slope in [V/s] that we must meet

    Returns:
        tuple: a tuple with one array for the ramp up and ramp down respectively
    """
    
    delta_v = vds
    delta_t = delta_v / alpha
    steps_ramp = time_to_steps(delta_t)
    ramp_up = np.linspace(0, vds, steps_ramp)
    ramp_down = np.flip(ramp_up)
    
    return ramp_up, ramp_down


def make_ramps(list_points, alpha):
    delta_vs = [list_points[i + 1] - list_points[i] for i in range(len(list_points) - 1)] 
    delta_t = [dv / alpha for dv in delta_vs]
    steps_t = [np.abs(time_to_steps(s)) for s in delta_t]
    starts = list_points[:-1]
    ends = list_points[1:]
    ramps = [np.linspace(starts[i], ends[i], steps_t[i]) for i in range(len(list_points) - 1)]
    return ramps


def vg_sequence(list_of_vgs, vds, time_on, alpha):
    """This function generates the sequence of voltages for the gate

    Args:
        list_of_vgs (list of floats): voltages for the vg
        vds (float): vds to use
        time_on (float): time in seconds to stay on
        alpha (float): slope in [V/s]

    Returns:
        np.array: array with the values to source the gate
    """
    steps_on = time_to_steps(time_on)    
    list_of_vgs.sort()  # we sort the vg's
    new_vg_list = list_of_vgs + [0]
    sequences_on = [np.linspace(v, v, steps_on - 2) for v in new_vg_list]  # the -2 accounts for the overlap with the ramps
    list_for_ramps = [0] + new_vg_list  # it starts in 0 and ends in 0
    ramps = make_ramps(list_for_ramps, alpha)
    assert len(ramps) == len(sequences_on)
    sequence = []
    for i in range(len(ramps)):
        sequence.append(ramps[i])
        sequence.append(sequences_on[i])
    
    sequence = sequence[:-1]
    
    ramp_up_vds, ramp_down_vds = ramps_vds(vds, alpha)
    sequence = [ramp_up_vds * 0] + sequence + [ramp_down_vds * 0]
    np_sequence = np.concatenate(sequence)
    return np_sequence


def vds_sequence(vds, alpha, v_gate_sequence):

    ramp_up, ramp_down = ramps_vds(vds, alpha)
    n = len(v_gate_sequence) - 2 * len(ramp_up)
    on_sequence = np.linspace(vds, vds, n)
    sequence_list = [ramp_up, on_sequence, ramp_down]
    return np.concatenate(sequence_list)


def parse_data(array: list[str]) -> np.ndarray:
    array = array.replace("\n", "")
    array = array.split(",")
    return np.array(array, dtype=float)


def v_g_voltages_no_negatives(v_g, steps_up):
    prime_array = np.linspace(0, v_g, steps_up)
    arrays = [
        prime_array,
        np.flip(prime_array)[1:]
    ]
    return np.concatenate(arrays)

def v_g_voltages(v_g, steps_up):
    prime_array = np.linspace(0, v_g, steps_up)
    arrays = [
        prime_array,
        np.flip(prime_array)[1:-1],
        -prime_array[:-1],
        -np.flip(prime_array),
        prime_array[1:-1],
        np.flip(prime_array)
    ]
    return np.concatenate(arrays)
