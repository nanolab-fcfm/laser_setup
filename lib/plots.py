import os
from typing import Tuple, Literal
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import square
from lib.fits import NanolabLaserMeasurement, RCWaveform, ChargeDischarge


def plot_curve_with_square(Curve: RCWaveform) -> None:
    """
    Plots a curve with a square wave with the same period and phase, representing
    the laser ON/OFF.
    """
    T = Curve.params.laser_T
    print(f'phase = {Curve.phase}')

    fig, ax = plt.subplots(tight_layout=True)
    ax.plot(Curve.x, Curve.y)
    ax.plot(Curve.x, Curve.y.mean() + 
             square((Curve.x + Curve.phase)*2*np.pi/T)*np.ptp(Curve.y)/2, '--',
             label='Laser ON/OFF')
    ax.set_xlabel('$t$ [s]')
    ax.set_ylabel('$I_{DS}$ [A]')
    ax.grid()
    ax.legend(loc='upper right')
    fig.show()


def plot_charge_with_fit(charge: ChargeDischarge, i, T, phi) -> None:
    """
    Plots a singular Charge/Discharge curve with the last fit, in three different scales.
    """
    fig, ax = plt.subplots(1, 2, tight_layout=True, figsize=(10*.8, 5*.8))
    scales = ['linear', 'loglog']
    for k in range(2):
        ax[k].plot(charge.x + (i*T/2 + phi)*0, charge.y, 'o', label=f'c{i}, {scales[k]}', ms=3)
        ax[k].plot(charge.x + (i*T/2 + phi)*0, charge.last_fit.best_fit, '--', label='Fit')
        # ax[k].plot(charge.x, charge.y[0] * charge.x**(-charge.sign * pows))   # power law with same exponent as fit
        ax[k].set_xlabel('$t$ [s]')
        ax[k].legend()
        ax[k].grid()
    ax[0].set_ylabel('$I_{DS}$ [A]')
    # ax[1].set_yscale('log')
    ax[-1].set_xscale('log'); ax[-1].set_yscale('log')
    fig.show()


def plot_tau_vs_vg(TestLaser: NanolabLaserMeasurement, interactive=False, show=False, save=True) -> Tuple[plt.Figure, plt.Axes, plt.Axes]:
    """
    Plots the fit's characteristic times vs Gate Voltage for a given Laser Measurement.
    """
    TestLaser.fit_all('2_exponentials')
    if not hasattr(TestLaser, 'slices'):
        raise AttributeError(f'NanolabLaserMeasurement.slice() must be called before plotting')

    fig, ax = plt.subplots(3, 1, tight_layout=True, sharex=True, gridspec_kw={'height_ratios': [2, 2, 1]})

    fig.suptitle(TestLaser.description)

    s_taus1 = lambda s: s.last_fit.params['e1_decay'].value
    s_taus2 = lambda s: s.last_fit.params['e2_decay'].value
    s_charge = lambda s: (s.sign > 0 and s.params['vg'] >= TestLaser.DP) or (s.sign < 0 and s.params['vg'] < TestLaser.DP)
    s_discharge = lambda s: (s.sign > 0 and s.params['vg'] < TestLaser.DP) or (s.sign < 0 and s.params['vg'] >= TestLaser.DP)

    vgs = TestLaser.params.vg_list[:-1]
    taus1_charge = TestLaser.get_by_vg(np.mean, s_taus1, s_charge)
    taus1_charge_std = TestLaser.get_by_vg(np.std, s_taus1, s_charge)
    taus1_discharge = TestLaser.get_by_vg(np.mean, s_taus1, s_discharge)
    taus1_discharge_std = TestLaser.get_by_vg(np.std, s_taus1, s_discharge)
    taus2_charge = TestLaser.get_by_vg(np.mean, s_taus2, s_charge)
    taus2_charge_std = TestLaser.get_by_vg(np.std, s_taus2, s_charge)
    taus2_discharge = TestLaser.get_by_vg(np.mean, s_taus2, s_discharge)
    taus2_discharge_std = TestLaser.get_by_vg(np.std, s_taus2, s_discharge)

    R2s_charge = TestLaser.get_by_vg(np.mean, lambda s: s.last_fit.rsquared, s_charge)
    R2s_charge_std = TestLaser.get_by_vg(np.std, lambda s: s.last_fit.rsquared, s_charge)
    R2s_discharge = TestLaser.get_by_vg(np.mean, lambda s: s.last_fit.rsquared, s_discharge)
    R2s_discharge_std = TestLaser.get_by_vg(np.std, lambda s: s.last_fit.rsquared, s_discharge)

    ax[0].errorbar(vgs, taus1_charge, yerr=taus1_charge_std, fmt='o', c='g', label='$\\tau_1$ charge')
    ax[0].errorbar(vgs, taus1_discharge, yerr=taus1_discharge_std, fmt='o', c='r', label='$\\tau_1$ discharge')
    ax[1].errorbar(vgs, taus2_charge, yerr=taus2_charge_std, fmt='o', c='g', label='$\\tau_2$ charge')
    ax[1].errorbar(vgs, taus2_discharge, yerr=taus2_discharge_std, fmt='o', c='r', label='$\\tau_2$ discharge')
    ax[2].errorbar(vgs, R2s_charge, yerr=R2s_charge_std, fmt='.', c='g', label='$R^2$ charge')
    ax[2].errorbar(vgs, R2s_discharge, yerr=R2s_discharge_std, fmt='.', c='r', label='$R^2$ discharge')

    ax[-1].set_xlabel('$V_{G}$ [V]')
    ax[0].set_ylabel('$\\tau_1$ [s]')
    ax[1].set_ylabel('$\\tau_2$ [s]')
    ax[2].set_ylabel('$R^2$')

    for ax in ax:
        ax.legend()
        ax.grid()

    if save:
        fig.savefig(f'img/taus/{TestLaser.date}.pdf')
        fig.savefig(f'img/temp.pdf')

    if show:
        fig.show()

    while interactive:
        cont = input("Do you want to see the individual plots? (q: No, 1: +RCWaveforms, 2: +ChargeDischarge): ")
        if cont == '1' or cont == '2':
            plot_individual_curves(TestLaser, slices=cont=='2')
        elif cont == 'q':
            break

    return fig, ax#, ax2


def plot_pow_vs_vg(TestLaser: NanolabLaserMeasurement, interactive=False, show=False, save=True) -> Tuple[plt.Figure, plt.Axes]:
    """
    Plots the fit's exponent vs Gate Voltage for a given Laser Measurement.
    """
    TestLaser.fit_all('power_law')
    if not hasattr(TestLaser, 'slices'):
        raise AttributeError(f'NanolabLaserMeasurement.slice() must be called before plotting')

    fig, ax = plt.subplots(2, 1, tight_layout=True, sharex=True, gridspec_kw={'height_ratios': [3, 1]})

    fig.suptitle(TestLaser.description + ', $a \cdot x^p$ fit.')

    s_pow = lambda s: s.last_fit.params['p_exponent'].value
    s_charge = lambda s: (s.sign > 0 and s.params['vg'] >= TestLaser.DP) or (s.sign < 0 and s.params['vg'] < TestLaser.DP)
    s_discharge = lambda s: (s.sign > 0 and s.params['vg'] < TestLaser.DP) or (s.sign < 0 and s.params['vg'] >= TestLaser.DP)

    vgs = TestLaser.params.vg_list[:-1]
    pows_charge = TestLaser.get_by_vg(np.mean, s_pow, s_charge)
    pows_charge_std = TestLaser.get_by_vg(np.std, s_pow, s_charge)
    pows_discharge = TestLaser.get_by_vg(np.mean, s_pow, s_discharge)
    pows_discharge_std = TestLaser.get_by_vg(np.std, s_pow, s_discharge)

    s_R2 = lambda s: s.last_fit.rsquared

    R2s_charge = TestLaser.get_by_vg(np.mean, s_R2, s_charge)
    R2s_charge_std = TestLaser.get_by_vg(np.std, s_R2, s_charge)
    R2s_discharge = TestLaser.get_by_vg(np.mean, s_R2, s_discharge)
    R2s_discharge_std = TestLaser.get_by_vg(np.std, s_R2, s_discharge)

    ax[0].errorbar(vgs, pows_charge, yerr=pows_charge_std, fmt='o', c='g', label='Charge')
    ax[0].errorbar(vgs, pows_discharge, yerr=pows_discharge_std, fmt='o', c='r', label='Discharge')

    ax[1].errorbar(vgs, R2s_charge, yerr=R2s_charge_std, fmt='.', color='g', label='Charge')
    ax[1].errorbar(vgs, R2s_discharge, yerr=R2s_discharge_std, fmt='.', color='r', label='Discharge')

    ax[-1].set_xlabel('$V_{G}$ [V]')
    ax[0].set_ylabel('$p$')
    ax[1].set_ylabel('$R^2$')

    for ax in ax:
        ax.legend()
        ax.grid()

    if save:
        fig.savefig(f'img/pow/{TestLaser.date}.pdf')
        fig.savefig(f'img/temp.pdf')

    if show:
        fig.show()

    while interactive:
        cont = input("Do you want to see the individual plots? (q: No, 1: +RCWaveforms, 2: +ChargeDischarge): ")
        if cont == '1' or cont == '2':
            plot_individual_curves(TestLaser, slices=cont=='2')
        elif cont == 'q':
            break

    return fig, ax#, ax2


def plot_individual_curves(TestLaser: NanolabLaserMeasurement, slices: bool = True) -> None:
    """Plot individual curves and slices of the measurement interactively."""
    for i, curve in enumerate(TestLaser.slices):
        assert isinstance(curve, RCWaveform)            # only for pylints type checking
        T = curve.params.laser_T
        phi = (T/2 - curve.phase) % (T/2)
        plot_curve_with_square(curve)
        breakpoint()
        "Call curve by 'curve'. Input c to continue, q to quit. Type 'slices = False' to stop plotting slices."

        if slices:
            for j, subcurve in enumerate(curve.curves):
                plot_charge_with_fit(subcurve, j, T, phi)
                breakpoint()
                "Call curve by 'subcurve'. Input c to continue, q to quit."


def plot_measurement(path, fit: Literal['power_law', '2_exponentials'], overwrite: bool = False, **kwargs) -> NanolabLaserMeasurement:
    """
    Wrapper that plots the measurement with the given fit's properties.
    """
    if not fit in ['power_law', '2_exponentials']:
        raise ValueError(f"fit must be 'power_law' or '2_exponentials', not {fit}")

    if overwrite:
        TestLaser = NanolabLaserMeasurement(path, yerr=1e-10)
        TestLaser.save()

    try:
        TestLaser = NanolabLaserMeasurement.load(path + '/object.pkl')
    except FileNotFoundError:
        TestLaser = NanolabLaserMeasurement(path, yerr=1e-10)
        TestLaser.save()

    if fit == '2_exponentials':
        plot_tau_vs_vg(TestLaser, **kwargs)
    elif fit == 'power_law':
        plot_pow_vs_vg(TestLaser, **kwargs)

    return TestLaser


def quick_csv_plot(csvfile: str, x_column: str = None, y_column: str = None, **kwargs) -> None:
    if not csvfile:
        while True:
            csvfile = input("Paste the path of the .csv file (with .csv): ")
            if os.path.isfile(csvfile) and csvfile[-4:] == ".csv":
                break
            else:
                print("The file is not valid.")

    df = pd.read_csv(csvfile)
    columns = list(df.columns)
    print(f"The available columns to plot are: {columns}")
    if not x_column or x_column not in columns:
        x_column = input("Write a valid column to put at the x axis: ")
    if not y_column or y_column not in columns:
        y_column = input("Write a valid column to put at the y axis: ")
    assert x_column, y_column in columns

    plt.plot(df[x_column], df[y_column], **kwargs)
    plt.xlabel(x_column)
    plt.ylabel(y_column)
    plt.tight_layout()
    plt.show()
