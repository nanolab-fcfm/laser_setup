# Laser Setup
Experimental setup for Laser, I-V and Transfer Curve measurements.

## Installation
This project mainly uses [PyMeasure](https://pypi.org/project/PyMeasure/), although other packages such as NumPy and PyQT6 are used. To install this project, first clone the repository:

```bash
git clone https://github.com/nanolab-fcfm/laser_setup
```
Then, create a virtual environment and activate it:

```bash
python -m venv <venv_name>
source <venv_name>/bin/activate
```
Finally, upgrade pip and install all necesary packages:
```python
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Usage
This project allows for the communication between the computer and the instruments used in the experimental setup, as well as the control of the instruments. So far, the following instruments are supported:
- Keithley 2450 SourceMeter ([Reference Manual](https://docs.rs-online.com/6c14/A700000007066480.pdf)) (Requires [NI-VISA](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html#480875) installed)
- TENMA Power Supply
- Thorlabs PM100D Power Meter ([Reference Manual](https://www.thorlabs.com/drawings/bb953791e3c90bd7-987A9A0B-9650-5B7A-6479A1E42E4265C8/PM100D-Manual.pdf))

As well as all instruments available un the PyMeasure library.

### Scripts
To start using the program, you should first setup the adapters needed to run a measurement. This is done by running

```python
python -m Scripts.setup_adapters
```

This interactive script will check all connected devices in your computer, and guide you to correctly setup every device in the configuration file `default_config.ini`. A new config file will be created; `config/config.ini`. This will override the default configuration, and you can later edit this file to your liking. To add more instruments, simply add their name to the `Adapters` section and run `setup_adapters.py`.


If you want to run a measurement that uses a TENMA controlled laser, you should first run the following script to calibrate the laser's power:

```python
python -m Scripts.calibrate_laser
```


Each Script corresponds to a different procedure, and can be run independently. To run a script, use the following command:
```
python -m Scripts.<script_name>
```

Additionally, there are two scripts to quickly analyze data.

If you want to find the dp of an IVg file:

```
python -m Scripts.find_dp_script
```

To calculate the desired powers of a LED calibration file you can use the following commando specifying the powers in uW (separated by a space):

```
python -m Scripts.find_calibration_voltage <desired powers>
```

## Testing
This project uses [PyTest](https://docs.pytest.org/en/stable/) for testing.
To run the tests, use the following command:
```
python -m pytest
```
Tests are stored in the `tests` folder, and are named `test_<module_name>.py`. You can add more tests by creating a new file in the `tests` folder, and naming it `test_<new_module_name>.py`. You can also check each test individually by running
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
| `laser_T`  | Laser ON+OFF period | 360. | 's'   |         |
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