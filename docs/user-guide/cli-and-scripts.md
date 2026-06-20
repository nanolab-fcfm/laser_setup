# CLI & Scripts

Laser Setup is launched with a single command, `laser_setup`, which we always
run as `uv run laser_setup` so it executes inside the project environment.

## The `laser_setup` command

```text
laser_setup [PROCEDURE_OR_SCRIPT] [-d/--debug] [-v/--version]
```

| Form | Effect |
| --- | --- |
| `laser_setup` | Open the main window (GUI hub). |
| `laser_setup <Procedure>` | Open an experiment window for that procedure. |
| `laser_setup <script>` | Run a registered utility script. |
| `laser_setup -d …` | Enable **debug mode** (simulate instruments). |
| `laser_setup -v` | Print the version and exit. |

The positional argument is validated against the set of registered procedures
**and** scripts, so `laser_setup --help` is also a quick way to list everything
the current configuration recognizes:

```bash
uv run laser_setup --help
```

Both `laser_setup` (console) and `laser_setup_gui` (windowed) entry points exist;
they call the same `main()` — the difference only matters for how a packaged
binary opens a console window on Windows.

!!! info "How dispatch works"
    `main()` calls `setup()` (which parses args and builds `CONFIG`) and then
    routes on the argument — see [Architecture](architecture.md#startup-flow).

## Bundled scripts

Scripts are plain functions registered under `scripts:` in `config.yaml` and
shown in the **Scripts** menu. The defaults:

| Script (CLI name) | Menu label | What it does |
| --- | --- | --- |
| `init` | Init Config | Copy the config templates and a starter `config.yaml` into `./config/`. |
| `setup_adapters` | Set up Adapters | Scan the VISA bus and write detected adapter addresses into `instruments.yaml`. |
| `get_updates` | Get updates | Check whether your clone is behind the GitHub remote; offer to pull. |
| `parameters_to_db` | Parameters to Database | Walk `./data/*.csv` and build a SQLite database of all run parameters. |
| `find_calibration_voltage` | Find calibration voltage | Interpolate the laser voltage for a target optical power from a calibration CSV. |

### `init`

```bash
uv run laser_setup init
```

Creates `config/config.yaml` and `config/templates/`. **Remember** to copy the
template files you reference into `config/` (see
[Tutorial 4](../tutorials/04-your-config.md#step-2-populate-the-referenced-files)).

### `setup_adapters`

```bash
uv run laser_setup setup_adapters
```

Auto-detects instrument addresses. Requires a VISA backend
([details](instruments.md#auto-discovering-adapters)).

### `get_updates`

```bash
uv run laser_setup get_updates
```

Uses GitPython to compare your local commit with the remote and tells you if a
`git pull` is available. It warns if `pyproject.toml` changed (so you know to
re-run `uv sync`).

### `parameters_to_db`

```bash
uv run laser_setup parameters_to_db
```

Reads every CSV under the data directory, extracts the parameter header, and
writes a SQLite database (one table per procedure, columns added dynamically as
new parameters appear). Browse it with **View → Database** in the GUI. See
[Data & Output Files](data-and-output.md#the-parameters-database).

### `find_calibration_voltage`

```bash
uv run laser_setup find_calibration_voltage
```

Prompts for a calibration CSV (produced by `LaserCalibration`) and one or more
target powers in µW, then interpolates the corresponding driver voltages. See
the [LED power calibration protocol](../led_calibration.md).

## Adding your own script

Point a `scripts:` entry at any importable function:

```yaml
scripts:
  my_tool:
    name: "My Tool"
    target: ${function:my_package.my_module.main}
    kwargs: {dry_run: true}
```

The function receives the `kwargs` as keyword arguments. If it accepts a
`parent` argument it can integrate with the GUI (for dialogs); CLI invocation
passes `parent=None`. See [Registering in YAML](../developer-guide/registering.md).
