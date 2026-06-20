# Tutorial 2 · The Experiment Window

**Goal:** understand every part of the experiment window so you can drive any
procedure. **Time:** ~10 minutes. **Hardware:** none (we'll use `-d`).

!!! abstract "What you'll learn"
    - How parameters, `show_more`, and grouped inputs work.
    - The plot, dock (multi-plot), log and info tabs.
    - Live estimates, aborting, and re-running with different parameters.

Open a realistic procedure in debug mode:

```bash
uv run laser_setup -d It
```

## The anatomy of the window

```text
┌───────────────────────────────────────────────────────────┐
│  Inputs            │            Plot (x vs y)              │
│  ───────           │                                       │
│  Chip group   ▼    │        ╭─────────────────────╮        │
│  Chip number       │        │       live curve     │        │
│  Sample       ▼    │        ╰─────────────────────╯        │
│  VDS               │   [ Plot | Dock | Log | Info ] tabs   │
│  VG …              ├───────────────────────────────────────┤
│  ☐ Show more       │  Browser: queued / finished runs      │
│  [ Queue ] [Abort] │  Log: live messages                   │
└───────────────────────────────────────────────────────────┘
```

## Inputs and the `Show more` toggle

The left panel lists this procedure's `INPUTS`. Some inputs are **grouped**:
they only appear when a controlling checkbox is on. Two patterns you'll meet
constantly:

- **`Show more`** — reveals advanced/rarely-changed parameters (e.g. `NPLC`,
  `Sampling time`). Tick it to see them.
- **Feature toggles** — e.g. `VG toggle` reveals the gate-voltage inputs, and
  `Laser toggle` reveals the laser inputs. Turning a toggle *off* also tells the
  procedure to **disable** the corresponding instrument at runtime.

!!! info "Why toggles disable instruments"
    Procedures override `connect_instruments()` to call
    `self.instruments.disable(self, 'tenma_laser')` when `laser_toggle` is off,
    so the unused instrument is never contacted. See
    [Instruments](../user-guide/instruments.md).

Try it: tick **Show more**, then toggle **Laser toggle** on and off and watch the
laser inputs appear and disappear.

## Special parameter: the dynamic gate voltage

`It` has a **VG** input that accepts an *expression*, not just a number. Its
default is:

```text
DP + 0. V
```

`DP` means "the sample's previously measured **Dirac Point**". Before the run,
the procedure looks up the latest Dirac point for the selected chip/sample and
substitutes it in. If none exists, it falls back to `0 V`. You can write things
like `DP + 15 V` or `-30 V`.

!!! note
    This substitution happens in `patch_parameters()` via the `VgMixin`. It's a
    good example of how procedures can transform inputs right before measuring.

## The tabs

Switch between the tabs above the plot:

- **Plot** — the primary `x` vs `y` graph. The first two `DATA_COLUMNS` are the
  default axes; you can change them with the axis selectors.
- **Dock** — several stacked plots at once (handy when a procedure emits many
  columns, e.g. current *and* temperature). The number of dock plots is set by
  `Qt.ExperimentWindow.dock_plot_number`.
- **Log** — the live log for this run (instrument messages, warnings, aborts).
- **Info** — renders a Markdown file (the LED protocol by default), so you can
  keep the measurement recipe next to the controls. Set with
  `Qt.ExperimentWindow.info_file`.

## Run it and read the estimates

Press **Queue**. While it runs:

- The **progress bar** advances (the procedure calls `emit('progress', %)`).
- The **plot** updates as `emit('results', …)` fires.
- Some procedures show **live estimates** (e.g. averages). `FakeProcedure` shows
  a "Data average"; `IVg` estimates the Dirac point.

## Abort and re-run

- Click **Abort** to stop early. Internally the procedure checks
  `self.should_stop()` in its loop and exits cleanly, then `shutdown()` runs.
- Change any input and click **Queue** again to start a new run. Each run is a
  new row in the **Browser** and a new file on disk.

!!! tip "The Shutdown button"
    Procedures derived from `BaseProcedure` show a **Shutdown** button that
    forces `instruments.shutdown_all()` — useful to safely power down sources if
    a run ended abnormally.

## Recap

- Inputs map to the procedure's `INPUTS`; `Show more` and toggles reveal grouped
  parameters and control which instruments are used.
- Plot / Dock / Log / Info tabs give you live data, multi-plots, messages and
  your recipe side by side.
- `DATA_COLUMNS` drives the plot axes and the saved file columns.

Next: chaining procedures with sequences →
[Tutorial 3: Running a Sequence](03-sequences.md).
