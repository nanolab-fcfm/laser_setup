# Adding an Instrument

To support a new piece of hardware you write a PyMeasure `Instrument` class, then
declare it in `instruments.yaml`. Procedures can then queue it like any other.

!!! tip "Check PyMeasure first"
    The [PyMeasure instrument library](https://pymeasure.readthedocs.io/en/latest/api/instruments/index.html)
    already covers many devices. If yours is there, you may only need a YAML
    entry pointing `target` at the existing class (as Laser Setup does for
    `ThorlabsPM100USB`).

## 1. Write the instrument class

Instruments live in `laser_setup/instruments/`. A PyMeasure instrument exposes
**controls** (read/write properties) and **measurements** (read-only) via
`Instrument.control(...)` / `Instrument.measurement(...)`, which map to SCPI-like
commands.

```python title="laser_setup/instruments/mydevice.py"
import logging

from pymeasure.instruments import Instrument, SCPIMixin

log = logging.getLogger(__name__)


class MyDevice(SCPIMixin, Instrument):
    """Driver for the Acme Widget 9000."""

    def __init__(self, adapter, name="Acme Widget 9000", **kwargs):
        super().__init__(adapter, name, **kwargs)

    # read/write property → 'VOLT?' to read, 'VOLT %g' to set
    voltage = Instrument.control(
        "VOLT?", "VOLT %g",
        """Output voltage in volts.""",
        validator=lambda v, vs: max(min(v, 10.0), 0.0),
    )

    # read-only measurement
    reading = Instrument.measurement(
        "MEAS?", """The latest sensor reading.""",
    )

    def shutdown(self):
        self.voltage = 0          # leave the device safe
        super().shutdown()
```

### Connection types

The `adapter` argument determines how the device is reached. PyMeasure picks the
backend from the adapter string/object:

- **VISA** (USB/GPIB): pass a resource string like
  `USB0::0x1313::0x8078::P0037982::INSTR`. Requires a VISA backend.
- **Serial**: pass a COM port; PyMeasure wraps it in a `SerialAdapter`. Set
  `read_termination` / `write_termination` to match the firmware (see
  `Clicker`/`PT100SerialSensor` in `instruments/serial.py`).
- **Proprietary**: override `__init__` to swap in a custom adapter object — the
  `Bentham` class replaces `self.adapter` with a `bendev.Device` for its USB
  protocol.

!!! note "Custom `shutdown()`"
    `InstrumentManager.shutdown_all()` calls each instrument's `shutdown()`.
    Implement it to return the device to a safe state (zero the output, turn off
    a lamp). It's skipped automatically for debug/fake instruments.

## 2. Export it (optional)

Re-export from `laser_setup/instruments/__init__.py` so procedures can import it
by name:

```python
from .mydevice import MyDevice
```

## 3. Declare it in `instruments.yaml`

```yaml
MyDevice:
  adapter: USB0::0x1234::0x5678::SN12345::INSTR
  name: Acme Widget 9000
  IDN: ACME,WIDGET9000           # used by setup_adapters to recognize it
  target: ${class:laser_setup.instruments.mydevice.MyDevice}
  kwargs:
    # any extra constructor args, e.g. termination for serial devices
    timeout: 5000
```

`${class:...}` resolves the dotted path to the class at config-load time. The
`Instruments` helper in `procedures/utils.py` then exposes `Instruments.MyDevice`.

## 4. Use it in a procedure

```python
from ..instruments import InstrumentManager, MyDevice
from .utils import Instruments

class MyMeasurement(BaseProcedure):
    instruments = InstrumentManager()
    widget: MyDevice = instruments.queue(**Instruments.MyDevice)

    def startup(self):
        self.connect_instruments()
        self.widget.voltage = 1.0

    def execute(self):
        self.emit('results', {'value': self.widget.reading})
```

## 5. Test without hardware

Because the queue/connect flow falls back to a `DebugInstrument` under `-d`, you
can exercise the whole procedure before the device arrives:

```bash
uv run laser_setup -d MyMeasurement
```

For finer control, give the YAML entry `kwargs: {debug: true}` so it always uses
the debug instrument.

## Gotchas

- **Termination characters** must match the firmware for serial devices, or
  reads hang or return garbage.
- **VISA backend required** for USB/GPIB devices — install NI-VISA or
  `pyvisa-py` ([details](../getting-started/installation.md#visa-backend)).
- **Instance caching:** the manager caches by `f"{Class}/{adapter}"`. Two
  procedures with the same class+adapter share one connection, which is great for
  reuse but means state can carry over — reset in `startup()`.
- **`help()`:** `InstrumentManager.help(MyDevice)` prints the available controls
  and measurements — handy while developing.

See [Instruments](../user-guide/instruments.md) for the runtime lifecycle.
