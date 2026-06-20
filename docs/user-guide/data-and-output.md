# Data & Output Files

Every procedure run writes a self-describing CSV file. This page explains where
files go, how they're named, what's inside them, and how to aggregate them into
a database.

## Where data is saved

Files are written under the **data directory**, configured by `Dir.data_dir`
(default `./data`). With `Filename.dated_folder: true`, runs are grouped into
per-day subfolders:

```text
data/
└── 2026-06-21/
    ├── FakeProcedure2026-06-21_1.csv
    ├── It2026-06-21_1.csv
    └── It2026-06-21_2.csv
```

## File naming

The filename is assembled from the `Filename` config section (parsed by
PyMeasure):

```yaml
Filename:
  prefix: ''            # empty → use the procedure class name
  suffix: ''
  ext: csv
  dated_folder: true    # data/<date>/
  index: true           # append _1, _2, … to avoid collisions
  datetimeformat: "%Y-%m-%d"
```

So the default pattern is:

```text
{data_dir}/{date}/{ProcedureClass}{date}_{index}.{ext}
```

Set `prefix` to use a fixed name instead of the class name, or `suffix` to tag
files (e.g. a run label).

## Anatomy of a CSV

A PyMeasure results file has a **header** (procedure, parameters, metadata) and
a **data** section:

```text
#Procedure: <laser_setup.procedures.It.It>
#Parameters:
#	Chip group: Margarita
#	Chip number: 3
#	Sample: B
#	VDS: 0.075 V
#	VG: 15.0 V
#	...
#Metadata:
#	Start time: 1718900000.0
#Data:
t (s),I (A),VL (V),Plate T (degC),Ambient T (degC),Clock (ms)
0.00,1.2e-06,0.0,25.0,23.4,1024
0.15,1.3e-06,0.0,25.1,23.4,1040
...
```

- The header records **every parameter value** and metadata, so a run is fully
  reproducible — you can see exactly how it was taken.
- The columns are the procedure's `DATA_COLUMNS`. Parameters listed in a
  procedure's `EXCLUDE` are omitted from the header.

!!! tip "Reading files programmatically"
    `laser_setup.utils` has helpers — `read_pymeasure()` splits header/data, and
    `read_file_parameters()` extracts just the parameter dict. PyMeasure's own
    `Results.load()` reconstructs a results object with a pandas DataFrame.

## The Dirac point and `DP`

The `IVg` procedure estimates a device's **Dirac point** (the gate voltage of
peak resistance) and other procedures can reference it. When you enter a gate
voltage like `DP + 15 V`, `utils.get_latest_DP()` scans recent files for the
selected chip/sample and substitutes the most recent measured Dirac point. If
none is found, it falls back to `0 V`. See
[Tutorial 2](../tutorials/02-experiment-window.md#special-parameter-the-dynamic-gate-voltage).

## The parameters database {#the-parameters-database}

To analyze many runs at once, build a SQLite database from your CSV headers:

```bash
uv run laser_setup parameters_to_db
```

This walks `data/*.csv`, creates one table per procedure type, and inserts a row
per file with all of its parameters (adding columns dynamically as new
parameters appear). The database name comes from `Dir.database` (default
`database.db`, relative to the data directory).

Browse it inside the app via **View → Database**, which opens the
`SQLiteWidget` — a sortable, read-only table view. This makes it easy to find,
say, every `It` run on a given chip at a given gate voltage.

## Plots and styling

Live plots use [pyqtgraph](https://www.pyqtgraph.org/); exported/Matplotlib
figures follow `matplotlib_rcParams` from the config (grid on, autolayout). The
first two `DATA_COLUMNS` are the default x/y axes, configurable in the experiment
window.

## Logs

Two log streams are configured under `Logging`:

- **Console** — colorized, level `INFO`, for live feedback.
- **File** — `log/laser_setup.log`, level `DEBUG`, for post-mortem debugging.

Adjust levels in the `Logging` section of `config.yaml`. The live log is also
visible in the GUI (experiment window Log tab, or **View → Logs**).
