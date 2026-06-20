# The Graphical Interface

The GUI is built with **PyQt6** (through [`qtpy`](https://github.com/spyder-ide/qtpy)
for cross-toolkit compatibility) and reuses PyMeasure's managed-window machinery.
It lives in `laser_setup/display/`. There are three windows and a handful of
reusable widgets, all driven by `CONFIG.Qt`.

## Entry point: `display_window()`

`display/app.py:display_window(procedure=None)` is the single GUI entry point.
It:

- creates the `QApplication` singleton,
- shows the **splash screen**,
- applies the configured **style, palette (dark mode) and font** from
  `CONFIG.Qt.GUI`,
- installs a global **`ShortcutFilter`** for keyboard shortcuts, and
- opens either the **MainWindow** (no procedure) or an **ExperimentWindow** (a
  procedure class/instance).

| Shortcut | Action |
| --- | --- |
| ++ctrl+w++ | Close the current window |
| ++ctrl+plus++ / ++ctrl+minus++ | Zoom in / out |
| ++f11++ | Toggle maximize |

## Main Window

`display/windows/main_window.py` is the hub. Its menu bar is generated entirely
from configuration:

| Menu | Built from | Opens |
| --- | --- | --- |
| **Procedures** | `CONFIG.procedures._types` | an `ExperimentWindow` (++ctrl+1++, ++ctrl+2++ …) |
| **Sequences** | `CONFIG.sequences._types` | a `SequenceWindow` (++ctrl+shift+1++ …) |
| **Scripts** | `CONFIG.scripts` | runs a function (++alt+1++ …) |
| **View** | — | database browser, camera, terminal, logs |
| **Config** | — | edit / import / export configuration |
| **Help** | `CONFIG.instruments` | per-instrument docstrings |

It also shows the project **README** in the central panel and a status bar with
a red **Reload** button (++ctrl+r++) that becomes active when configuration
changes. A background `Worker` thread polls a status message periodically.

!!! note "Why a Reload button?"
    `CONFIG` is read once at startup. Editing config (in a file or via the
    Config editor) requires a reload to rebuild it, which restarts the window.

## Experiment Window

`display/windows/experiment_window.py` subclasses PyMeasure's
`ManagedWindowBase` and runs **one** procedure with live visualization.

On construction it validates that the procedure has at least two
`DATA_COLUMNS` (the first two become the default x/y axes) and builds:

- a **Plot** widget (x vs y, with axis selectors),
- a **Dock** of stacked plots (`Qt.ExperimentWindow.dock_plot_number`),
- a **Log** widget capturing the run's log records,
- a **Text/Info** widget rendering `Qt.ExperimentWindow.info_file` (Markdown).

When you press **Queue**:

1. a `Results` object is created with a unique filename
   (see [Data & Output Files](data-and-output.md)),
2. the procedure's `patch_parameters()` hook runs,
3. PyMeasure's manager runs `startup() → execute() → shutdown()` in a background
   thread, streaming `emit('results', …)` to the plots and `emit('progress', …)`
   to the progress bar.

Procedures derived from `BaseProcedure` also get a **Shutdown** button that calls
`instruments.shutdown_all()` for a safe power-down.

!!! warning "Dark-mode plots"
    In dark mode the plot backgrounds are set to black explicitly, because
    pyqtgraph defaults to a white canvas (which would hide light-colored
    curves).

## Sequence Window

`display/windows/sequence_window.py` runs a **chain** of procedures. It reads a
`Sequence` class (`.procedures`, `.common_procedure`, `.inputs_ignored`) and
builds:

- a **common-parameter** panel (inputs shared by all steps), and
- a column per step with its unique inputs, a color-coded **status icon**, and
  two **timers** (time-in-step `+` and cumulative `=`).

`Queue` runs each step in order using a blocking event loop (the window stays
responsive to abort but processes steps sequentially). On failure it shows an
**abort dialog** with a countdown (`Qt.SequenceWindow.abort_timeout`). Instruments
are shut down **after the final step**. See [Sequences](sequences.md).

## Widgets

`display/widgets/` provides the reusable pieces:

| Widget | Role |
| --- | --- |
| `InputsWidget` | Parameter input form (wraps PyMeasure's, accepts a class or instance). |
| `LogWidget` / `LogsWidget` | Live, colorized log capture. |
| `TextWidget` | Read-only Markdown/text viewer (the Info tab, README). |
| `SQLiteWidget` | Browse the parameters database in a sortable table. |
| `ConfigWidget` | Edit `CONFIG` as a parameter tree and save back to YAML. |
| `CameraWidget` | Live camera feed (OpenCV) — e.g. to watch the sample/laser spot. |

## Threading model

- **PyMeasure's manager** runs each procedure in its own background thread, so
  the GUI stays responsive during a measurement.
- The **`Worker`** helper (`display/Qt.py`) runs short background tasks (camera
  scanning, status polling) on a `QThread` and signals completion.
- The **SequenceWindow** intentionally drives steps from a blocking event loop
  so it can monitor them one at a time.

## Configuration cheat-sheet

All window behavior is under `CONFIG.Qt`:

```yaml
Qt:
  GUI: {style, dark_mode, font, font_size, splash_image}
  MainWindow: {title, readme_file, size, widget_size, icon}
  ExperimentWindow: {title, inputs_in_scrollarea, dock_plot_number, info_file, icon}
  SequenceWindow: {abort_timeout}
```

See the [Configuration reference](../reference/configuration.md) for defaults.
