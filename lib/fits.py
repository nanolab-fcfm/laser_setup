import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import lmfit as lf
import dill as pickle
from scipy.signal import square
from numba import njit
from abc import ABC, abstractmethod
from glob import glob
from typing import Callable, Type, Any
from dataclasses import dataclass, field
from lib.utils import Params, get_month_day_test


@dataclass
class LabMeasurement(ABC):
    """
    Abstract class that describes a measurement of a GFET's electrical response.
    """
    path: str
    params: Params = field(default_factory=Params)
    df: pd.DataFrame = field(init=False, repr=False, default=None)

    def __post_init__(self):      
        self.path = os.path.relpath(self.path)

        if not os.path.isdir(self.path):
            raise ValueError(f'{self.path} is not a valid directory.')

        self.files = glob(self.path + "\\*")
        self.parse_params()

    def get_filename(self, startswith: str = None, endswith: str = None):
        """
        Returns the filename of the file that starts and/or ends with the given string.
        """
        filenames = [os.path.split(f)[1] for f in self.files]
        if startswith is not None:
            filenames = [f for f in filenames if f.startswith(startswith)]
        if endswith is not None:
            filenames = [f for f in filenames if f.endswith(endswith)]
        
        if len(filenames) == 0:
            raise ValueError(f'No file found with the given startswith and endswith.')

        return filenames[0]

    def save(self, filename: str = None) -> None:
        """
        Saves the measurement's parameters to a pickle file, using dill.
        """
        if filename is None:
            filename = self.path + '\\object.pkl'
        with open(filename, 'ab') as f:
            pickle.dump(self, f)
        
    @staticmethod
    def load(filename: str) -> Type['LabMeasurement']:
        """
        Loads the measurement's parameters from a pickle file, using dill.
        """
        if not os.path.isfile(filename):
            raise FileNotFoundError(f'{filename} is not a valid file.')
        with open(filename, 'rb') as f:
            self = pickle.load(f)
        
        return self

    @abstractmethod
    def parse_params(self, filename: str = None) -> None:
        """
        Abstract method that parses the parameters from the measurement's data.
        """
        pass


@dataclass
class GateSweep(LabMeasurement):
    """ TODO
    Describes a Gate Sweep measurement.

    Attributes
    ----------
    csvfile: str
        the absolute or relative path of the measurement's csv file
    params: Params
        the parameters of the measurement
    df: pandas.DataFrame
        the dataframe of the measurement. It includes more voltage and current values than the ones used for this class.
    x: numpy.ndarray
        time array measured by the Drain-Source Keithley, in seconds
    y: numpy.ndarray
        current array measured by the Drain-Source Keithley, in Amperes

    Methods
    -------
    """
    pass


@dataclass
class LaserMeasurement(LabMeasurement):
    """
    Abstract class that describes a measurement of a GFET's response to a laser pulse.

    Attributes
    ----------
    csvfile: str
        the absolute or relative path of the measurement's csv file
    params: Params
        the parameters of the measurement
    df: pandas.DataFrame
        the dataframe of the measurement. It includes more voltage and current values than the ones used for this class.
    x: numpy.ndarray
        time array measured by the Drain-Source Keithley, in seconds
    y: numpy.ndarray
        current array measured by the Drain-Source Keithley, in Amperes

    Methods
    -------
    """
    x: np.ndarray = field(init=False, repr=False, default=None)
    y: np.ndarray = field(init=False, repr=False, default=None)
    yerr: float = field(repr=False, default=1.)

    def __post_init__(self):
        super().__post_init__()


@dataclass
class NanolabLaserMeasurement(LaserMeasurement):
    """
    Describes a measurement of a GFET's response to a laser pulse, taken with the Nanolab's 2022 setup.

    Attributes
    ----------
    path: str
        the absolute or relative path of the measurement's csv file
    params: Params
        the parameters of the measurement
    yerr: float | np.ndarray
        the error of the current measurement, in Amperes
    init_slices: bool
        initializes the slices of the measurement, separating by Gate Voltage
    df: pandas.DataFrame
        the dataframe of the measurement. It includes more voltage and current values than the ones used for this class.
    x: numpy.ndarray
        time array measured by the Drain-Source Keithley, in seconds
    y: numpy.ndarray
        current array measured by the Drain-Source Keithley, in Amperes

    Methods
    -------

    """
    init_slices: bool = True
    slices: list = field(init=False, repr=False, default_factory=list)
    n_vgs: int = field(init=False, repr=False, default=0)
    _fit: bool = True

    def __post_init__(self):
        super().__post_init__()
        self.df = pd.read_csv(os.path.join(self.path, self.get_filename(endswith='.csv')))
        self.x = np.asarray(self.df['ds_time'].array)
        self.y = np.asarray(self.df['ids'].array)
        self.n_vgs = self._get_n_vgs()
        self.DP = self.params.vg_list[int(self.n_vgs/2)]
        if self.init_slices: self.slice()

    def parse_params(self, filename: str = None) -> None:
        """
        Parses the parameters from the measurement's params file.
        """
        if filename is None:
            filename = self.get_filename(startswith='params')

        params_file = os.path.join(self.path, filename)

        if not os.path.isfile(params_file):
            raise ValueError('No params file found.')
        
        with open(params_file, 'r') as f:
            self.params += Params(eval(f.read()))

        try:
            self.params['month'], self.params['day'], self.params['test_n'] = get_month_day_test(params_file)
        except ValueError:
            print(f'Could not parse month, day and test_n from {self.path}')

        if not hasattr(self.params, "laser_T"):
            print("Warning: No laser_T found in the params file. Setting it to 600")
            self.params["laser_T"] = 600

    def _get_n_vgs(self):
        """
        Returns the number of gate voltages in the measurement's VG list.
        """
        vg_list = self.params.vg_list
        if vg_list[-1] == 0:
            vg_list = vg_list[:-1]      # Elimina el 0 que se añade al final
        return len(list(set(vg_list)))

    def slice(self) -> None:
        """
        Splits the measurement into multiple curves, one for each gate voltage.
        """
        print(f'This measurement (test #{self.params.test_n} on {self.params.month} {self.params.day}) has {self.n_vgs} curve(s). Splitting...')
        t_good = self.x[:-1][np.abs(np.diff(self.df['vg']))<.25]
        ids_good = self.y[:-1][np.abs(np.diff(self.df['vg'].array))<.25]

        t_split = np.array_split(t_good, self.n_vgs)
        ids_split = np.array_split(ids_good, self.n_vgs)

        for i, (t, ids) in enumerate(zip(t_split, ids_split)):
            new_params = self.params.copy()
            new_params['curve_n'] = i
            new_params['vg'] = self.params.vg_list[i]

            try:
                self.slices.append(
                    RCWaveform(t, ids, new_params, yerr=self.yerr, init=True)
                    )

            except ValueError:
                print(f'Curve #{i+1} of test #{self.params.test_n} on {self.params.month} {self.params.day} is not valid.')
                continue

    def fit_all(self, model: str) -> None:
        """
        Fits all the curves in the measurement.
        """
        if not self.slices:
            raise ValueError('No curves to fit. Run slice() first.')
        
        if model not in ['2_exponentials', 'power_law']:
            raise ValueError('Invalid model.')

        for curve in self.slices:
            assert isinstance(curve, RCWaveform)
            for subcurve in curve.curves:
                assert isinstance(subcurve, ChargeDischarge)
                if model == '2_exponentials':
                    subcurve.fit_2_exponentials()
                elif model == 'power_law':
                    subcurve.fit_power_law()

    def get_by_vg(self, func_slices: Callable[[list], Any],
                func_subcurves: Callable[[Type['ChargeDischarge']], Any],
                condition: Callable[[Type['ChargeDischarge']], bool], *args, **kwargs):
        """
        Returns an array with the result of applying func_slices to each curve and
        func_subcurves to each subcurve that satisfies a condition.

        Parameters
        ----------
        func_slices: Callable
            A function that takes the array resulting from func_subcurves as argument and returns a value.
        func_subcurves: Callable
            A function that takes a ChargeDischarge as argument and returns a value.
        condition: Callable
            A function that takes a ChargeDischarge as argument and returns a boolean.
        *args, **kwargs: 
            Arguments to be passed to the functions.

        Returns
        -------
        result: np.ndarray
            An array with the result of applying the functions to the curves
            that satisfy the condition.
        """
        result = []
        for curve in self.slices:
            assert isinstance(curve, RCWaveform)
            subcurves = [func_subcurves(subcurve, *args, **kwargs) for subcurve in curve.curves if condition(subcurve)]
            result.append(func_slices(subcurves))

        return np.array(result)

    @property
    def description(self):
        desc = ""
        if hasattr(self.params, 'chip') and hasattr(self.params, 'sample'):
            desc += f"Chip {self.params.chip} sample {self.params.sample}, "

        if hasattr(self.params, 'laser_color'):
            desc += f"{self.params.laser_color}, "
        else:
            desc += "Blue Laser, "          # Asumiendo laser azul

        if hasattr(self.params, 'vds'):
            desc += f"$V_{{DS}}$ = {int(self.params.vds*1000)} [mV]"

        return desc

    @property
    def date(self):
        return f"{self.params['month']}_{self.params['day']}_test{self.params['test_n']}"


class Data:
    """
    Describes a 2D array of data, with optional error bars.

    Attributes
    ---------
    xdata: array-like
        x axis data
    ydata: array-like
        y axis data
    yerr=1: array-like or float
        error bars on y axis data. If float, it is the same error bar for
        every point

    Methods
    -------
    func2min(params, modelo, xdata, ydata, yerr):
        function to minimize using lmfit.minimizer.Minimizer.minimize()
    fit(params, modelo, xdata, ydata, yerr):
        Fits the indicated model to the data, given a set of initial
        parameters. Returns a lmfit.minimizer.MinimizerResult
    report(**kwargs):
        Prints a report of the last fit. If plot=True, also plots the data
        and the optimized model.
    average_y(n=10, keep_borders=False):
        averages each point with n points on the left and n to the right
    slice_data(*slice_):
        performs a simultaneous in-place slice of self.x and self.y

    """
    def __init__(self, xdata, ydata, yerr=1):
        self.x = np.asarray(xdata)
        self.y = np.asarray(ydata)
        self.yerr = yerr

    def __repr__(self) -> str:
        repr_str = 'Data(xdata : {}, ydata : {}, yerr : {})'.format(
            type(self.x), type(self.y), type(self.yerr)
        )
        return repr_str


    def get_params(self, params: list[lf.Parameter] | list[dict] | dict) -> lf.Parameters:
        """
        Creates a lmfit.Parameters() object with the parameters given in a list
        of either dict or lmfit.Parameters() objects. If params is a dict, it
        assumes they're of the form {'name': value, ...}.
        """
        lf_params = lf.Parameters()
        if not params:
            raise ValueError('params must be a non empty list of lmfit.Parameter or dict')

        else:
            if all(isinstance(p, lf.Parameter) for p in params):
                lf_params.add_many(*params)

            elif all(isinstance(d, dict) for d in params):
                lf_params.add_many(*[lf.Parameter(**d) for d in params])

            elif isinstance(params, dict):
                lf_params.add_many(*params.items())

            return lf_params

    def _func2min(self, params, model, xdata, ydata, yerr):
        """
        Function to minimize using lmfit.Minimizer.minimize().
        It is used internally by fit()
        """
        return (ydata - model(params, xdata)) / yerr

    def fit(self, model: Callable[[lf.Parameters, object], object],
            params, method='leastsq') -> lf.minimizer.MinimizerResult:
        """
        Fits the indicated model to self.x and self.y, given a set of initial
        parameters. It uses lmfit.Minimizer.minimize() to find the optimal
        parameters. Returns a lmfit.minimizer.MinimizerResult
        """
        self.init_params = self.get_params(params)
        out = lf.Minimizer(self._func2min, self.init_params, nan_policy='propagate',
                           fcn_args=(model, self.x, self.y, self.yerr))
        fit = out.minimize(method)
        self.last_fit: lf.model.ModelResult = fit
        self.last_model = model
        return fit

    def fit_model(self, Model: Type[lf.models.Model], params=None, guess=True) -> lf.model.ModelResult:
        """
        Fits a lmfit.models.Model to self.x and self.y, guessing initial
        parameters.
        """
        if guess and params is None:
            params = Model.guess(self.y, x=self.x)
        fit = Model.fit(self.y, params, x=self.x)
        self.last_fit: lf.model.ModelResult = fit
        self.last_model = Model
        return fit

    def report(self, plot=False, plot_init=False, xylabels=2*[''],
               legend=2*[''], **rkwargs):
        """
        Prints a report of the last fit. If plot=True, also plots the data,
        which is plotted with the optimized model. Try not to use this method,
        as it won't be updated.
        Returns None.

        Parameters
        ----------
        plot=False: bool
            whether it shows a matplotlib Figure
        xylabels=2*['']: array-like of len 2
            the labels to put on the x and y axis
        legend=2*['']: array-like of len 2
        the labels of the data and model to put on the legend
        **rkwargs
            extra parameters to give to lmfit.report_fit()

        """
        lf.report_fit(self.last_fit, **rkwargs)
        if plot:
            x_to_plot = np.linspace(self.x.min(), self.x.max(), 2*len(self.x))
            fig, ax = plt.subplots(tight_layout=True)
            ax.plot(self.x, self.y, 'o', ms=3, label=legend[0])
            ax.plot(x_to_plot,
                    self.last_model(self.last_fit.params, x_to_plot),
                    label=legend[1])
            ax.set_xlabel(xylabels[0])
            ax.set_ylabel(xylabels[1])
            title_str = ''.join(['{} = {:.3g}, '.format(
                p.name, p.value) for p in self.last_fit.params.values()
            ])
            ax.set_title(title_str)

            if plot_init:
                ax.plot(x_to_plot, self.last_model(self.init_params, x_to_plot),
                label='init')
            ax.legend()
            plt.show(block=False)

    def average_y(self, n=10, keep_borders=False):
        """Convolves the waveform with a unitary stride of length 2*n + 1."""
        self.y = np.convolve(self.y, [1/(2*n+1)]*(2*n+1))[n-1:-n-1]
        assert len(self.x) == len(self.y)
        if not keep_borders:
            self.x = self.x[n+1:-n+1]
            self.y = self.y[n+1:-n+1]

    def slice_data(self, *slice_):
        """Slices self.x and self.y in-place."""
        self.x = self.x[slice(*slice_)]
        self.y = self.y[slice(*slice_)]


class RCWaveform(Data):
    """
    Describes a RC curve with (assumed) constant gate voltage.

    Attributes
    ---------
    x: array-like
        x data, in this case, ds_time [s] 
    ydata: array-like
        y data, in this case, I_DS [A]
    params:
        params.Params object that describes the measurement parameters
    **kwargs:
        extra initial kwargs to give to super().__init__() (like yerr)

    Methods
    -------
    center_o1():
        centers the data by subtracting a linear fit to the data
    
    """
    def __init__(self, x, y, params: Params, init=True, **kwargs):
        super().__init__(x-x[0], y, **kwargs)
        self.params = params

        if init:
            self.init_curves()

    def __repr__(self) -> str:
        return f'RCWaveform(x={type(self.x)}, y={type(self.y)}, params={self.params})'

    def _set_fft(self):
        """
        Calculates the approximate Fourier Transform of the signal, 
        assuming that every point is evenly distributed in time and using
        the average time interval for the frequencies.
        The time array is irregular, so the FFT is not exact.
        """
        self.fft = np.fft.fft(self.y)
        self.freq = np.fft.fftfreq(len(self.y), np.diff(self.x).mean())

    def _set_phase(self):
        if self.x.max() < self.params.laser_T / 2:
            raise ValueError('The laser pulse is too short to be a RC curve. This measurement is not valid.')

        square_signal = square((self.x - 0)*2*np.pi/self.params.laser_T)
        ts1 = np.transpose([self.x, self.y])
        ts2 = np.transpose([self.x, square_signal])

        self.phase, DCF, DCFERR = sdcf(ts1, ts2, self.params.laser_T, dt=2.)
    
    def center_o1(self):
        """
        Centers the signal to first order. Adjusts a first order polynomial
        and subtracts it from the signal.
        """
        out = self.fit_model(lf.models.LinearModel())
        self.o1_fit = out
        self.y -= out.best_fit

    def _split_curves(self):
        self.curves = []
        semiT = self.params.laser_T / 2
        phi = (semiT - self.phase) % semiT
        t_span = np.ptp(self.x)
        delta = (t_span - phi) % semiT
        is_middle_curve = (self.x > phi) & (self.x < t_span-delta)
        t_good = self.x[is_middle_curve]
        ids_good = self.y[is_middle_curve]

        n_onoffs = int((t_span - phi - delta) // semiT)
        self.n_onoffs = n_onoffs

        is_ith_curve = lambda i: (t_good-phi>i*semiT) & (t_good-phi<(i+1)*semiT)

        for i in range(n_onoffs):
            sign = np.sign(self.phase) if i%2 else -np.sign(self.phase)
            t = t_good[is_ith_curve(i)][:-5]        # last 5 points are removes to avoid noise
            ids = ids_good[is_ith_curve(i)][:-5]
            curve = ChargeDischarge(t, ids, self.params, sign, yerr=self.yerr)
            self.curves.append(curve)

    def init_curves(self):
        """
        Initializes self.curves, a list of ChargeDischarge objects. These are
        fitted with either a power law or two exponentials.
        """
        self._set_phase()
        self._split_curves()


class ChargeDischarge(Data):
    """
    Describes a charge-discharge curve.

    Attributes
    ---------
    x: array-like
        x data, in this case, ds_time [s]
    y: array-like
        y data, in this case, I_DS [A]
    params:
        params.Params object that describes the measurement parameters
    sign: int or float
        +1 or -1, depending on the direction of the charge-discharge curve
    **kwargs:
        extra initial kwargs to give to super().__init__() (like yerr)

    Methods
    -------
    fit_2_exponentials():
        fits the taus of the charge-discharge curve with two exponentials
    
    """
    def __init__(self, x, y, params: Params, sign: int, **kwargs):
        if sign not in [-1, 1]:
            raise ValueError('sign must be -1 or 1')

        super().__init__(x - x[0], y, **kwargs)
        self.params = params
        self.sign = sign

    def fit_2_exponentials(self):
        nans = 'omit'       # nan_policy for lmfit Models
        c_mod = lf.models.ConstantModel(nan_policy=nans)
        e1_mod = lf.models.ExponentialModel(prefix='e1_', nan_policy=nans)
        e2_mod = lf.models.ExponentialModel(prefix='e2_', nan_policy=nans)

        y_range = self.y.ptp()
        max_mult = 100
        if self.sign == 1:
            min_amp = -y_range * max_mult
            max_amp = -y_range / max_mult
            init_amp = -y_range

        else:  
            min_amp = y_range / max_mult
            max_amp = y_range * max_mult
            init_amp = y_range

        pars = c_mod.make_params()
        pars['c'].set(value=self.y.mean(), min=self.y.min() - y_range, max=self.y.max() + y_range)
        pars.update(e1_mod.make_params())
        pars['e1_amplitude'].set(value=init_amp, min=min_amp, max=max_amp)
        pars['e1_decay'].set(value=5., min=1e-5, max=100.)

        pars.update(e2_mod.make_params())
        pars['e2_amplitude'].set(value=init_amp, min=min_amp, max=max_amp)
        pars['e2_decay'].set(value=40., min=1e-5, max=1000.)

        mod = c_mod + e1_mod + e2_mod
        fit = self.fit_model(mod, params=pars)

        t1, t2 = fit.params['e1_decay'], fit.params['e2_decay']
        self.taus = [t1, t2]
        self.RMS = fit.residual.std()
        self.last_fit: lf.model.ModelResult = fit
        return self.taus

    def fit_power_law(self):
        nans = 'omit'       # nan_policy for lmfit Models
        c_mod = lf.models.ConstantModel(nan_policy=nans)
        p_mod = lf.models.PowerLawModel(prefix='p_', nan_policy=nans)

        #Delete first values from x and y
        self.x = self.x[1:]
        self.y = self.y[1:]

        y_range = self.y.ptp()
        y_range_mult = 1.
        
        min_amp = self.y[0] - y_range * y_range_mult
        max_amp = self.y[0] + y_range * y_range_mult

        pars = c_mod.make_params()
        #pars['c'].set(value=self.y.mean(), min=self.y.min() - y_range, max=self.y.max() + y_range)
        pars['c'].set(expr='0.')
        pars.update(p_mod.make_params())
        pars['p_amplitude'].set(value=self.y[0], min=min_amp, max=max_amp)
        pars['p_exponent'].set(value=self.sign * .01, min=-.5, max=.5)

        mod = c_mod + p_mod
        fit = self.fit_model(mod, params=pars)

        t1, t2 = fit.params['p_exponent'], fit.params['p_amplitude']
        self.taus = [t1, t2]
        self.RMS = fit.residual.std()
        self.last_fit: lf.model.ModelResult = fit
        return self.taus



@njit(cache=True)
def _dcf(ts1: np.ndarray, ts2: np.ndarray, T: float, dt: float, dst: np.ndarray):
    t = np.linspace(-T/2 + dt/2., T/2 - dt/2., int(T/dt))
    dcf = np.zeros(t.shape[0])
    dcferr = np.zeros(t.shape[0])
    n = np.zeros(t.shape[0])

    for k in range(t.shape[0]):
        #ts1idx, ts2idx = np.where((dst < t[k]+dt/2.) & (dst > t[k]-dt/2.))
        ts1idx, ts2idx = np.where(np.abs(dst - t[k]) < dt/2.)
        n[k] = ts1idx.shape[0]

        dcfdnm = np.sqrt(np.var(ts1[ts1idx,1]) \
                        * np.var(ts2[ts2idx,1]))

        dcfs = (ts2[ts2idx,1] - np.mean(ts2[ts2idx,1])) \
                * (ts1[ts1idx,1] - np.mean(ts1[ts1idx,1])) / dcfdnm

        dcf[k] = np.sum(dcfs) / float(n[k])
        dcferr[k] = np.sqrt(np.sum((dcfs - dcf[k])**2)) / float(n[k] - 1)
    
    return t, dcf, dcferr


def sdcf(ts1: np.ndarray, ts2: np.ndarray, T: float, dt: float = None):
    """
    Extracted from github.com/astronomerdamo/pydcf. Original method by
        Edelson, R. A., & Krolik, J. H. (1988).
        "The discrete correlation function-A new method for analyzing unevenly sampled variability data".
        The Astrophysical Journal, 333, 646-659.

    This routine calculates the correlation of two time series by using a DCF
    algorithm with slot weighting. Uneven time series are allowed.

    This function is the bottleneck of the whole program. # TODO: optimize
    """
    if not ts1.shape == ts2.shape or not ts1.shape[1] in [2, 3]:
        raise ValueError(
            'ts1 and ts2 must have the same shape, and shape[1] must be 2 or 3'
            )

    if dt is None:
        # Recommended in @astronomerdamo's repo. Never choose dt < mean_diff_ts1
        dt = 10 * np.diff(ts1[:, 0]).mean()

    dst = ts2[None, :, 0] - ts1[:, 0, None]
    
    t, dcf, dcferr = _dcf(ts1, ts2, T, dt, dst)
    
    phase = t[dcf.argmax()]
    return phase, dcf, dcferr


def modelo_exp(params, t):
    r"$I_0 + I_1\cdot e^{-t/\tau_1}$"
    I0, I1, tau1, d = params.valuesdict().values()
    return I0 + I1 * np.exp(-(t-d)/tau1)

def modelo_rc(params, t):
    r"$I_0 + I_1\cdot e^{-t/\tau_1} + I_2\cdot e^{-t/\tau_2}$"
    I0, I1, I2, tau1, tau2 = params.valuesdict().values()
    return I0 + I1 * np.exp(-(t-0)/tau1) + I2 * np.exp(-(t-0)/tau2)

def modelo_recta(params, t):
    r"$I_0 + I_1\cdot t$"
    I0, I1 = params.valuesdict().values()
    return I0 + I1 * t
