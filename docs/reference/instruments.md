# Instrument catalog

Supported instruments and their default declarations. For the runtime lifecycle
see [Instruments](../user-guide/instruments.md); to add one see
[Adding an Instrument](../developer-guide/adding-an-instrument.md).

## Classes

| Logical name | Class | Hardware | Connection |
| --- | --- | --- | --- |
| `Keithley2450` | `laser_setup.instruments.keithley.Keithley2450` | Keithley 2450 SourceMeter | VISA |
| `Keithley6517B` | `laser_setup.instruments.keithley.Keithley6517B` | Keithley 6517B Electrometer | VISA |
| `TENMANEG` / `TENMAPOS` / `TENMALASER` | `laser_setup.instruments.tenma.TENMA` | TENMA 72-xxxx supplies | Serial |
| `ThorlabsPM100USB` | `pymeasure.instruments.thorlabs.ThorlabsPM100USB` | Thorlabs PM100D/USB | VISA |
| `Bentham` | `laser_setup.instruments.bentham.Bentham` | Bentham TLS120Xe light source | `bendev` USB |
| `PT100SerialSensor` | `laser_setup.instruments.serial.PT100SerialSensor` | RosaTech PT100 sensor | Serial |
| `Clicker` | `laser_setup.instruments.serial.Clicker` | RosaTech hot-plate controller | Serial |

## Default declarations (`instruments.yaml`)

```yaml
Keithley2450:
  adapter: USB0::0x05E6::0x2450::04448997::0::INSTR
  name: Keithley 2450
  IDN: KEITHLEY
  target: ${class:laser_setup.instruments.keithley.Keithley2450}

Bentham:
  adapter: COM6
  name: Bentham TLS120Xe
  IDN: USB\VID_04D8&PID_1705\41839/1
  target: ${class:laser_setup.instruments.bentham.Bentham}
  kwargs:
    manufacturer: Bentham
    vendor_id: 1240
    read_termination: \r\n\x00
    write_termination: \r\n\x00

TENMANEG: {adapter: COM3, IDN: "TENMA 72-2715 V6.6 SN:37793902", target: "${class:laser_setup.instruments.tenma.TENMA}"}
TENMAPOS: {adapter: COM4, IDN: "TENMA 72-2715 V6.6 SN:37793916", target: "${class:laser_setup.instruments.tenma.TENMA}"}
TENMALASER: {adapter: COM7, IDN: "TENMA 72-2715 V6.6 SN:37793899", target: "${class:laser_setup.instruments.tenma.TENMA}"}

ThorlabsPM100USB:
  adapter: USB0::0x1313::0x8078::P0037982::INSTR
  IDN: Thorlabs,PM100D,P0037982,2.8.1
  target: ${class:pymeasure.instruments.thorlabs.ThorlabsPM100USB}

PT100SerialSensor:
  adapter: COM8
  IDN: ROSATECH,TSN100,P0000002,1.0.1
  target: ${class:laser_setup.instruments.serial.PT100SerialSensor}

Clicker:
  adapter: COM8
  IDN: ROSATECH,CLK100,P0000003,1.0.0
  target: ${class:laser_setup.instruments.serial.Clicker}
```

!!! note
    `adapter` values are machine-specific. Run
    [`setup_adapters`](../user-guide/cli-and-scripts.md#setup_adapters) to
    auto-detect and rewrite them.

## Notable methods

### `Keithley2450`
- `make_buffer(name, size, mode)` / `clear_buffer()` — named trace buffers.
- `get_data()` → `[time, current]`; `get_time()`.
- `apply_voltage()`, `measure_current(current, nplc, auto_range)`,
  `enable_source()`.
- `shutdown()` plays a short triad before the base shutdown.

### `TENMA`
- `voltage` / `current` / `output` controls.
- `ramp_to_voltage(target, step, step_time)` — soft ramp to avoid overshoot.
- `apply_voltage(voltage, current, timeout)`.
- `shutdown()` ramps to 0 V then disables the output.

### `Bentham`
- `wavelength`, `goto`, `filt` (filter wheel), `lamp`, `output`.
- `source_current` / `source_voltage` (lamp PSU), `photocurrent`, `power`,
  `resistance`.
- Wraps `bendev.Device`; sends `SYST:REM` on connect; `shutdown()` turns the lamp
  off and closes the adapter.

### `PT100SerialSensor`
- Background daemon thread continuously polls; read `.data` →
  `(plate_T, ambient_T, clock)`.
- `DATA_COLUMNS = ['Plate T (degC)', 'Ambient T (degC)', 'Clock (ms)']`.

### `Clicker`
- `CT` (current temperature, read-only), `TT` (target).
- `set_target_temperature(T)` then `go()` to start heating.

## Debug & disabled instruments

- **`DebugInstrument`** — returned under `-d` when a real connection fails;
  yields random values.
- **`DisabledInstrument`** — substituted by `instruments.disable(self, 'name')`;
  silently ignores all commands. Used to skip optional hardware.

See [Instruments → Debug mode](../user-guide/instruments.md#debug-mode) and
[Disabling instruments](../user-guide/instruments.md#disabling).
