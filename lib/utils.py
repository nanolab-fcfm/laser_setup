from typing import Dict, List, Tuple
from glob import glob
import logging
import os

import numpy as np
import requests
import pandas as pd
from scipy.signal import find_peaks

from lib import config

log = logging.getLogger(__name__)

# Songs for the Keithley to play when it's done with a measurement.
SONGS: Dict[str, List[Tuple[float, float]]] = dict(
    washing = [(1318.5102276514797, 0.284375), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1760.0, 0.008125), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1318.5102276514797, 0.008125), (1318.5102276514797, 0.854375), (1318.5102276514797, 0.045625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.284375), (1244.5079348883237, 0.015625), (1244.5079348883237, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.854375), (1318.5102276514797, 0.045625), (1318.5102276514797, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.141875), (2349.31814333926, 0.008125), (2349.31814333926, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.854375), (1760.0, 0.045625), (1760.0, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.854375), (1760.0, 0.045625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.141875), (1760.0, 0.008125), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1760.0, 0.008125), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.854375)],
    triad = [(6/4*1000, 0.25), (5/4*1000, 0.25), (1000, 0.25)],
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

def iv_ramp(vsd_start: float, vsd_end: float, vsd_step: float) -> np.ndarray:
    """This function returns an array with the voltages to be applied to the
    source drain for a IV sweep. It goes from 0 to vg_start, then to vg_end, then to
    vg_start, and finally back to 0.

    :param vsd_start: The starting voltage of the sweep
    :param vsd_end: The ending voltage of the sweep
    :param vsd_step: The step size of the sweep
    :return: An array with the voltages to be applied to the gate
    """
    Vsd_up = np.arange(vsd_start, vsd_end, vsd_step)
    Vsd_down = np.arange(vsd_end, vsd_start - vsd_step, -vsd_step)
    Vsd_m = np.concatenate((Vsd_up, Vsd_down))

    vsd_start_dir = 1 if vsd_start > 0 else -1

    vsd_i = np.arange(0, vsd_start, vsd_start_dir * vsd_step)
    vsd_f = np.flip(vsd_i)
    Vsd = np.concatenate((vsd_i, Vsd_m, vsd_f))

    return Vsd


def remove_empty_data():
    """This function removes all the empty files in the data folder.
    By empty files we mean files with only the header and no data.
    """
    DataDir = config['Filename']['directory']
    data = glob(DataDir + '/**/*.csv', recursive=True)
    for file in data:
        with open(file, 'r') as f:
            nonheader = [l for l in f.readlines() if not l.startswith('#')]

        if len(nonheader) == 1:
            os.remove(file)
    
    log.info('Empty files removed')


def send_telegram_alert(message: str):
    """Sends a message to all valid Telegram chats on config['Telegram'].
    """
    try:
        requests.get("https://www.google.com/", timeout=1)

    except:
        log.error("No internet connection. Cannot send Telegram message.")
        return
    
    if 'TOKEN' not in config['Telegram']:
        log.error("Telegram token not specified in config.")
        return

    TOKEN = config['Telegram']['token']

    chats = [c for c in config['Telegram'] if c != 'token']
    if len(chats) == 0:
        log.error("No chats specified in config.")
        return
    
    message = ''.join(['\\' + c if c in "_*[]()~`>#+-=|{}.!" else c for c in message])
    
    for chat in chats:
        chat_id = config['Telegram'][chat]
        params = dict(
            chat_id = chat_id,
            text = message,
            parse_mode = 'MarkdownV2'
        )

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, params=params)
        log.info(f"Sent '{message}' to {chat}.")


def read_pymeasure(file_path):
    data = pd.read_csv(file_path, comment="#")
    parameters = {}
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('#Parameters:'):
                break
        for line in file:
            line = line.strip()
            if not line or line.startswith('#Data:'):
                break
            if ':' in line:
                key, value = map(str.strip, line.split(':', 1))
                key = key.lstrip('#\t')
                parameters[key] = value
    return parameters, data


def find_dp(data: Tuple[Dict, pd.DataFrame]) -> float:
    df = data[1]
    R = 1 / df['I (A)']
    peaks, _ = find_peaks(R)
    return df['Vg (V)'][peaks].mean()


def get_latest_DP(chip_group: str, chip_number: int, sample: str, max_files=1) -> float:
    """This function returns the latest Dirac Point found for the specified
    chip group, chip number and sample. This is based on IVg measurements.

    :param chip_group: The chip group name
    :param chip_number: The chip number
    :param sample: The sample name
    :param max_files: The maximum number of files to look for, starting from the
    latest one.
    :return: The latest Dirac Point found
    """
    DataDir = config['Filename']['directory']
    data_total = glob(DataDir + '/**/*.csv', recursive=True)
    data_files = [d for d in data_total if 'IVg' in d][-1:-max_files-1:-1]
    for file in data_files:
        data = read_pymeasure(file)
        if data[0]['Chip group name'] == chip_group and data[0]['Chip number'] == str(chip_number) and data[0]['Sample'] == sample:
            DP =  find_dp(data)
            log.info(f"Dirac Point found from {file.split('/')[-1]}: {DP} [V]")
            if not isinstance(DP, float) or np.isnan(DP):
                continue

            return DP
    
    log.error(f"Dirac Point not found for {chip_group} {chip_number} {sample}")
    raise ValueError("Dirac Point not found")
    
    