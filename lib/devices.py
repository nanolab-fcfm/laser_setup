"""
Module that includes the K2450 class to communicate with the Keithleys,
as well as some functions that make voltage sequences for the Keithleys.
"""
from dataclasses import dataclass
import pyvisa
import numpy as np

@dataclass
class K2450:
    rm: pyvisa.ResourceManager = pyvisa.ResourceManager()

    def __init__(self, r: str):
        self.resource = r
        self.instrument = self.rm.open_resource(self.resource)
        self.digital_in = None
        self.digital_out = None

    def write(self, cmd: str):
        return self.instrument.write(cmd)

    def query(self, query: str):
        return self.instrument.query(query)

    def reset(self):
        self.write("*RST")

    def sense_curr(self):
        self.write("SENS:FUNC \"CURR\"")

    def sense_curr_range_auto(self, value: bool):
        table = {0: 'OFF', 1: 'ON'}
        self.write(f"SENS:CURR:RANG:AUTO {table[value]}")

    def curr_limit(self, limit: float):
        """
        This funtion sets the current limit
        :param limit: current limit in A
        :return: None
        """
        self.write(f"SOUR:VOLT:ILIM {limit}")

    def source_volt(self):
        self.write("SOUR:FUNC VOLT")

    def set_volt_range(self, range_: float):
        self.write(f"SOUR:VOLT:RANG {range_}")

    def cre_sour_conf(self, name: str):
        """
        This function creates a source configuration list with the given name
        :param name: name of the list
        :return: None
        """
        self.write(f"SOUR:CONF:LIST:CRE \"{name}\"")

    def sense_curr_nplc(self, nplc_value: int):
        self.write(f"SENS:CURR:NPLC {int(nplc_value)}")

    def set_in_out_digital_pin(self, in_: int, out_: int):
        assert isinstance(in_, int) and isinstance(out_, int)

        self.write(f"DIG:LINE{out_}:MODE TRIG, OUT")
        self.write(f"DIG:LINE{in_}:MODE TRIG, IN")  # set digital line n to input
        self.write(f"TRIG:DIG{out_}:OUT:STIM NOT{out_}")
        self.write(f"TRIG:DIG{in_}:IN:CLE")  # clear digital in
        self.write(f"TRIG:DIG{in_}:IN:EDGE RIS")  # set to detect edge rise

    def set_volt(self, voltage: float):
        self.write(f"SOUR:VOLT {voltage}")

    def add_voltage_to_configuration_list(self, voltage: float, list_name: str):
        self.set_volt(voltage)
        self.write(f"SOUR:CONF:LIST:STORE \"{list_name}\"")

@dataclass
class TENMA:
    arg = 'test'
    def __init__(self) -> None:
        pass


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
