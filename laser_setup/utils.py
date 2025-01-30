import datetime
import logging
from pathlib import Path
from typing import Dict, Generator, List, Tuple

import numpy as np
import pandas as pd
import requests

from .config import config

log = logging.getLogger(__name__)


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

    sgn = 1 if v_start > 0 else -1

    v_i = np.arange(0, v_start, sgn * v_step)
    v_f = np.flip(v_i)
    V = np.concatenate((v_i, V_m, v_f))
    return V


def voltage_ds_sweep_ramp(v_start: float, v_end: float, v_step: float) -> np.ndarray:
    """This function returns an array with the voltages to be applied
    for a voltage sweep. It goes from 0 to v_start, then to v_end and finally back to 0.
    If the step size is 1e-6, it will only be applied in the range -1mV to 1mV.
    Otherwise, a step size of 1mV will be used.

    :param v_start: The starting voltage of the sweep
    :param v_end: The ending voltage of the sweep
    :param v_step: The step size of the sweep
    :return: An array with the voltages to be applied
    """
    small_step = v_step
    if 1e-6 <= v_step <= 5e-4:
        # Paso de 1e-6 en el rango de -1mV a 1mV
        large_step = 5e-4  # 0.5mV
    else:
        # Paso de 1mV fuera del rango de -1mV a 1mV
        large_step = v_step

    sgn = 1 if v_start > 0 else -1
    first_v = min(abs(v_start), 5e-4)
    last_v = min(abs(v_end), 5e-4)

    v_i = np.arange(0, sgn * first_v, sgn * small_step)
    v_m1 = np.arange(sgn * first_v, v_start, sgn * large_step)
    v_m2 = np.arange(v_start, sgn * first_v, sgn * -large_step)
    v_m3 = np.arange(sgn * first_v, -sgn * last_v, sgn * -small_step)
    v_m4 = np.arange(-sgn * last_v, v_end, sgn * -large_step)
    v_f1 = np.arange(v_end, -sgn * last_v, sgn * large_step)
    v_f2 = np.arange(-sgn * last_v, 0 + sgn * small_step, sgn * small_step)
    V = np.concatenate((v_i, v_m1, v_m2, v_m3, v_m4, v_f1, v_f2))
    return V


def get_data_files(pattern: str = '*.csv') -> List[Path]:
    data_path = Path(config.Dir.data_dir)
    return list(data_path.rglob(pattern))


def iter_file_lines(
    file: str | Path,
    **kwargs
) -> Generator[str, None, None] | None:
    """Reads a file line by line and yields each line.
    Useful for checks on files with large data.

    :param file: The file to read
    :param kwargs: Additional arguments for the open function
    :return: A generator with the lines of the file
    """
    file_path = Path(file)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file}")

    with file_path.open(mode='r', **kwargs) as f:
        for line in f:
            yield line


def remove_empty_data(days: int = 2):
    """This function removes all the empty files in the data folder,
    up to a certain number of days back. Empty files are considered files with
    only the header and no data.
    """
    data = get_data_files()
    data = [file for file in data if (
        datetime.datetime.now() - extract_date_and_number(file)[0]
        ).days <= days]

    at_least_one = False
    for file in data:
        nonheader_count = 0
        for line in iter_file_lines(file):
            if not line.startswith('#'):
                nonheader_count += 1

            if nonheader_count > 1:
                break

        if nonheader_count <= 1:
            at_least_one = True
            file.unlink()
            log.debug(f"Removed empty file: {file}")

    for directory in Path(config.Dir.data_dir).rglob('*'):
        if directory.is_dir() and not list(directory.iterdir()):
            directory.rmdir()
            log.debug(f"Removed empty directory: {directory}")

    if at_least_one:
        log.info('Empty files removed')


def send_telegram_alert(message: str):
    """Sends a message to all valid Telegram chats on config.Telegram.
    """
    if not (TOKEN := config.Telegram.get('token', None)):
        log.debug("Telegram token not specified in config.")
        return

    if len(config.Telegram.chat_ids) == 0:
        log.debug("No chats specified in config.")
        return

    try:
        requests.get("http://www.example.com/", timeout=0.5)
    except requests.RequestException:
        log.error("No internet response. Cannot send Telegram message.")
        return

    message = ''.join(['\\' + c if c in "_*[]()~`>#+-=|{}.!" else c for c in message])
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    for chat_id in config.Telegram.chat_ids:
        params = {'chat_id': chat_id, 'text': message, 'parse_mode': 'MarkdownV2'}

        requests.post(url, params=params)

    log.debug(f"Sent '{message}' to {config.Telegram.chat_ids}.")


def get_status_message(timeout: float = .5) -> str:
    """Gets a status message from somewhere :)"""
    try:
        res = requests.get("https://api.benbriel.me/nanolab", timeout=timeout)
        message = res.json()['message']
        return message

    except (requests.RequestException, KeyError):
        return 'Ready'


def read_file_parameters(file_path: str | Path) -> Dict[str, str]:
    """Reads the parameters from a PyMeasure data file."""
    parameters = {}
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    for line in iter_file_lines(file_path):
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


def find_dp(df: pd.DataFrame) -> float:
    """Finds the Dirac Point from an IVg measurement."""
    from scipy.signal import find_peaks
    R = 1 / df['I (A)']
    peaks, _ = find_peaks(R)
    return df['Vg (V)'][peaks].mean()


def extract_date_and_number(filename: str | Path) -> tuple[datetime.datetime, int]:
    """Extracts the date and number from a file name.

    :param filename: The file name to sort
    :return: A tuple with the date and number of the file
    """
    filename = Path(filename).name
    date_part, number_part = filename.split('_')
    date = datetime.datetime.strptime(date_part[-10:], '%Y-%m-%d')
    number = int(number_part.split('.')[0])
    return date, number


def get_latest_DP(chip_group: str, chip_number: int | str, sample: str, max_files=1) -> float:
    """This function returns the latest Dirac Point found for the specified
    chip group, chip number and sample. This is based on IVg measurements.

    :param chip_group: The chip group name
    :param chip_number: The chip number
    :param sample: The sample name
    :param max_files: The maximum number of files to look for, starting from the
    latest one.
    :return: The latest Dirac Point found
    """
    data_total = get_data_files()
    data_sorted: list[Path] = sorted(data_total, key=extract_date_and_number)
    data_files: list[Path] = [d for d in data_sorted if 'IVg' in str(d.stem)][-1:-max_files-1:-1]
    for file in data_files:
        params, data = read_pymeasure(file)
        if all((
            params['Chip group name'] == chip_group,
            params['Chip number'] == str(chip_number),
            params['Sample'] == sample
        )):
            DP = find_dp(data)
            if not isinstance(DP, float) or np.isnan(DP):
                continue

            log.info(
                f"Dirac Point found for {chip_group} {chip_number} {sample} "
                f"in {file.name}: {DP:.2f} [V]"
            )
            return DP

    log.warning(
        f"Dirac Point not found for {chip_group} {chip_number} {sample}. (Using DP = 0. instead)"
    )
    return 0.


def rename_data_value(original: str, replace: str) -> None:
    """Takes all .csv files in data/**/*.csv, checks for
    headers and replaces all strings matching original with replace

    :param original: The string to replace
    :param replace: The string to replace with
    """
    data_total = get_data_files()
    for file in data_total:
        with file.open('r+') as f:
            lines = f.readlines()

            for i, line in enumerate(lines):
                if line.startswith('#'):
                    lines[i] = line.replace(original, replace)

            f.seek(0)
            f.writelines(lines)
            f.truncate()

    log.info(f"Replaced '{original}' with '{replace}' in all data files.")
