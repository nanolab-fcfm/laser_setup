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
- Keithley 2450 SourceMeter
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
