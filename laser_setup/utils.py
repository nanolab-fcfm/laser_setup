import logging
from pathlib import Path
import datetime
from typing import Dict, List, Tuple

import numpy as np
import requests
import pandas as pd

from .config import config

log = logging.getLogger(__name__)

# Songs for the Keithley to play when it's done with a measurement.
SONGS: Dict[str, List[Tuple[float, float]]] = dict(
    washing = [(1318.5102276514797, 0.284375), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1760.0, 0.008125), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1318.5102276514797, 0.008125), (1318.5102276514797, 0.854375), (1318.5102276514797, 0.045625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (2217.4610478149766, 0.015625), (2217.4610478149766, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.284375), (1244.5079348883237, 0.015625), (1244.5079348883237, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.854375), (1318.5102276514797, 0.045625), (1318.5102276514797, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.141875), (2349.31814333926, 0.008125), (2349.31814333926, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1760.0, 0.008125), (1760.0, 0.854375), (1760.0, 0.045625), (1760.0, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.284375), (1760.0, 0.015625), (1760.0, 0.284375), (1760.0, 0.015625), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.854375), (1760.0, 0.045625), (1760.0, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.141875), (1479.9776908465376, 0.008125), (1479.9776908465376, 0.284375), (1479.9776908465376, 0.015625), (1479.9776908465376, 0.141875), (1760.0, 0.008125), (1760.0, 0.141875), (1661.2187903197805, 0.008125), (1661.2187903197805, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.141875), (1760.0, 0.008125), (1760.0, 0.569375), (1318.5102276514797, 0.030625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.284375), (1318.5102276514797, 0.015625), (1318.5102276514797, 0.426875), (1318.5102276514797, 0.023125), (1318.5102276514797, 0.141875), (1975.533205024496, 0.008125), (1975.533205024496, 0.284375), (1661.2187903197805, 0.015625), (1661.2187903197805, 0.284375), (1760.0, 0.015625), (1760.0, 0.854375)],
    triad = [(6/4*1000, 0.25), (5/4*1000, 0.25), (1000, 0.25)],
    A = [(440, 0.2)]
)


def up_down_ramp(v_start: float, v_end: float, v_step: float) -> np.ndarray:
    """This function returns a ramp array with the voltages to be applied
    for a voltage sweep. It goes from v_start to v_end, then to v_start.

    :param v_start: The starting voltage of the sweep
    :param v_end: The ending voltage of the sweep
    :param v_step: The step size of the sweep
    :return: An array with the voltages to be applied
    """
    V_up = np.arange(v_start, v_end, v_step)
    V_down = np.arange(v_end, v_start - v_step, -v_step)
    V = np.concatenate((V_up, V_down))
    return V


def voltage_sweep_ramp(v_start: float, v_end: float, v_step: float) -> np.ndarray:
    """This function returns an array with the voltages to be applied
    for a voltage sweep. It goes from 0 to v_start, then to v_end, then to
    v_start, and finally back to 0.

    :param v_start: The starting voltage of the sweep
    :param v_end: The ending voltage of the sweep
    :param v_step: The step size of the sweep
    :return: An array with the voltages to be applied
    """
    V_m = up_down_ramp(v_start, v_end, v_step)

    direction = 1 if v_start > 0 else -1

    v_i = np.arange(0, v_start, direction * v_step)
    v_f = np.flip(v_i)
    V = np.concatenate((v_i, V_m, v_f))
    return V


def get_data_files(pattern: str = '*.csv') -> List[Path]:
    data_path = Path(config.Dir.data_dir)
    return list(data_path.rglob(pattern))


def remove_empty_data(days: int = 2):
    """This function removes all the empty files in the data folder,
    up to a certain number of days back. Empty files are considered files with
    only the header and no data.
    """
    data = get_data_files()
    try:
        data = [file for file in data if (
            datetime.datetime.now() - sort_by_creation_date(file)[0]
            ).days <= days]
    except:
        pass
    for file in data:
        with open(file, 'r') as f:
            nonheader = [l for l in f.readlines() if not l.startswith('#')]

        if len(nonheader) == 1:
            file.unlink()

    log.info('Empty files removed')


def send_telegram_alert(message: str):
    """Sends a message to all valid Telegram chats on config.Telegram.
    """
    if not (TOKEN := config.Telegram.get('token', None)):
        log.debug("Telegram token not specified in config.")
        return

    chats = [c for c in config.Telegram if c != 'token']
    if len(chats) == 0:
        log.debug("No chats specified in config.")
        return

    try:
        requests.get("http://www.example.com/", timeout=0.5)
    except requests.RequestException:
        log.error("No internet response. Cannot send Telegram message.")
        return

    message = ''.join(['\\' + c if c in "_*[]()~`>#+-=|{}.!" else c for c in message])
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    for chat in chats:
        if chat_id := config.Telegram[chat]:
            params = {'chat_id': chat_id, 'text': message, 'parse_mode': 'MarkdownV2'}

        requests.post(url, params=params)

    log.info(f"Sent '{message}' to {chats}.")


def get_status_message(timeout: float = .5) -> str:
    """Gets a status message from somewhere :)"""
    try:
        res = requests.get("https://api.benbriel.me/nanolab", timeout=timeout)
        message = res.json()['message']
        return message

    except:
        return 'Ready'


def read_file_parameters(file_path: str) -> Dict[str, str]:
    """Reads the parameters from a PyMeasure data file."""
    parameters = {}
    file = Path(file_path).read_text().splitlines()
    for line in file:
        line = line.strip()
        if not line or line.startswith('#Data:'):
            break           # Stop reading after the data starts

        if ':' in line:
            if line.startswith(('#Parameters:', '#Metadata:')):
                continue    # Skip these lines

            key, value = map(str.strip, line.split(':', 1))
            key = key.lstrip('#\t')
            parameters[key] = value
    return parameters


def read_pymeasure(file_path: str, comment='#') -> Tuple[Dict, pd.DataFrame]:
    """Reads the parameters and data from a PyMeasure data file."""
    parameters = read_file_parameters(file_path)
    data = pd.read_csv(file_path, comment=comment)
    return parameters, data


def find_dp(data: Tuple[Dict, pd.DataFrame]) -> float:
    from scipy.signal import find_peaks
    df = data[1]
    R = 1 / df['I (A)']
    peaks, _ = find_peaks(R)
    return df['Vg (V)'][peaks].mean()


def sort_by_creation_date(filename: str) -> List[str]:
    """This function sorts the files found in the given pattern by their
    creation date.

    :param pattern: The pattern to look for files
    :return: A list of file paths sorted by creation date
    """
    filename = Path(filename).name
    date_part, number_part = filename.split('_')
    date = datetime.datetime.strptime(date_part[-10:], '%Y-%m-%d')
    number = int(number_part.split('.')[0])
    return date, number


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
    # Old method: (data = read_pymeasure(file))
    # df = data[1]  # pandas df
    # diff = np.abs(df.diff()["I (A)"].values)
    # indices_smallest_four = np.argpartition(diff, 4)[:4]
    # return round(np.mean(df["Vg (V)"].values[indices_smallest_four]), 2)
    data_total = get_data_files()
    data_sorted = sorted(data_total, key=sort_by_creation_date)
    data_files = [d for d in data_sorted if 'IVg' in str(d)][-1:-max_files-1:-1]
    for file in data_files:
        data = read_pymeasure(file)
        if all(
            data[0]['Chip group name'] == chip_group,
            data[0]['Chip number'] == str(chip_number),
            data[0]['Sample'] == sample
        ):
            DP = find_dp(data)
            log.info(f"Dirac Point found from {file.split('/')[-1]}: {DP} [V]")
            if not isinstance(DP, float) or np.isnan(DP):
                continue

            return DP

    log.warning(
        f"Dirac Point not found for {chip_group} {chip_number} {sample}. (Using DP = 0. instead)"
    )
    return 0.


def rename_data_value(original: str, replace: str):
    """Takes all .csv files in data/**/*.csv, checks for
    headers and replaces all strings matching original with replace
    """
    data_total = get_data_files()
    for file in data_total:
        with open(file, 'r+') as f:
            lines = f.readlines()

            for i, line in enumerate(lines):
                if line.startswith('#'):
                    lines[i] = line.replace(original, replace)

            f.seek(0)
            f.writelines(lines)
            f.truncate()

    log.info(f"Replaced '{original}' with '{replace}' in all data files.")
