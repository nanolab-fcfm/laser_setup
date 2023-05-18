# Laser Setup
Experimental setup for Laser, I-V and Transfer Curve measurements.

## Installation
This project mainly uses [PyMeasure](https://pypi.org/project/PyMeasure/), although other packages such as NumPy are used.
To install all necessary packages, use the following:
```
pip install -r requirements.txt
```

## Usage
This project allows for the communication between the computer and the instruments used in the experimental setup, as well as the control of the instruments. So far, the following instruments are supported:
- Keithley 2450 SourceMeter
- TENMA Power Supply

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
