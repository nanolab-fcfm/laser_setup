# Laser Setup
Experimental setup for Laser, I-V and Transfer Curve measurements.

## Installation
This project mainly uses [PyMeasure](https://pypi.org/project/PyMeasure/), although other packages such as NumPy are used.
To install all necessary packages, use the following:

```python
pip install -r requirements.txt
```

This program also includes Jupyter Notebooks, which are not included in the requirements.

## Usage
This project allows for the communication between the computer and the instruments used in the experimental setup, as well as the control of the instruments. So far, the following instruments are supported:
- Keithley 2450 SourceMeter (Requires [NI-VISA](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html#480875) installed)
- TENMA Power Supply

To start using the program, you should first setup the adapters needed to run a measurement. This is done by running

```python
python -m Scripts.setup_adapters
```

This interactive script will check all connected devices in your computer, and guide you to correctly setup every device in the configuration file `default_config.ini`. A new config file will be created; `config/config.ini`. This will override the default configuration, and you can later edit this file to your liking. To add more devices, simply add their name to the `Adapters` section and run `setup_adapters.py`.

Each Script corresponds to a different procedure, and can be run independently. To run a script, use the following command:
```
python -m Scripts.<script_name>
```

## Testing
This project uses [PyTest](https://docs.pytest.org/en/stable/) for testing.
To run the tests, use the following command:
```
python -m pytest
```

## Procedures
A list of all available Procedures and their parameters.

### IVgBaseProcedure

#### Parameters
| Name       | Ext. Name   | Default | Units | Choices |
|------------|-------------|---------|-------|---------------|
| `chip`     | Chip name   |         |       |['Margarita', 'Miguel', 'Pepe (no ALD)', 'other']|
|`chip_number`| Chip number| 1       |       |['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']|
| `sample`   | Sample      |         |       |          |
| `info`     | Information | 'None'  |       |          |
| `vds`      | VDS         | 0.075   | 'V'   |          |
| `vg_start` | VG start    | -35.    | 'V'   |          |
| `vg_end`   | VG end      | 35.     | 'V'   |          |
| `N_avg`    | N_avg       | 2       |       |          |
| `vg_step`  | VG step     | 0.2     | 'V'   |          |
| `step_time`| Step time   | 0.01    | 's'   |          |
| `Irange`   | Irange      | 0.001   | 'A'   |          |

#### INPUTS
['chip', 'chip_number', 'sample', 'info', 'vds', 'vg_start', 'vg_end', 'N_avg', 'vg_step', 'step_time']

#### DATA_COLUMNS
['Vg (V)', 'I (A)']

#### Execute
`pass`


### ItBaseProcedure

#### Parameters
| Name       | Ext. Name   | Default | Units | Choices |
|------------|-------------|---------|-------|---------------|
| `chip`     | Chip name   |         |       |['Margarita', 'Miguel', 'Pepe (no ALD)', 'other']|
|`chip_number`| Chip number| 1       |       |['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']|
| `sample`   | Sample      |         |       |          |
| `info`     | Information | 'None'  |       |          |
| `laser_wl` | Laser wavelength    | 0.   | 'nm'  |         |
| `laser_T`  | Laser ON+OFF period | 360. | 's'   |         |
| `laser_v`  | Laser voltage       | 0.   | 'V'   |         |
| `vds`      | VDS                 | 0.075| 'V'   |         |
| `vg`       | VG                  | 0.   | 'V'   |         |
| `sampling_t`| Sampling time (excluding Keithley)| 0.   | 's'   |          |
| `N_avg`    | N_avg               | 2    |       |         |
| `Irange`   | Irange              | 0.001| 'A'   |         |

#### INPUTS
['chip', 'chip_number', 'sample', 'info', 'laser_wl', 'laser_T', 'laser_v', 'vds', 'vg', 'sampling_t', 'N_avg']

#### DATA_COLUMNS
['t (s)', 'I (A)', 'VL (V)']

#### Execute
`pass`


### IVg(IVgBaseProcedure)

#### Instruments
- Keithley 2450 (Control: `vds`, Measure: 'I (A)')
- TENMA (Control: `vg` (Positive))
- TENMA (Control: `vg` (Negative))

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
