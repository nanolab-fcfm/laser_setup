# Defining Parameters

Parameters are the typed inputs of a procedure. Laser Setup defines reusable
parameters once in `parameters.yaml` and references them from procedures, so
units, limits and descriptions stay consistent everywhere.

## PyMeasure parameter types

Parameters are PyMeasure objects. The types you'll use:

| Type | For | Example |
| --- | --- | --- |
| `FloatParameter` | real numbers (with units) | `vds`, `laser_v` |
| `IntegerParameter` | integers | `chip_number`, `N_avg` |
| `BooleanParameter` | on/off toggles | `laser_toggle` |
| `ListParameter` | a dropdown of choices | `chip_group`, `laser_wl` |
| `Parameter` | free text / expressions | `info`, `vg` (`"DP + 0 V"`) |
| `Metadata` | computed values saved but not entered | `start_time` |

## The `parameters.yaml` schema

Parameters are grouped under categories (`Chip`, `Laser`, `Instrument`,
`Control`). Each entry uses a `_target_` to select the PyMeasure type — the file
defines YAML anchors at the top so you can write `*FloatParameter` instead of the
full path:

```yaml
_types:
  - &Parameter pymeasure.experiment.Parameter
  - &BooleanParameter pymeasure.experiment.BooleanParameter
  - &IntegerParameter pymeasure.experiment.IntegerParameter
  - &FloatParameter pymeasure.experiment.FloatParameter
  - &ListParameter pymeasure.experiment.ListParameter
  - &Metadata pymeasure.experiment.Metadata

Control:
  vds:
    _target_: *FloatParameter
    default: 0.075
    name: VDS
    description: Drain-Source voltage
    units: V
    minimum: -210.
    maximum: 210.
    decimals: 10

  vg_toggle:
    _target_: *BooleanParameter
    default: true
    name: VG toggle

  vg:
    _target_: *FloatParameter
    default: 0.
    name: VG
    units: V
    minimum: -100.
    maximum: 100.
    group_by: vg_toggle      # only shown when vg_toggle is on
```

### Supported keys

| Key | Meaning |
| --- | --- |
| `_target_` | The parameter class (use the anchors). |
| `default` | Default value. |
| `name` | Label shown in the GUI and written to the file. |
| `description` | Tooltip/help text. |
| `units` | Unit string (appended to the value). |
| `minimum` / `maximum` | Numeric bounds. |
| `decimals` | Display precision. |
| `choices` | Options for a `ListParameter`. |
| `group_by` | Show/hide based on another (boolean) parameter. |
| `fget` | For `Metadata`: attribute/function providing the value. |

### Grouping with `group_by`

`group_by` ties a parameter's visibility to a boolean. Two forms:

```yaml
laser_wl:
  group_by: laser_toggle               # simple: show when laser_toggle is true

step_time:
  group_by: show_more                  # advanced inputs hidden until "Show more"
```

Procedures also use `group_by: {}` in `procedures.yaml` to *clear* a grouping
inherited from the shared definition.

## Using parameters in a procedure

`laser_setup/procedures/utils.py` exposes the instantiated parameters as
`Parameters`, organized by category. Assign them as class attributes:

```python
from .utils import Parameters

class It(ChipProcedure):
    vds = Parameters.Control.vds
    laser_v = Parameters.Laser.laser_v
    NPLC = Parameters.Instrument.NPLC
```

!!! note "Why a deep copy?"
    `Parameters` is a `DeepCopyDictConfig`, so each access returns a *fresh*
    parameter object. That prevents two procedures from accidentally sharing
    (and mutating) the same parameter instance.

You can equally define parameters **inline** (as in the
[Creating a Procedure](creating-a-procedure.md) example) — handy for one-off
inputs that don't belong in the shared file.

## Overriding parameter defaults per procedure

`procedures.yaml` overrides defaults without code. Under a procedure's
`parameters:` key, set any parameter attribute:

```yaml
It:
  parameters:
    procedure_version: {value: 2.2.0}
    laser_T: {value: 120., group_by: {}}
    vg: {value: "DP + 0. V"}
```

`value` sets the default; other keys (`units`, `minimum`, `group_by`, `choices`,
…) patch the parameter object. This is applied by `BaseProcedure.configure_class`
via the [`@configurable`](internals.md) machinery.

## `INPUTS`, `EXCLUDE`, `DATA_COLUMNS`, `SEQUENCER_INPUTS`

These class lists tie parameters to behavior:

- **`INPUTS`** — which parameters appear as inputs, in order. Build on the base:
  `INPUTS = ChipProcedure.INPUTS + ['vds', 'vg', ...]`.
- **`EXCLUDE`** — parameters omitted from the saved file header (e.g. transient
  toggles).
- **`DATA_COLUMNS`** — output column names; the first two are the default plot
  axes. You can append an instrument's columns:
  `DATA_COLUMNS = ['t (s)', 'I (A)'] + PT100SerialSensor.DATA_COLUMNS`.
- **`SEQUENCER_INPUTS`** — parameters a sequence may sweep.

See the [Procedure catalog reference](../reference/procedures.md) for how the
built-ins combine these.
