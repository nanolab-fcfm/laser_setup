# Laser Setup
Experimental setup for Laser, I-V and Transfer Curve measurements.


## Usage
This project allows for the communication between the computer and the instruments used in the experimental setup, as well as the control of the instruments. So far, the following instruments are supported:
- Keithley 2450 SourceMeter ([Reference Manual](https://download.tek.com/manual/2450-901-01_D_May_2015_Ref.pdf)) (Requires [NI-VISA](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html) installed)
- Keithley 6517B Electrometer ([Reference Manual](https://download.tek.com/manual/6517B-901-01D_Feb_2016.pdf) (Also requires NI-VISA))
- TENMA Power Supply
- Thorlabs PM100D Power Meter ([Reference Manual](https://www.thorlabs.com/drawings/bb953791e3c90bd7-987A9A0B-9650-5B7A-6479A1E42E4265C8/PM100D-Manual.pdf))
- Bentham TLS120Xe Light Source ([Reference Manual](https://www.bentham.co.uk/fileadmin/uploads/bentham/Components/Tunable%20Light%20Sources/TLS120Xe/TLS120Xe_CommunicationManual.pdf))

As well as all instruments available in the [PyMeasure library](https://pymeasure.readthedocs.io/en/latest/api/instruments/index.html).

The main window of the program can be run by executing either of the following commands:

```bash
laser_setup
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

Alternatively, you can install the package directly from the repository:

```bash
pip install git+https://github.com/nanolab-fcfm/laser_setup.git
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


## Procedures
A list of all available Procedures and their parameters. To maximize functionality, all user-written procedures should be subclasses of `BaseProcedure`, which is a subclass of `Procedure` from PyMeasure. Procedures inherit the following from their parent class:
- Parameters (`pymeasure.experiment.Parameter` type)
- INPUTS (Inputs to display in the GUI)
- DATA_COLUMNS (Columns to display in the GUI and save to file)
- `startup`, `execute` and `shutdown` methods


## Procedure Sequence
A series of procedures can be run in sequence for a single chip by using the `MetaProcedure` class. This class allows for the execution of a series of procedures, and the saving of the data to the respective files. The `MetaProcedure` class is a subclass of `BaseProcedure`.

To run a sequence of procedures, create a new class that inherits from `MetaProcedure`, and define the `procedures` attribute as a list of procedures to run. The `procedures` attribute should be a list of `BaseProcedure` subclasses, uninitialized. The parameters of each procedure are then set by running the `display_window` function.


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
