# Laser Setup

📖 **Full documentation:** <https://nanolab.cl/laser_setup/> — start with the
[Installation guide](https://nanolab.cl/laser_setup/getting-started/installation/)
and the [hands-on Tutorials](https://nanolab.cl/laser_setup/tutorials/)
(no hardware required). The documentation source lives in [`docs/`](docs/) and can be
previewed locally with `uv run --group docs mkdocs serve`.

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

If you have procedures defined in a Python script and in the YAML (see [procedures.yaml](laser_setup/assets/templates/procedures.yaml) for examples), you can invoke them directly:

```bash
laser_setup <procedure_name>
```

This will load the relevant procedure class from the OmegaConf-based configs, then open an ExperimentWindow.

If you prefer to run procedures directly from Python, you can import the relevant `Procedure` classes and call them directly.

### Scripts

Scripts can be run similarly by name:

```bash
laser_setup <script_name>
```

## Installation

The recommended way is with [`uv`](https://docs.astral.sh/uv/), which installs
everything into a project-local environment (nothing system-wide). The repository
pins Python 3.12 via `.python-version`.

```bash
git clone https://github.com/nanolab-fcfm/laser_setup.git
cd laser_setup
uv sync                 # create the environment and install dependencies
uv run laser_setup      # launch the main window
```

See the **[full Installation guide](https://nanolab.cl/laser_setup/getting-started/installation/)**
for the Docker option, instrument drivers (NI-VISA), and troubleshooting.

## Usage

```bash
uv run laser_setup                 # main window (GUI hub)
uv run laser_setup FakeProcedure   # a demo experiment, no hardware needed
uv run laser_setup -d It           # a real procedure with simulated instruments
uv run laser_setup --help          # list every procedure and script
```

This launches the window defined in [MainWindow](laser_setup/display/windows/main_window.py).
New here? Follow the [hands-on Tutorials](https://nanolab.cl/laser_setup/tutorials/).

## Configuration

Most configuration is handled in YAML files and can be loaded or overridden at runtime. OmegaConf merges these with defaults, enabling dynamic instantiation of procedures, sequences, instruments and parameters. The YAML templates are stored in [laser_setup/assets/templates](laser_setup/assets/templates).

### Editing Configuration

You can edit YAML settings to define:

- Main window parameters (e.g., README file, window size, icon, etc.).
- Procedures, Scripts, and Sequences.
- Instrument settings, pointing to classes that the InstrumentManager will initialize.

## Procedures

To maximize functionality, all user-written procedures should be subclasses of `BaseProcedure`, which is a subclass of `Procedure` from PyMeasure. These procedures inherit the following:

- The following parameters (`pymeasure.experiment.Parameter` type):
  - `procedure_version` (version of the procedure)
  - `show_more` (boolean to show more parameters in the GUI)
  - `info` (information about the procedure)
  - `skip_startup` (boolean to skip the startup method)
  - `skip_shutdown` (boolean to skip the shutdown method)
  - `start_time` (start time of the procedure, set with `time.time()`)
- Their corresponding INPUTS (Inputs to display in the GUI)
- Base `startup` and `shutdown` methods
- `instruments`, an `InstrumentManager` object that handles the instruments used in the procedure

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
- Documentation lives in [`docs/`](docs/) (MkDocs Material) and is published to
  [GitHub Pages](https://nanolab.cl/laser_setup/). See the
  [Contributing guide](https://nanolab.cl/laser_setup/contributing/)
  and [Building & deploying the docs](https://nanolab.cl/laser_setup/building-and-deploying-docs/).
