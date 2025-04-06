# Laser Setup

Experimental setup for Laser, I-V, and Transfer Curve measurements. This project utilizes [PyMeasure](https://pypi.org/project/PyMeasure/) under the hood and extends it with a YAML-based configuration system (via OmegaConf and Hydra) for flexible instrument and procedure management. It is strongly recommended to read the [PyMeasure documentation](https://pymeasure.readthedocs.io/en/latest/) to understand the underlying structure and classes.

This project allows for the communication between the computer and the instruments used in the experimental setup, as well as the control of the instruments. The following instruments are supported:

- Keithley 2450 SourceMeter ([Reference Manual](https://download.tek.com/manual/2450-901-01_D_May_2015_Ref.pdf)) (Requires [NI-VISA](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html) installed)
- Keithley 6517B Electrometer ([Reference Manual](https://download.tek.com/manual/6517B-901-01D_Feb_2016.pdf) (Also requires NI-VISA))
- TENMA Power Supply
- Thorlabs PM100D Power Meter ([Reference Manual](https://www.thorlabs.com/drawings/bb953791e3c90bd7-987A9A0B-9650-5B7A-6479A1E42E4265C8/PM100D-Manual.pdf))
- Bentham TLS120Xe Light Source ([Reference Manual](https://www.bentham.co.uk/fileadmin/uploads/bentham/Components/Tunable%20Light%20Sources/TLS120Xe/TLS120Xe_CommunicationManual.pdf))

As well as all instruments available in the [PyMeasure library](https://pymeasure.readthedocs.io/en/latest/api/instruments/index.html).

## Features

- Optional installation via uv for handling Python dependencies.
- YAML configs [laser_setup/assets/templates/](laser_setup/assets/templates/) that leverage Hydra instantiation to dynamically load modules and objects.
- A robust main GUI window (see [laser_setup.display.main_window.py](laser_setup/display/main_window.py)) that displays available procedures and scripts.
- An experiment window (laser_setup.display.experiment_window.py) for running PyMeasure-based procedures with plots, logs, and parameter inputs.
- Sequences: run multiple procedures in series using the SequenceWindow.
- InstrumentManager (laser_setup.instruments.manager.py) for centralized instrument setup and teardown.

### Running Specific Procedures

If you have procedures defined in a Python script and in the YAML (see [Qt.yaml](laser_setup/assets/templates/Qt.yaml) for examples), you can invoke them directly:

```bash
laser_setup <procedure_name>
```

This will load the relevant procedure class from the Hydra-based configs, then open an ExperimentWindow.

If you prefer to run procedures directly from Python, you can import the relevant classes and call them directly.

### Scripts

Scripts can be run similarly by name:

```bash
laser_setup <script_name>
```

## Installation

Clone the repository:

```bash
git clone https://github.com/nanolab-fcfm/laser_setup.git
```

Optionally install using uv:

```bash
uv venv
uv pip install https://github.com/nanolab-fcfm/laser_setup
```

or a virtual environment:

```bash
python -m venv <venv_name>
source <venv_name>/bin/activate  # Linux/Mac
<venv_name>/Scripts/activate     # Windows
pip install --upgrade pip
```

Or, for direct installation from GitHub:

```bash
pip install git+https://github.com/nanolab-fcfm/laser_setup.git
```

If installed, the `laser_setup` entry point for the program wll be created.

## Usage

Once installed, run either of the following commands to start the main GUI:

```bash
laser_setup
```

or

```python
python -m laser_setup
```

This launches the window defined in [MainWindow](laser_setup/display/main_window.py).

## Configuration

Most configuration is handled in YAML files and can be loaded or overridden at runtime. Hydra and OmegaConf merge these with defaults, enabling dynamic instantiation of procedures, sequences, instruments and parameters. The YAML templates are stored in [laser_setup/assets/templates/](laser_setup/assets/templates/).

### Editing Configuration

You can edit YAML settings (e.g., Qt.yaml) to define:

- Main window parameters (e.g., README file, window size, etc.).
- Procedure lists, Script entries, and Sequences.
- Instrument settings, pointing to classes that the InstrumentManager will initialize.

## Procedures

A list of all available Procedures and their parameters. To maximize functionality, all user-written procedures should be subclasses of `BaseProcedure`, which is a subclass of `Procedure` from PyMeasure. Procedures inherit the following from their parent class:

- Parameters (`pymeasure.experiment.Parameter` type)
- INPUTS (Inputs to display in the GUI)
- DATA_COLUMNS (Columns to display in the GUI and save to file)
- `startup`, `execute` and `shutdown` methods

## Creating New Procedures

Develop custom procedures by:

1. Subclassing `BaseProcedure`.
2. Defining your `INPUTS` and `DATA_COLUMNS`.
3. Setting up your parameters.
4. Setting up your instruments.
5. Overriding `startup`, `execute`, and `shutdown` as needed.

## Sequences

Use the SequenceWindow to group multiple procedures in series. This allows chaining them together without manually rerunning each experiment. Edit or create new sequence entries in YAML to define the flow of procedures.

## Contributing

- Code contributions should follow typical pull-request workflow on GitHub.
- Documentation is currently WIP.
