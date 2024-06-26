# Laser Setup
Experimental setup for Laser, I-V and Transfer Curve measurements.


## Usage
This project allows for the communication between the computer and the instruments used in the experimental setup, as well as the control of the instruments. So far, the following instruments are supported:
- Keithley 2450 SourceMeter ([Reference Manual](https://docs.rs-online.com/6c14/A700000007066480.pdf)) (Requires [NI-VISA](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html) installed)
- TENMA Power Supply
- Thorlabs PM100D Power Meter ([Reference Manual](https://www.thorlabs.com/drawings/bb953791e3c90bd7-987A9A0B-9650-5B7A-6479A1E42E4265C8/PM100D-Manual.pdf))
- Bentham TLS120Xe Light Source ([Reference Manual](https://www.bentham.co.uk/fileadmin/uploads/bentham/Components/Tunable%20Light%20Sources/TLS120Xe/TLS120Xe_CommunicationManual.pdf))

As well as all instruments available in the [PyMeasure library](https://pymeasure.readthedocs.io/en/latest/api/instruments/index.html).

The main window of the program can be run by executing either of the following commands:

```bash
laser_setup     # Only after installing the package
```

```python
python .
```

The main window will display all available procedures, and will allow you to run them.


## Installation
This project mainly uses [PyMeasure](https://pypi.org/project/PyMeasure/), although other packages such as NumPy and PyQT6 are used. To install this project, first clone the repository:

```bash
git clone https://github.com/nanolab-fcfm/laser_setup.git
```
Then, create a virtual environment and activate it:

```bash
python -m venv <venv_name>
source <venv_name>/bin/activate
```

In Windows, use the following command to activate the virtual environment instead:

```powershell
<venv_name>/scripts/activate
```

Finally, upgrade pip and install this package and its required:
```python
python -m pip install --upgrade pip
pip install .
```

This will create an entry point for the program, which can be run by executing:

```bash
laser_setup
```


## Configuration
The configuration file `default_config.ini` contains the configuration for the instruments used in the setup. This file is used to set up the instruments and their respective addresses, as well as the default parameters for the procedures. The configuration file is divided into sections, each corresponding to a different instrument. This file, however, should not be edited directly. Any changes to the configuration should be done by first running the `setup_adapters` script, which will create a new configuration file `config/config.ini`. This file will be loaded after the default configuration, and will override any parameters set before.


### Scripts
If you prefer it, you can run the scripts directly from the command line. To start using a specific script, you should first set up the adapters needed to run a measurement. This is done by running

```bash
laser_setup setup_adapters
```

This interactive script will check all connected devices in your computer, and guide you to correctly setup every device in your configuration. A new config file will be created; `config/config.ini`. To add more instruments, simply add their name to the `Adapters` section of the new config file and run `setup_adapters.py`.

If you want to run a measurement that uses a TENMA controlled laser, you should first run the following script to calibrate the laser's power:

```bash
laser_setup calibrate_laser
```

Each Script corresponds to a different procedure, and can be run independently. To run a script, use the following command:

```bash
laser_setup <script_name>
```

If you cloned the repository, you can also run the scripts directly from the `Scripts` folder:

```python
python -m Scripts.<script_name>
```

Additionally, there are two scripts to quickly analyze data.

If you want to find the Dirac Point of an IVg file:

```
laser_setup find_dp_script
```

To calculate the desired powers of a LED calibration file you can use the following command, specifying the powers in uW (separated by a space):

```
python -m Scripts.find_calibration_voltage <desired powers>
```


## Testing
This project uses [PyTest](https://docs.pytest.org/en/stable/) for testing.
To run the tests, use the following command:
```
python -m pytest
```
Tests are stored in the `tests` folder, and are named `test_<module_test>.py`. You can add more tests by creating a new file in the `tests` folder, and naming it `test_<any>.py`. You can also check each test individually by running

```
python -m tests.<test_name>
```


## Procedures
A list of all available Procedures and their parameters. All procedures are subclasses of `BaseProcedure`, which is a subclass of `Procedure` from PyMeasure. Procedures inherit the following from their parent class:
- Parameters (`pymeasure.experiment.Parameter` type)
- INPUTS (Inputs to display in the GUI)
- DATA_COLUMNS (Columns to display in the GUI and save to file)
- `startup`, `execute` and `shutdown` methods


### BaseProcedure

The base class for all procedures involving a chip.

#### Parameters
| Name       | Ext. Name   | Default | Units | Choices |
|------------|-------------|---------|-------|---------------|
|`procedure_version`| Procedure version|'1.0.0'|       |          |
| `chip_group`|Chip group name|       |       |['Margarita', 'Miguel', 'Pepe (no ALD)', 'Unbonded', '8']|
|`chip_number`| Chip number| 1       |       |          |
| `sample`   | Sample      |         |       |['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']|
| `info`     | Information | 'None'  |       |          |

#### INPUTS
['chip_group', 'chip_number', 'sample', 'info']


### IVgBaseProcedure(BaseProcedure)

#### Parameters
| Name       | Ext. Name   | Default | Units | Choices |
|------------|-------------|---------|-------|---------|
| `vds`      | VDS         | 0.075   | 'V'   |          |
| `vg_start` | VG start    | -35.    | 'V'   |          |
| `vg_end`   | VG end      | 35.     | 'V'   |          |
| `laser_toggle`|Laser toggle| False |       |          |
| `laser_wl` |Laser wavelength|      | 'nm'  |[0, 280, 300, 325, 365, 385, 405, 455, 470, 505, 565, 590, 625, 680, 700, 850, 1050, 1450]|
| `laser_v`  |Laser voltage| 0.      | 'V'   |          |
| `N_avg`    | N_avg       | 2       |       |          |
| `vg_step`  | VG step     | 0.2     | 'V'   |          |
| `step_time`| Step time   | 0.01    | 's'   |          |
| `Irange`   | Irange      | 0.001   | 'A'   |          |

#### INPUTS
['vds', 'vg_start', 'vg_end', 'laser_toggle', 'laser_wl', 'laser_v', 'N_avg', 'vg_step', 'step_time']

#### DATA_COLUMNS
['Vg (V)', 'I (A)']

#### Execute
`pass`


### ItBaseProcedure(BaseProcedure)

#### Parameters
| Name       | Ext. Name   | Default | Units | Choices |
|------------|-------------|---------|-------|---------------|
| `laser_wl` |Laser wavelength|      | 'nm'  |[0, 280, 300, 325, 365, 385, 405, 455, 470, 505, 565, 590, 625, 680, 700, 850, 1050, 1450]|
| `laser_T`  | Laser ON+OFF period | 120. | 's'   |         |
| `laser_v`  | Laser voltage       | 0.   | 'V'   |         |
| `vds`      | VDS                 | 0.075| 'V'   |         |
| `vg`       | VG                  | 0.   | 'V'   |         |
| `sampling_t`| Sampling time (excluding Keithley)| 0.   | 's'   |          |
| `N_avg`    | N_avg               | 2    |       |         |
| `Irange`   | Irange              | 0.001| 'A'   |         |

#### INPUTS
['laser_wl', 'laser_T', 'laser_v', 'vds', 'vg', 'sampling_t', 'N_avg']

#### DATA_COLUMNS
['t (s)', 'I (A)', 'VL (V)']

#### Execute
`pass`


### IVg(IVgBaseProcedure)

#### Instruments
- Keithley 2450 (Control: `vds`, Measure: 'I (A)')
- TENMA (Control: `vg` (Positive))
- TENMA (Control: `vg` (Negative))
- TENMA (Control: `laser_V` (Positive), used if `laser_toggle` is True)

#### Execute
Perform I-V Measurement over a range of Gate Voltages


### It(ItBaseProcedure)

#### Instruments
- Keithley 2450 (Control: `vds`, Measure: ['t (s)', 'I (A)'])
- TENMA (Control: `vg` (Positive))
- TENMA (Control: `vg` (Negative))
- TENMA (Control: `laser_V` (Positive))

#### Execute
Perform I-t Measurement over time, turning the laser on at $t = 0$ and off at $t =$ `laser_T` $/2$.


### LaserCalibration

#### Parameters
| Name       | Ext. Name   | Default | Units | Choices |
|------------|-------------|---------|-------|---------------|
| `laser_wl` |Laser wavelength|      | 'nm'  |[0, 280, 300, 325, 365, 385, 405, 455, 470, 505, 565, 590, 625, 680, 700, 850, 1050, 1450]|
| `fiber`    | Optical fiber |    |       |['F1 (M92L02)', 'F2 (M92L02)', 'F3 (M96L02)', 'F4 (M96L02)']|
| `vl_start` | Laser voltage end | 0.   | 'V'   |         |
| `vl_end`   | Laser voltage end | 5.   | 'V'   |         |
| `vl_step`  | Laser voltage step | 0.1   | 'V'   |         |
| `step_time`| Step time   | 2.      | 's'   |         |
| `N_avg`    | N_avg       | 2       |       |         |

#### Metadata
| Name       | Ext. Name   | fget |
|------------|-------------|---------|
|  `sensor`  | Sensor model | 'power_meter.sensor_name' |

### PtBaseProcedure(Procedure)

#### Parameters
| Name       | Ext. Name   | Default | Units | Choices |
|------------|-------------|---------|-------|---------------|
| `laser_wl` |Laser wavelength|      | 'nm'  |[0, 280, 300, 325, 365, 385, 405, 455, 470, 505, 565, 590, 625, 680, 700, 850, 1050, 1450]|
| `laser_T`  | Laser ON+OFF period | 20. | 's'   |         |
| `laser_v`  | Laser voltage       | 0.   | 'V'   |         |
| `sampling_t`| Sampling time (excluding Keithley)| 0.   | 's'   |          |
| `N_avg`    | N_avg               | 2    |       |         |
| `Irange`   | Irange              | 0.001| 'A'   |         |

#### INPUTS
['show_more', 'info', 'laser_wl', 'fiber', 'laser_v', 'laser_T', 'N_avg', 'sampling_t']

#### DATA_COLUMNS
['t (s)', 'P (W)', 'VL (V)']

#### Execute
`pass`


## Procedure Sequence
A series of procedures can be run in sequence for a single chip by using the `MetaProcedure` class. This class allows for the execution of a series of procedures, and the saving of the data to the respective files. The `MetaProcedure` class is a subclass of `BaseProcedure`.

To run a sequence of procedures, create a new class that inherits from `MetaProcedure`, and define the `procedures` attribute as a list of procedures to run. The `procedures` attribute should be a list of `BaseProcedure` subclasses, uninitialized. The parameters of each procedure are then set by running the `display_window` function.
