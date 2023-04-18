import datetime
import os
import time
import glob
import numpy as np

class Params(object):
    """
    A class to store the parameters of a measurement. It can be used as a dictionary 
    and as an object with attributes. It can be added to another Params object to 
    create a new one with the parameters of both.

    Attributes
    ----------
    param_dict: dict
        A dictionary with the parameters of the measurement.

    Methods
    -------
    __init__(param_dict: dict = {})
        Initializes the object with the parameters in param_dict.
    __str__()
        Returns a string with the parameters.
    __getitem__(key)
        Returns the value of the parameter with the given key.
    __setitem__(key, value)
        Sets the value of the parameter with the given key.
    __add__(other: 'Params')
        Returns a new Params object with the parameters of self and other.
    copy()
        Returns a copy of the object.
    """
    def __init__(self, param_dict: dict = {}):
        self.param_dict = param_dict

        for key in self.param_dict:
            setattr(self, key, self.param_dict[key])

    def __str__(self):
        param_str = "Measurement Parameters:\n" + \
            "".join(f"{key}: {val}\n" for key, val in self.param_dict.items())
        return param_str

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)
        self.param_dict[key] = value

    def __add__(self, other: 'Params'):
        return Params({**self.param_dict, **other.param_dict})

    def copy(self):
        return Params(self.param_dict.copy())


def get_csvfile(params: Params):
    """
    Asks for a path to save the .csv and .png files.

    Returns:
    csvfile: str
        The path for the .csv file
    """
    folder_name = params.folder_name
    filename = params.filename
    workspace_path = params.workspace_path
    today_str = datetime.datetime.now().strftime("%B/%d/")

    if not os.path.exists(workspace_path + today_str):
        os.mkdir(workspace_path + today_str)
    files = [file for file in os.listdir(workspace_path + today_str) if file.startswith(folder_name)]
    if not files:
        folder_name = folder_name + "1"
        filename = filename + "1"
    else:
        max_test_number = max([int(file[4:]) + 1 for file in files if files is not None])
        folder_name = folder_name + f"{max_test_number}"
        filename = filename + f"{max_test_number}"

    # A path for saving the data is suggested
    suggested_path = workspace_path + today_str + folder_name  # A new test_i folder is created
    csvfile = suggested_path + "/" + filename + ".csv"

    yes_aliases = ["y", "Y", "yes", "1", ""]
    ans = input(f"Do you want to save as '{csvfile}'? [Y/n] ")
    if ans in yes_aliases:
        path = suggested_path
        if not os.path.exists(path):
            os.mkdir(path)
    else:
        while True:
            csvfile = input("Enter a new path, including the filename but not '.csv': ") + ".csv"
            if os.path.isfile(csvfile):
                ans = input(f"File {csvfile} already exists! Do you want to overwrite it? [Y/n] ")
                if ans in yes_aliases:
                    break
                else:
                    print("If you want to quit without saving, press Ctrl+C.")
                    continue
            break

    return csvfile


def timeit(func):
    """Wrapper to time a function."""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        print(f'Timing {func.__name__}...', end='\r')
        func(*args, **kwargs)
        print('End after {:.2f} seconds!'.format(time.perf_counter() - start))

    return wrapper


def get_month_day_test(csvfile):
    """
    Returns the month and day of the test and the test number. The csvfile must
    be in the format of '**\\{month}\\{day}\\test{i}\\file.extension'
    """
    csvfile = os.path.abspath(csvfile)
    head1, test_str = os.path.split(os.path.split(csvfile)[0])
    head2, day_str = os.path.split(head1)
    _, month = os.path.split(head2)
    return month, int(day_str), int(test_str[4:])


def get_params_from_txt(params_file):
    """
    Reads and returns the parameters from a params.txt file.
    """
    if not os.path.isfile(params_file):
        raise ValueError('No params.txt found')
    
    else:
        with open(params_file, 'r') as f:
            # Overwrites param_dict if params.txt exists and is a dict
            param_dict = eval(f.read())

            params = Params(param_dict)

        params['month'], params['day'], params['test_n'] = get_month_day_test(params_file)

    return params

def filter_tests(func, is_testlaser=True, data_path="../data/nanolab/data/graphene_transistors/Kaj_samples_2g/"):
    if not os.path.isdir(data_path):
        raise ValueError("No data folder found")

    param_files = np.array(glob.glob(data_path + "**/params.txt", recursive=True))
    param_arr = np.array([get_params_from_txt(file) for file in param_files])

    if is_testlaser:
        newfunc = lambda p: hasattr(p, "vg_list") and func(p)
    else:
        newfunc = func

    is_long_testlaser = np.array([newfunc(par) for par in param_arr])
    laser_params = param_arr[is_long_testlaser]

    dirname = lambda p: os.path.join(data_path, f"{p.month}/{p.day:02d}/test{p.test_n}")
    tests = [dirname(par) for par in laser_params]

    # test_dates = [f"{par.month} {par.day} test{par.test_n}" for par in laser_params]
    return tests
