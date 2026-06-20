# Creating a New Procedure

This is the page you came for: how to add a **new experiment**. We'll build one
from nothing, run it without hardware, then grow it into a real instrument-driven
device measurement. Every snippet is complete and copy-pasteable.

!!! abstract "The checklist"
    To create a procedure you:

    1. **Subclass** `BaseProcedure` (or `ChipProcedure` for device measurements).
    2. Declare **parameters** and `INPUTS`.
    3. Declare `DATA_COLUMNS`.
    4. Queue any **instruments** you need.
    5. Implement `startup()`, `execute()`, `shutdown()`.
    6. **Register** it in `procedures.yaml` so the app can find it.

## 1. A minimal procedure (no hardware)

Create `laser_setup/procedures/CountUp.py`:

```python title="laser_setup/procedures/CountUp.py"
import logging
import time

from pymeasure.experiment import FloatParameter, IntegerParameter

from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CountUp(BaseProcedure):
    """A teaching procedure: emit a noisy ramp for `n_points` steps."""
    name = 'Count Up'

    # --- Parameters (shown as inputs) ---
    n_points = IntegerParameter('Number of points', default=50, minimum=1)
    step_time = FloatParameter('Step time', units='s', default=0.1, minimum=0.)

    # --- GUI inputs (order matters) ---
    INPUTS = BaseProcedure.INPUTS + ['n_points', 'step_time']

    # --- Output columns (first two are the default plot axes) ---
    DATA_COLUMNS = ['i', 'value']

    def execute(self):
        log.info("Counting up to %d", self.n_points)
        for i in range(self.n_points):
            if self.should_stop():               # (1) makes Abort work
                log.warning('Aborted')
                break
            value = i + (hash(time.time()) % 100) / 100   # ramp + noise
            self.emit('results', dict(zip(self.DATA_COLUMNS, [i, value])))  # (2)
            self.emit('progress', 100 * (i + 1) / self.n_points)            # (3)
            time.sleep(self.step_time)
```

1. **Always** poll `self.should_stop()` in your loop so the **Abort** button
   works and sequences can interrupt cleanly.
2. `emit('results', …)` streams one data row; the dict keys **must** match
   `DATA_COLUMNS`.
3. `emit('progress', …)` drives the progress bar (0–100).

We didn't override `startup()`/`shutdown()` — the `BaseProcedure` defaults
(connect/disconnect instruments) are fine, and there are no instruments here.

## 2. Register it

The app discovers procedures from the `_types` map in `procedures.yaml`. Add a
line (in `config/procedures.yaml` for your local setup, or the bundled template):

```yaml
_types:
  # … existing entries …
  CountUp: ${class:laser_setup.procedures.CountUp.CountUp}
```

!!! tip "Two ways to reference the class"
    `${class:laser_setup.procedures.CountUp.CountUp}` points at the file
    directly. If you also re-export it from `procedures/__init__.py`
    (`from .CountUp import CountUp`), you can use the shorter
    `${class:laser_setup.procedures.CountUp}`. The bundled procedures use the
    short form; `FakeProcedure` uses the long form.

Now run it — no hardware, no `-d` needed:

```bash
uv run laser_setup CountUp
```

Press **Queue** and watch your noisy ramp. 🎉 That's a complete new experiment.

## 3. Add an instrument

Let's measure a real current instead of faking one. Queue a Keithley 2450 and
use it in the lifecycle. Replace the body with:

```python title="laser_setup/procedures/CountUp.py (with an instrument)"
import logging
import time

from pymeasure.experiment import FloatParameter, IntegerParameter

from ..instruments import InstrumentManager, Keithley2450
from .BaseProcedure import BaseProcedure
from .utils import Instruments       # instrument configs from instruments.yaml

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CountUp(BaseProcedure):
    """Sample the Keithley current `n_points` times."""
    name = 'Count Up'

    # --- Instruments (queued, not yet connected) ---
    instruments = InstrumentManager()
    meter: Keithley2450 = instruments.queue(**Instruments.Keithley2450)

    n_points = IntegerParameter('Number of points', default=50, minimum=1)
    step_time = FloatParameter('Step time', units='s', default=0.1, minimum=0.)
    vds = FloatParameter('VDS', units='V', default=0.1)

    INPUTS = BaseProcedure.INPUTS + ['vds', 'n_points', 'step_time']
    DATA_COLUMNS = ['i', 'I (A)']

    def startup(self):
        self.connect_instruments()        # turns the proxy into a real meter
        self.meter.reset()
        self.meter.apply_voltage()
        self.meter.measure_current()
        self.meter.source_voltage = self.vds
        self.meter.enable_source()

    def execute(self):
        for i in range(self.n_points):
            if self.should_stop():
                break
            current = self.meter.current      # read the instrument
            self.emit('results', dict(zip(self.DATA_COLUMNS, [i, current])))
            self.emit('progress', 100 * (i + 1) / self.n_points)
            time.sleep(self.step_time)

    # shutdown() inherited from BaseProcedure → instruments.shutdown_all()
```

Run it **in debug mode** so the Keithley is simulated:

```bash
uv run laser_setup -d CountUp
```

The `DebugInstrument` returns random values for `.current`, so you get a working
run without a real meter. Drop `-d` once you have hardware and a correct
`instruments.yaml`.

!!! info "How the instrument connects"
    `instruments.queue(...)` stores config in a proxy at class-definition time.
    `connect_instruments()` (called in `startup`) replaces the proxy with a live
    `Keithley2450` — or a `DebugInstrument` under `-d`. See
    [Instruments](../user-guide/instruments.md).

## 4. Make it a device measurement

If the measurement is tied to a chip/sample, subclass **`ChipProcedure`** instead
of `BaseProcedure`. You automatically get the `chip_group`, `chip_number` and
`sample` inputs (recorded in every file) and a Telegram "finished" alert:

```python
from .ChipProcedure import ChipProcedure

class CountUp(ChipProcedure):
    ...
    INPUTS = ChipProcedure.INPUTS + ['vds', 'n_points', 'step_time']
```

For optional instruments, override `connect_instruments()` to disable what you
don't need (so the same procedure runs with or without, say, the laser):

```python
def connect_instruments(self):
    if not self.sense_T:
        self.instruments.disable(self, 'temperature_sensor')
    super().connect_instruments()
```

## 5. Use shared parameters from YAML (recommended)

Rather than redefining `vds`, `NPLC`, etc. inline, pull the canonical
definitions (units, limits, descriptions) from `parameters.yaml`:

```python
from .utils import Parameters

class CountUp(ChipProcedure):
    vds = Parameters.Control.vds          # FloatParameter defined once in YAML
    Irange = Parameters.Instrument.Irange
    NPLC = Parameters.Instrument.NPLC
```

This keeps every procedure consistent. See
[Defining Parameters](parameters.md) for the schema and the available
categories (`Chip`, `Laser`, `Instrument`, `Control`).

## 6. Optional niceties

| Hook / attribute | What it does |
| --- | --- |
| `get_estimates()` | Return `[(label, value), …]` shown live in the window (e.g. a running average or an estimated Dirac point). |
| `patch_parameters()` | Transform inputs right before a run (e.g. resolve `DP + 15 V` like `VgMixin` does). |
| `EXCLUDE` | Parameter names to leave out of the saved file header. |
| `SEQUENCER_INPUTS` | Parameters a [sequence](../user-guide/sequences.md) is allowed to sweep. |
| `DATA_COLUMNS` order | First two columns are the default plot axes; add more for the Dock tab. |

## 7. Lint and run the tests

```bash
uv run --group dev flake8 laser_setup/procedures/CountUp.py
uv run laser_setup -d CountUp
```

## Common mistakes

??? failure "The procedure doesn't appear in the menu"
    It isn't in `_types`, or your local `config/procedures.yaml` doesn't include
    it (remember the [blank-menu trap](../user-guide/configuration.md)). Check
    `uv run laser_setup --help`.

??? failure "`AttributeError` about DATA_COLUMNS / the window won't open"
    The experiment window needs **at least two** `DATA_COLUMNS`. Add a second
    column.

??? failure "Abort does nothing"
    Your `execute()` loop must check `self.should_stop()` regularly.

??? failure "Plot is empty"
    The keys you pass to `emit('results', …)` must exactly match `DATA_COLUMNS`.

## Where next

- [Defining Parameters](parameters.md) — make rich, reusable inputs.
- [Adding an Instrument](adding-an-instrument.md) — for hardware not yet
  supported.
- [Registering in YAML](registering.md) — procedures, sequences and scripts.
- [Procedures](../user-guide/procedures.md) — study `It` and `IVg` as real
  references.
