# Troubleshooting & FAQ

Common issues and how to fix them. If your problem isn't here, check the
[log file](user-guide/data-and-output.md#logs) (`log/laser_setup.log`) and open
an issue on GitHub.

## Installation

??? failure "`uv` tries to compile scipy/numpy from source and fails (wants a Fortran compiler)"
    `uv` selected a Python newer than the available prebuilt wheels. This repo
    pins **Python 3.12** via `.python-version` to avoid it. Force it if needed:

    ```bash
    uv run --python 3.12 laser_setup
    # or pin for the project:
    uv python pin 3.12 && uv sync
    ```

??? failure "`command not found: laser_setup`"
    Run it through the project environment: `uv run laser_setup` from the repo
    folder. The bare command only exists if you did `uv tool install`.

??? failure "The window never appears / `qt.qpa.plugin: could not load the Qt platform plugin`"
    On Linux, install the system Qt/X11 runtime libraries your distro needs for
    Qt apps (e.g. `libxcb-*`, `libgl1`). For headless commands set
    `QT_QPA_PLATFORM=offscreen`.

## Configuration

??? failure "The Procedures or Sequences menu is empty"
    You ran `init`, which created `config/config.yaml` pointing at
    `./config/procedures.yaml` (etc.) that don't exist yet. Copy the templates:

    ```bash
    cp config/templates/{procedures,sequences,instruments,parameters}.yaml config/
    ```

    See [Tutorial 4](tutorials/04-your-config.md#step-2-populate-the-referenced-files).

??? failure "My config edits don't take effect"
    `CONFIG` is read at startup. Relaunch the app, or click the red **Reload**
    button (++ctrl+r++) after editing in the Config window.

??? question "Where does my data go?"
    Under `Dir.data_dir` (default `./data`), in dated subfolders. See
    [Data & Output Files](user-guide/data-and-output.md).

## Instruments

??? failure "A procedure errors at startup trying to connect an instrument"
    Either connect the hardware and fix the adapter address (run
    `setup_adapters`), or run in **debug mode** to simulate it:

    ```bash
    uv run laser_setup -d <Procedure>
    ```

??? failure "`setup_adapters` finds nothing"
    It needs a VISA backend. Install NI-VISA (real hardware) or `pyvisa-py`
    (`uv add pyvisa-py`). Serial-only devices (TENMA, PT100) appear as COM ports.
    See [Installation → VISA backend](getting-started/installation.md#visa-backend).

??? failure "`ModuleNotFoundError: bendev` when using the Bentham light source"
    The Bentham driver depends on the proprietary `bendev` package, which isn't
    on PyPI. Install it from the vendor, or avoid procedures that use the Bentham
    (`VVg`, `ItWl`, `Pwl`) unless you have it.

??? warning "An instrument seems to do nothing during a run"
    It may have been **disabled** by a toggle (e.g. *Laser toggle* off disables
    `tenma_laser`). Disabled instruments silently ignore commands. See
    [Instruments → Disabling](user-guide/instruments.md#disabling).

## GUI

??? failure "Plot lines are invisible / the plot is white"
    In dark mode the canvas is forced black so light curves show. If you changed
    `dark_mode`, restart the app so plot styling re-applies.

??? question "How do I stop a run safely?"
    Click **Abort** (the procedure checks `should_stop()` and exits cleanly), or
    use the **Shutdown** button to force-power-down instruments.

## Documentation

??? failure "`mkdocs build --strict` fails on a link or reference"
    `--strict` rejects broken internal links and nav entries. Fix the path the
    error names. Preview interactively with `uv run --group docs mkdocs serve`.

??? question "How do I build the docs without installing anything globally?"
    Use the `uv` docs group or Docker — see
    [Building & deploying these docs](building-and-deploying-docs.md).

## Updating

??? question "How do I update to the latest version?"
    ```bash
    git pull && uv sync
    ```
    Or run the in-app **Get updates** script / `uv run laser_setup get_updates`
    to check whether you're behind.
