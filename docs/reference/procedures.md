# Procedure catalog

Built-in measurement procedures. For the class hierarchy and lifecycle see
[Procedures](../user-guide/procedures.md); to write your own see
[Creating a New Procedure](../developer-guide/creating-a-procedure.md).

!!! note "Authoritative source"
    A procedure's exact `INPUTS`, `DATA_COLUMNS` and defaults live in its source
    file under `laser_setup/procedures/` and may be overridden in
    `procedures.yaml`. The tables below summarize intent; check the source for
    the definitive list.

## Catalog

| Class | `name` | x → y | Key instruments | Source |
| --- | --- | --- | --- | --- |
| `IVg` | I vs Vg | Vg → I | Keithley, TENMA ×2 | `procedures/IVg.py` |
| `IV` | I vs V | Vsd → I | Keithley, TENMA | `procedures/IV.py` |
| `VVg` | V vs Vg | Vg → V | Keithley, Bentham | `procedures/VVg.py` |
| `It` | I vs t | t → I | Keithley, TENMA ×3, PT100, Clicker | `procedures/It.py` |
| `Vt` | V vs t | t → V | Keithley, TENMA, PT100 | `procedures/Vt.py` |
| `ItVg` | I vs t @ Vg | t → I | Keithley, TENMA | `procedures/ItVg.py` |
| `ItWl` | I vs t @ λ | t → I | Keithley, Bentham | `procedures/ItWl.py` |
| `Tt` | T vs t | t → T | Clicker, PT100 | `procedures/Tt.py` |
| `Pt` | P vs t | t → P | Thorlabs PM100 | `procedures/Pt.py` |
| `Pwl` | P vs λ | λ → P | Bentham, Thorlabs | `procedures/Pwl.py` |
| `LaserCalibration` | Laser calibration | Vlaser → P | TENMA, Thorlabs | `procedures/LaserCalibration.py` |
| `Stress` | Stress & relax | t → (I, T) | Keithley, TENMA, Clicker | `procedures/Stress.py` |
| `Wait` | Wait | — | none | `procedures/Wait.py` |
| `FakeProcedure` | Fake Procedure | t → fake | none | `procedures/FakeProcedure.py` |

Aliases for older configs: `IVT`→`IV`, `ITt`→`It`, `IVgT`→`IVg`.

## Parameter categories (`parameters.yaml`)

Most parameters come from shared categories. See
[Defining Parameters](../developer-guide/parameters.md).

| Category | Examples |
| --- | --- |
| `Chip` | `chip_group`, `chip_number`, `sample` |
| `Laser` | `laser_toggle`, `laser_wl`, `laser_v`, `laser_T`, `burn_in_t`, `fiber`, `wl`, `wl_start/end/step` |
| `Instrument` | `Irange`, `Vrange`, `NPLC`, `N_avg`, `sense_T`, `sensor` |
| `Control` | `vds`, `vg`, `vg_dynamic`, `vg_toggle`, `sampling_t`, `step_time`, `vg_start/end/step`, `vsd_start/end/step`, `vl_start/end/step`, `initial_T`, `target_T`, `T_start_t`, `T_start/end/step`, `t_on`, `t_off` |

## Common parameters (all procedures)

From `BaseProcedure`:

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `procedure_version` | `Parameter` | `1.0.0` | Versioning, often overridden in YAML. |
| `show_more` | `Boolean` | `false` | Reveals advanced (`group_by: show_more`) inputs. |
| `info` | `Parameter` | `None` | Free-text note saved to the file. |
| `skip_startup` | `Boolean` | `false` | Skip `startup()` (used by sequences). |
| `skip_shutdown` | `Boolean` | `false` | Skip `shutdown()`. |
| `start_time` | `Metadata` | — | `time.time()` at run start. |

`ChipProcedure` adds: `chip_group`, `chip_number`, `sample`.

## Example: `It` inputs

A concrete reference (from `procedures/It.py`):

```python
DATA_COLUMNS = ['t (s)', 'I (A)', 'VL (V)'] + PT100SerialSensor.DATA_COLUMNS
INPUTS = ChipProcedure.INPUTS + [
    'vds', 'Irange', 'vg_toggle', 'vg', 'laser_toggle', 'laser_wl', 'laser_v',
    'laser_T', 'sampling_t', 'sense_T', 'initial_T', 'target_T', 'T_start_t', 'NPLC',
]
EXCLUDE = ChipProcedure.EXCLUDE + ['vg_toggle', 'laser_toggle', 'sense_T']
SEQUENCER_INPUTS = ['vds', 'laser_v', 'vg', 'target_T']
```

Note `vg` accepts the dynamic expression `DP + <delta> V` (resolved by
`VgMixin`); `It` runs a three-phase laser off→on→off cycle whose total length is
`laser_T × 3/2`.

## Per-procedure version overrides

`procedures.yaml` pins each procedure's `procedure_version` and tweaks a few
defaults. See the template for the current values; e.g. `It` ships at `2.2.0`
with `laser_T: 120 s` and `vg: "DP + 0. V"`.
