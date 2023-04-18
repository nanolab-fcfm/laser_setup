from lib.fits import NanolabLaserMeasurement
import pandas as pd
import glob
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import linregress
import matplotlib.pyplot as plt
from scipy.io import loadmat

def charge_curve_sign(df: pd.DataFrame):
    """
    this function takes a dataframe with the charge curve data and returns
    the sign of the charge curve
    """
    x, y = df.values[:len(df)//2, :].T
    res = linregress(x, y)
    return np.sign(res.slope)

def norm(x, y):
    x -= x[0]
    y -= y[0]
    y /= np.max(y)
    return x, y


def two_exp_model(x, A1, A2, tau1, tau2):
    return A1 * np.exp(-x/tau1) + A2 * np.exp(-x/tau2)


def model(x, y, *args, **kwargs):
    L = len(x)
    x_ = x[:int(L/10)]
    y_ = y[:int(L/10)]
    res = linregress(x_, y_)
    slope = res.slope
    
    if slope > 0:
        x, y = norm(x, y)
    else:
        x, y = norm(x, -y)
    
    # model 2 exp
    fit_result = curve_fit(two_exp_model, x, y, *args, **kwargs)
    
    return fit_result


def get_voltage_list_from_path(voltage_list_path):
    with open(voltage_list_path, "r") as f:
        r = f.read()
    r = r.split("\n")[:-1][::2]
    return [float(i) for i in r]


def get_info_from_path(path2info):
    """
    this function takes the path of the info file and returns
    a dictionary with the information
    """
    with open(path2info, "r") as f:
        r = f.read()
    r = r.split("\n")[1:-2]
    r = [i.split(",") for i in r]
    r = [item for sublist in r for item in sublist]
    r = [i.replace(" ", "") for i in r]
    r = {i.split("=")[0]: i.split("=")[1] for i in r}
    
    r["Vmin"] = float(r["Vmin"][:-1])
    r["Vmax"] = float(r["Vmax"][:-1])
    r["Vstep"] = float(r["Vstep"][:-1])
    r["Cycles"] = int(r["Cycles"])
    r["waitingtime"] = float(r["waitingtime"][:-1])
    r["timeatlight"] = float(r["timeatlight"][:-1])
    r["timeatdark"] = float(r["timeatdark"][:-1])
    r["wavelength"] = float(r["wavelength"][:-2])
    return r


def get_pandas_df_from_path(data_path):
    return pd.read_csv(data_path, sep="\t")


def get_calibration_values(voltage_list, calibration_path, wl, factor=1):
    """
    calibration_path: is the path of the folder with the calibration data
    wl: wavelength we are using
    factor: is the factor with which to get the effective power to the device
    
    returns (dict): list of the effective powers to the devices
    """
    
    file = glob.glob(calibration_path + f"/*{int(wl)}nm*")[0]
    df = pd.read_csv(file)
    df_filtered = df[df["SetVoltage(V)"].isin(voltage_list)]
    powers = {}
    for i, j in df_filtered.values:
        powers[i] = j
        
    base_power = df[df["SetVoltage(V)"].isin([0])]
    return base_power, powers


class ICMM_Measurement(NanolabLaserMeasurement):
    def __init__(self, data_path, calibration_path, calibration_factor=1):
        self.main_path = data_path
        files = glob.glob(self.main_path + "/*")
        files.sort()
        self.info_path, self.voltage_list_path, self.data_path = files  # here we have all the paths
        self.calibration_factor = calibration_factor
        self.calibration_path = calibration_path
        
        self.info = get_info_from_path(self.info_path)
        self.voltage_list = get_voltage_list_from_path(self.voltage_list_path)  # this voltage list is for the power
        self.data = get_pandas_df_from_path(self.data_path)
        
        self.fancy_indexing = None
        self.slices = None
        self.base_power, self.power_dict = get_calibration_values(self.voltage_list, self.calibration_path, self.info["wavelength"], self.calibration_factor)
        self.add_effective_power()

        self.model = None
        self.fit_results = None

        self.responsivity = {}
        self.photocurrent = {}
        self.dt_for_responsivity = None

    def chop(self):
        number_of_voltages_for_power = len(self.voltage_list)
        if self.info["waitingtime"] != 0:
            important_times = [self.info["waitingtime"]]
            cycle_time = self.info["timeatlight"] + self.info["timeatdark"]
            for i in range(number_of_voltages_for_power):
                important_times.append(important_times[-1] + cycle_time)
            important_times.append(self.info["waitingtime"])
        
        else:
            important_times = [0]
            current_time = 0
            cycle_time = self.info["timeatlight"] + self.info["timeatdark"]
            for i in range(number_of_voltages_for_power):
                current_time += cycle_time
                important_times.append(current_time)
                
        indices = []
        for t in important_times:
            indices.append(np.argmin(np.abs(self.data.values[:, 0] - t)))
            
        fancy_indexing = []
        for i, j in enumerate(indices):
            if i == len(indices) - 1:  # if it is the last index
                fancy_indexing.append([k for k in range(j, len(self.data.values[:,0]))])
            else:
                fancy_indexing.append([k for k in range(j, indices[i+1])])
        self.fancy_indexing = fancy_indexing
        
        self.slices = {}
        for i, key in enumerate(self.power_dict):
            self.slices[key] = self.data.iloc[self.fancy_indexing[i]]
        
    def add_effective_power(self):
        """
        this is the power from the laser that irradiates to the device, calibrated
        """
        base_power = self.base_power.values[0, 1]
        self.effective_power = {key: (self.power_dict[key] - base_power) * self.calibration_factor for key in self.power_dict}

    def fit(self, model, *args, **kwargs):
        self.model = model
        self.fit_results = {}

        for key in self.slices:
            x, y = self.slices[key].values.T
            l = int(len(x) / 2)
            x = x[:l]
            y = y[:l]
            self.fit_results[key] = model(x, y, *args, **kwargs)
            
    def plot_fit_result(self, dic_key, *args, **kwargs):

        x, y = self.slices[dic_key].values.T
        L = len(x)
        x_ = x[:int(L/10)]
        y_ = y[:int(L/10)]
        res = linregress(x_, y_)
        slope = res.slope
        
        if slope > 0:
            x, y = norm(x, y)
        else:
            x, y = norm(x, -y)
        
        x_hat = np.linspace(0, x.max())
        y_hat = two_exp_model(x_hat, *self.fit_results[dic_key][0])

        plt.plot(x, y, label="original")
        plt.plot(x_hat, y_hat, label="fit")
        plt.legend()
        plt.show()

    def get_responsivity(self, seconds, n=1):
        """

        Parameters
        ----------
        seconds: float: is a parameter to know how many seconds to consider for the linear fir in order
        to determine if the curve has a maximum or a minimum
        n: int: number of indices to ignore in the first half of each slice
        Returns
        None
        -------
        """

        if not self.slices:  # Check if sliced
            self.chop()

        if self.dt_for_responsivity != seconds:  # if we already did this, don't do it again
            self.dt_for_responsivity = seconds
        else:
            return

        for key in self.slices:  # for each slice
            x, y = self.slices[key].values.T  # get values (time, current)
            x -= x[0]
            time_index = np.argmin(np.abs(x - seconds))  # look for firsts seconds in order to check curvature
            x_fit, y_fit = x[:time_index], y[:time_index]
            r = linregress(x_fit, y_fit)  # perform linear regression
            half_index = int(len(y) / 2)
            if r.slope > 0:
                delta_i = np.abs(y[0] - np.max(y[:half_index - n]))
            else:
                delta_i = np.abs(y[0] - np.min(y[:half_index - n]))
            p = self.power_dict[key] - self.base_power.iloc[0, 1]
            self.responsivity[key] = delta_i / (self.calibration_factor * p)
            self.photocurrent[key] = delta_i



def get_responsivity(data):
    x, y = [], []
    for key in data.voltage_list:
        x.append(data.effective_power[key])
        y.append(data.responsivity[key])
    return x, y




class TransferCurve:
    def __init__(self, path, device_name):
        self.name = device_name
        self.matlab_file = loadmat(path)
        self.data = self.matlab_file["data_array"][1:, :]
        self.dp = self.data[np.argmin(self.data[:, 1]), 0]

    def plot(self):
        self.fig, self.ax = plt.subplots()
        x, y = self.data.T
        self.ax.plot(x, y * 1e6)
        self.ax.set_xlabel("Gate voltage (V)")
        self.ax.set_ylabel("Current ($\mu$A)")
        self.ax.set_title(f"Vds=75mV, {self.name}, Dirac Point at {self.dp}V")
        self.ax.grid(True)
        plt.tight_layout()
        return self.fig, self.ax


def plot_before_after(transfer_curve_before, transfer_curve_after, title):
    x_before, y_before = transfer_curve_before.data.T
    x_after, y_after = transfer_curve_after.data.T

    y_before *= 1e6
    y_after *= 1e6

    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.plot(x_before, y_before, label=f"Before photomeasurements Dirac point: {transfer_curve_before.dp} V")
    ax.plot(x_after, y_after, label=f"After photomeasurements Dirac point: {transfer_curve_after.dp} V")
    ax.set_xlabel("Gate voltage (V)")
    ax.set_ylabel("Current ($\mu$A)")
    ax.grid(True)
    ax.legend()

    plt.show()
