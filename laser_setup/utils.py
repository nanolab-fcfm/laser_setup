from typing import Dict, List, Tuple
from glob import glob
import datetime
import logging
import os

import numpy as np
import requests
import pandas as pd
from scipy.stats import linregress
from scipy.signal import find_peaks

from . import config

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


def remove_empty_data(days: int = 2):
    """This function removes all the empty files in the data folder,
    up to a certain number of days back. Empty files are considered files with
    only the header and no data.
    """
    DataDir = config['Filename']['directory']
    data = glob(DataDir + '/**/*.csv', recursive=True)
    try:
        data = [file for file in data if (datetime.datetime.now() - sort_by_creation_date(file)[0]).days <= days]
    except:
        pass
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
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#Data:'):
                break           # Stop reading after the data starts

            if ':' in line:
                if any(map(line.startswith, ('#Parameters:', '#Metadata:'))):
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
    filename = os.path.basename(filename)
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
    DataDir = config['Filename']['directory']
    data_total = glob(DataDir + '/**/*.csv', recursive=True)
    data_sorted = sorted(data_total, key=sort_by_creation_date)
    data_files = [d for d in data_sorted if 'IVg' in d][-1:-max_files-1:-1]
    for file in data_files:
        data = read_pymeasure(file)
        if data[0]['Chip group name'] == chip_group and data[0]['Chip number'] == str(chip_number) and data[0]['Sample'] == sample:
            DP =  find_dp(data)
            log.info(f"Dirac Point found from {file.split('/')[-1]}: {DP} [V]")
            if not isinstance(DP, float) or np.isnan(DP):
                continue

            return DP

    log.warning(f"Dirac Point not found for {chip_group} {chip_number} {sample}. (Using DP = 0. instead)")
    return 0.


def rename_data_value(original: str, replace: str):
    """Takes all .csv files in data/**/*.csv, checks for
    headers and replaces all strings matching original with replace
    """
    DataDir = config['Filename']['directory']
    data_total = glob(DataDir + '/**/*.csv', recursive=True)
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


####################################################################################################
# Old functions, to be removed
####################################################################################################


def get_timestamp(file):
    return float(read_pymeasure(file)[0]['Start time'])


def sort_by_creation_date_calibration(pattern):
    # Get a list of file paths that match the specified pattern
    file_paths = glob(pattern)

    # exclude calibration files
    file_paths = [path for path in file_paths if "Calibration" not in path]

    # Sort the file paths based on their creation date
    sorted_file_paths = sorted(file_paths, key=get_timestamp)

    return sorted_file_paths


def find_Miguel(day_of_data):
    indices_out = []
    for i, data in enumerate(day_of_data):
        if (data[0]['Chip group name'] == "Miguel") and (data[0]['Chip number'] == "8") and (data[0]['Sample'] == "A"):
            indices_out.append(i)
    return indices_out


def experiment_type(experiment):
    if 'VG end' in experiment[0]:
        return "Vg"
    return "It"


def find_NN_points(data, vg):
    df = data.copy()
    df["Vg (V)"] -= vg
    df.sort_values(by='Vg (V)', inplace=True)
    nearest_left = df[df['Vg (V)'] <= 0].iloc[-1]
    nearest_right = df[df['Vg (V)'] >= 0].iloc[0]
    return nearest_left['Vg (V)'], nearest_right['Vg (V)'], nearest_left['I (A)'], nearest_right['I (A)']


def interpolate_df(data, vg):
    df = data.copy()
    df["Vg (V)"] -= vg
    x_1, x_2, y_1, y_2 = find_NN_points(data, vg)

    return y_2 - x_2 * (y_2 - y_1) / (x_2 - x_1)


def increment_numbers(input_list):
    current_number = input_list[0]
    counter = 1
    output_list = []

    for num in input_list:
        if num != current_number:
            current_number = num
            counter += 1
        output_list.append(counter)

    return output_list


def divide_inyective(data):
    chunks = np.sign(data.values[1:,0] - data.values[:-1,0])
    chunks = np.concatenate([chunks.reshape(-1), chunks[-1].reshape(-1)])
    return increment_numbers(chunks)


def get_mean_current_for_given_gate(data, vg):
    # primero revisamos si existe
    if vg in data["Vg (V)"]:
        return data[data["Vg (V)"]==vg].mean()["I (A)"]

    # primreo hay que dividir el intervalo en intervalos inyectivos
    data.loc[:, "chunks"] = divide_inyective(data)

    results = []
    number_of_chunks = int(data.loc[len(data) - 1, "chunks"])
    groups = data.groupby("chunks")
    for i in range(number_of_chunks):
        # check if desired value in chunk
        current_df = groups.get_group(i+1)
        if (vg > current_df["Vg (V)"].max()) and (vg < current_df["Vg (V)"].min()):
            continue

        results.append(interpolate_df(current_df, vg))

    #devolver el promedio de la lista
    return np.mean(results)


def summary_current_given_voltage(data):
    if experiment_type(data) == "Vg":
        return get_mean_current_for_given_gate(data[1], -1.3)
    else:
        return "None"


def center_data(data):
    min_x, min_y = find_dp(data)
    data_ = data.copy()
    data_["Vg (V)"] -= min_x
    data_["I (A)"] -= min_y
    return data_


def add_zoomed_in_subplot(ax, x_data, y_data, x_data_2, y_data_2, zoom_x_range, zoom_y_range, deltaI):
    zoomed_in_ax = ax.inset_axes([0.6, 0.3, 0.3, .5])  # Adjust the position and size as needed
    zoomed_in_ax.plot(x_data, y_data, color='blue')
    zoomed_in_ax.plot(x_data_2, y_data_2, color='red')
    zoomed_in_ax.vlines(-1.3, *zoom_y_range, "k", "--")
    zoomed_in_ax.set_title(f'$\Delta I$ = {deltaI} (A)')

    zoomed_in_ax.grid()
    zoomed_in_ax.set_xlim(zoom_x_range)
    zoomed_in_ax.set_ylim(zoom_y_range)
    ax.indicate_inset_zoom(zoomed_in_ax)


def get_VG(data):
    try:
        return data[0]["VG"]
    except:
        "None"


def make_data_summary(experiments):
    ledV = [data[0]['Laser voltage'] for data in experiments]
    led_wl = [data[0]['Laser wavelength'] for data in experiments]
    exp_type = [experiment_type(data) for data in experiments]
    Ids = [summary_current_given_voltage(data) for data in experiments]
    vg = [get_VG(data) for data in experiments]
    dp = []
    timestamp = []
    for i, data in enumerate(experiments):
        timestamp.append(get_timestamp_from_unix(float(data[0]["Start time"])))
        if exp_type[i] == "Vg":
            dp.append(find_dp(data))
        else:
            dp.append(np.nan)


    data = {'led V': ledV, 'Experiment type': exp_type, 'wl': led_wl, "vg": vg, "dp": dp, "timestamp": timestamp}
    df = pd.DataFrame(data)
    return df


def get_current_from_Vg(data, vg):
    # we first check if the value exists
    df = data[1]
    if vg in df["Vg (V)"]:
        return df[df["Vg (V)"]==vg].mean()["I (A)"]

    # encontrar la vecindad a fitear
    dVg = np.abs(df["Vg (V)"][1] - df["Vg (V)"][0])

    df_filtered = df[(df["Vg (V)"]>vg-2*dVg)&(df["Vg (V)"]<vg+2*dVg)]
    reg = linregress(df_filtered["Vg (V)"].values, df_filtered["I (A)"].values)
    #plt.plot(df["Vg (V)"], df["I (A)"], "+")
    #plt.plot(df_filtered["Vg (V)"], df_filtered["I (A)"], "o")
    #x = np.linspace(vg-2*dVg, vg+2*dVg, 100)
    #y = reg.slope * x + reg.intercept
    #plt.plot(x, y)

    return reg.slope * vg + reg.intercept


def get_timestamp_from_unix(timestamp_unix):
    # Convert Unix timestamp to a datetime object
    dt_object = datetime.datetime.fromtimestamp(timestamp_unix)

    # Convert the datetime object to a pandas Timestamp
    timestamp_pandas = pd.Timestamp(dt_object)

    return timestamp_pandas


def get_date_time_from_timestamp_unix(timestamp_unix):
    # Convert Unix timestamp to a datetime object
    dt_object = datetime.datetime.fromtimestamp(timestamp_unix)

    # Extract year, month, day, hour, minute, and second from the datetime object
    year = dt_object.year
    month = dt_object.month
    day = dt_object.day
    hour = dt_object.hour
    minute = dt_object.minute
    second = dt_object.second

    return year, month, day, hour, minute, second


def load_sorted_data(path_folder):
    data = sort_by_creation_date_calibration(os.path.join(path_folder, "*.csv"))
    return [read_pymeasure(path) for path in data]
