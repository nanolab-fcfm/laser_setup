# CLI & scripts reference

See [CLI & Scripts](../user-guide/cli-and-scripts.md) for the full explanations.

## Command

```text
laser_setup [PROCEDURE_OR_SCRIPT] [-d] [-v] [-h]
```

Always invoked as `uv run laser_setup …` to stay inside the project environment.

| Argument / flag | Effect |
| --- | --- |
| *(none)* | Open the main window. |
| `<Procedure>` | Open an experiment window for that procedure. |
| `<script>` | Run a registered script. |
| `-d`, `--debug` | Debug mode — simulate instruments. |
| `-v`, `--version` | Print version and exit. |
| `-h`, `--help` | Show help, including the list of valid procedures/scripts. |

The positional argument's valid values are the union of registered procedure
names and script names.

## Bundled scripts

| CLI name | Menu label | Function |
| --- | --- | --- |
| `init` | Init Config | `laser_setup.cli.init_config.init_config` |
| `setup_adapters` | Set up Adapters | `laser_setup.cli.setup_adapters.setup` |
| `get_updates` | Get updates | `laser_setup.cli.get_updates.main` |
| `parameters_to_db` | Parameters to Database | `laser_setup.cli.parameters_to_db.main` |
| `find_calibration_voltage` | Find calibration voltage | `laser_setup.cli.find_calibration_voltage.main` |

## Examples

```bash
uv run laser_setup                 # main window
uv run laser_setup FakeProcedure   # demo experiment (no hardware)
uv run laser_setup -d It           # real procedure, simulated instruments
uv run laser_setup init            # scaffold config/
uv run laser_setup setup_adapters  # detect instrument adapters
uv run laser_setup --help          # list everything recognized
```

## Entry points

`pyproject.toml` defines two console entry points, both calling
`laser_setup.__main__:main`:

| Entry point | Kind |
| --- | --- |
| `laser_setup` | console script |
| `laser_setup_gui` | GUI script (no console window on Windows) |
