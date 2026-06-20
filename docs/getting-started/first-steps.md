# First Steps

You've [installed](installation.md) Laser Setup. Let's launch it, understand
what you're looking at, and run something — all **without any hardware**.

## 1. Launch the main window

From the repository folder:

```bash
uv run laser_setup
```

The **Main Window** opens. It is the *hub* of the application, built entirely
from your configuration. From its menu bar you can:

- **Procedures** — open an experiment window to run a single measurement.
- **Sequences** — run several procedures back-to-back.
- **Scripts** — utility actions (create config, detect instruments, check for
  updates…).
- **View** — open the live log, a database browser, a camera viewer, or a
  Python terminal.
- **Config** — edit your configuration from within the app.

!!! success "It works out of the box"
    On a fresh clone there is no `config/` folder yet, so the app loads its
    **built-in defaults**. That already includes every measurement procedure
    (`It`, `IVg`, `IV`, … and the demo `FakeProcedure`) and the example
    sequences. You can start exploring immediately.

## 2. Run your first (simulated) experiment

You don't need to click through menus to start — you can open a procedure
directly. Let's run the **debug-friendly demo procedure**:

```bash
uv run laser_setup FakeProcedure
```

An **Experiment Window** opens. `FakeProcedure` generates synthetic data, so it
needs no instruments at all. Press **Queue** and watch the plot fill in over a
few seconds.

That's a complete measurement run: parameters in, live plot + log, data written
to disk. The [Tutorials](../tutorials/index.md) build on exactly this.

## 3. Debug mode (simulate real instruments)

Real procedures like `It` or `IVg` *do* expect instruments. To run them with no
hardware, add the **`-d` / debug flag**:

```bash
uv run laser_setup -d It
```

In debug mode, any instrument that fails to connect is transparently replaced by
a **`DebugInstrument`** that returns random values. This lets you exercise the
full GUI, plotting, sequencing and data-saving pipeline on your laptop.

!!! info "What debug mode does"
    The `-d` flag sets `debug=True` on every instrument. When a real connection
    can't be made, the manager substitutes a fake instrument instead of raising
    an error. See [Instruments](../user-guide/instruments.md#debug-mode) for
    details.

## 4. Create your own configuration

Sooner or later you'll want to change parameter defaults, rename chip groups, or
point instruments at your COM ports. To get an **editable, local configuration**,
run the *Init Config* script:

```bash
uv run laser_setup init
```

This creates, in your current folder:

```text
config/
├── config.yaml          # your global settings (start editing here)
└── templates/           # pristine copies of every config file
    ├── config.yaml
    ├── parameters.yaml
    ├── procedures.yaml
    ├── sequences.yaml
    └── instruments.yaml
```

!!! danger "Important: copy the templates you want to use"
    The generated `config/config.yaml` points its procedure, sequence and
    instrument files at `./config/procedures.yaml`, `./config/sequences.yaml`
    and `./config/instruments.yaml` — **which don't exist yet**. Until you
    create them, the Procedures and Sequences menus will be **empty**.

    Copy the templates you intend to customize up one level into `config/`:

    === "macOS / Linux"

        ```bash
        cp config/templates/{procedures,sequences,instruments,parameters}.yaml config/
        ```

    === "Windows (PowerShell)"

        ```powershell
        Copy-Item config\templates\procedures.yaml,config\templates\sequences.yaml,`
                  config\templates\instruments.yaml,config\templates\parameters.yaml config\
        ```

    Now your menus are populated again — and editable. Re-launch the app (or
    click **Reload**) to pick up changes.

You can confirm what's loaded at any time:

```bash
uv run laser_setup --help     # lists every procedure & script it recognizes
```

The [Configuration System](../user-guide/configuration.md) guide explains the
full layering (defaults → global → local) and every key you can set.

## 5. Where your data goes

Each run writes a CSV file under the **data directory** (default `./data`),
organized by date, with all parameters stored in the file header so the
measurement is reproducible:

```text
data/2026-06-21/FakeProcedure2026-06-21_1.csv
```

See [Data & Output Files](../user-guide/data-and-output.md) for the naming
scheme and how to turn a folder of CSVs into a queryable SQLite database.

## You're ready

You can now launch the app, run procedures (real or simulated), and create a
configuration. Next:

<div class="grid cards" markdown>

-   :material-school: **Tutorials**

    A guided, hands-on path that teaches the software through small experiments.

    [:octicons-arrow-right-24: Start Tutorial 1](../tutorials/01-first-experiment.md)

-   :material-book-open-variant: **User Guide**

    Reference-style explanations of every subsystem.

    [:octicons-arrow-right-24: Read the User Guide](../user-guide/index.md)

</div>
