import pandas as pd
import glob
import numpy as np
import os 
import matplotlib.pyplot as plt
import datetime 


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


def get_timestamp(file):
    return float(read_pymeasure(file)[0]['Start time'])

def sort_by_creation_date(pattern):
    # Get a list of file paths that match the specified pattern
    file_paths = glob.glob(pattern)

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


def find_dp(data):
    df = data[1]  # pandas df
    diff = np.abs(df.diff()["I (A)"].values)
    indices_smallest_four = np.argpartition(diff, 4)[:4]
    return round(np.mean(df["Vg (V)"].values[indices_smallest_four]), 2)
    

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

# Perform the fitting using the L1-norm (absolute error) loss function

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
    data = sort_by_creation_date(os.path.join(path_folder, "*.csv"))
    return [read_pymeasure(path) for path in data]