# Configuration keys

Every configuration key, its default, and what it controls. Defaults come from
`laser_setup/config/defaults.py` (the `AppConfig` dataclasses) and the bundled
`assets/templates/config.yaml`. For the layering/merge model see the
[Configuration System](../user-guide/configuration.md).

## Top-level sections

| Section | Purpose |
| --- | --- |
| `Dir` | File and directory paths. |
| `scripts` | Entries in the Scripts menu. |
| `Adapters` | Named adapter addresses (convenience). |
| `Qt` | All GUI/window settings. |
| `Filename` | Data file naming. |
| `Logging` | `logging.config.dictConfig` for console/file logs. |
| `matplotlib_rcParams` | Matplotlib styling (string values). |
| `Telegram` | Optional notification bot. |
| `parameters` / `procedures` / `sequences` / `instruments` | Loaded from their own files. |
| `_session` | Runtime-only state (CLI args, paths). Read-only. |

## `Dir`

| Key | Default | Meaning |
| --- | --- | --- |
| `global_config_file` | `config/config.yaml` (or `$CONFIG`) | Global config path. |
| `local_config_file` | `config/config.yaml` | Local override path. |
| `parameters_file` | bundled `templates/parameters.yaml` | Parameter definitions. |
| `procedures_file` | bundled `templates/procedures.yaml` | Procedure registry/overrides. |
| `sequences_file` | bundled `templates/sequences.yaml` | Sequence registry. |
| `instruments_file` | bundled `templates/instruments.yaml` | Instrument declarations. |
| `data_dir` | `data` | Where CSV files are written. |
| `database` | `database.db` | SQLite name, relative to `data_dir`. |

!!! warning
    After `init`, the local `config.yaml` repoints these at `./config/*.yaml`.
    Copy the templates you reference or the menus go empty — see the
    [blank-menu trap](../user-guide/configuration.md).

## `Qt.GUI`

| Key | Default | Meaning |
| --- | --- | --- |
| `style` | `Fusion` | Qt style; `default` uses the OS theme. |
| `dark_mode` | `true` | Dark palette; if false, the OS theme is used. |
| `font` | `Segoe UI` | Font family (empty → style default). |
| `font_size` | `12` | Base font size. |
| `splash_image` | bundled `splash.png` | Splash screen. |

## `Qt.MainWindow`

| Key | Default | Meaning |
| --- | --- | --- |
| `title` | `Laser Setup` | Window title. |
| `readme_file` | `README.md` | Markdown shown in the hub. |
| `size` | `[640, 480]` | Window size. |
| `widget_size` | `[640, 480]` | Default child widget size. |
| `icon` | bundled `splash.png` | Window icon. |

## `Qt.ExperimentWindow`

| Key | Default | Meaning |
| --- | --- | --- |
| `title` | `''` | Window title (empty → procedure name). |
| `inputs_in_scrollarea` | `true` | Put inputs in a scroll area. |
| `enable_file_input` | `false` | (Not implemented) file-input widget. |
| `dock_plot_number` | `2` | Plots shown in the Dock tab. |
| `info_file` | `./docs/led_protocol.md` | Markdown for the Info tab. |
| `icon` | bundled `splash.png` | Window icon. |

## `Qt.SequenceWindow`

| Key | Default | Meaning |
| --- | --- | --- |
| `abort_timeout` | `30` | Seconds the abort dialog waits before auto-continuing. |

## `Filename`

| Key | Default | Meaning |
| --- | --- | --- |
| `prefix` | `''` | File prefix (empty → procedure class name). |
| `suffix` | `''` | File suffix. |
| `ext` | `csv` | Extension. |
| `dated_folder` | `true` | Group files under `data/<date>/`. |
| `index` | `true` | Append `_1`, `_2`, …. |
| `datetimeformat` | `%Y-%m-%d` | Date format for folder/name. |

## `scripts`

A map of menu key → `{name, target, kwargs}`. `target` uses the
`${function:...}` resolver. Defaults: `init`, `setup_adapters`, `get_updates`,
`parameters_to_db`, `find_calibration_voltage`. See [CLI & scripts](cli.md).

## `Logging`

A standard `logging.config.dictConfig`. By default:

- **console** handler — `ColoredFormatter`, level `INFO`, attached to the
  `laser_setup` logger.
- **file** handler — level `DEBUG`, writes `log/laser_setup.log`.
- `pymeasure.log` is set to `WARNING`.

Change a logger's `level` to make the app more/less verbose.

## `matplotlib_rcParams`

String-valued Matplotlib settings passed to PyMeasure. Defaults:
`axes.grid: "True"`, `figure.autolayout: "True"`.

## `Telegram`

| Key | Default | Meaning |
| --- | --- | --- |
| `token` | `''` | Bot token; empty disables alerts. |
| `chat_ids` | `[]` | Chat IDs to notify on procedure completion. |

## `Adapters`

A flat map of friendly name → adapter address (e.g.
`keithley2450: USB0::...`, `tenma_neg: COM9`). Authoritative instrument wiring
lives in [`instruments.yaml`](instruments.md).

## Environment variables

| Variable | Effect |
| --- | --- |
| `CONFIG` | Overrides the global config file path. |
| `QT_QPA_PLATFORM=offscreen` | Run the Qt app headless (CI, servers). |
