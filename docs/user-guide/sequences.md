# Sequences

A **sequence** runs several procedures in order from a single window. They
encode measurement *protocols* — e.g. *IVg → It → IVg → Wait → IVg* — so a whole
experiment runs unattended. Sequences are defined in `sequences.yaml`.

See [Tutorial 3](../tutorials/03-sequences.md) for a hands-on walkthrough.

## Defining a sequence

```yaml
TestSequence:
  name: Test Sequence
  description: Runs FakeProcedure, Wait
  common_procedure: ${class:laser_setup.procedures.ChipProcedure}
  inputs_ignored: ['show_more', 'skip_startup', 'skip_shutdown']
  procedures:
  - FakeProcedure
  - Wait
```

| Key | Meaning |
| --- | --- |
| `name` | Label in the Sequences menu. |
| `description` | Shown in the sequence window. |
| `common_procedure` | A base procedure whose inputs are shared across all steps (entered once). |
| `inputs_ignored` | Common inputs to hide from the shared panel. |
| `procedures` | Ordered list of steps (procedure names, with optional overrides). |

Every sequence must also be registered under `_types` using the `${sequence:...}`
resolver:

```yaml
_types:
  TestSequence: ${sequence:TestSequence}
  MainSequence: ${sequence:MainSequence}
```

`${sequence:Name}` dynamically builds a `Sequence` subclass from the named block.

## Common vs. per-step parameters

The `common_procedure` provides inputs that apply to every step — typically the
chip identity (`chip_group`, `chip_number`, `sample`). You set them once in the
top panel. Each step also exposes the parameters that are unique to it.

## Overriding parameters per step

A step can be a bare name (`- It`) or a mapping that overrides parameters for
that step only:

```yaml
procedures:
- IVg:
    parameters:
      laser_wl: {group_by: {laser_toggle: true}}
- It:
    parameters:
      skip_startup: {value: false}
      vds: {value: 0.75}
      vg:  {value: "40."}
```

Override values follow the same schema as `procedures.yaml` (a `value` plus any
parameter attributes). YAML anchors (`&name` / `*name`) are handy to reuse a
value across steps — see `ItMadness` in the template.

## Parameter sweeps with `sequencer`

A step can expand into **many runs** by sweeping a parameter, using PyMeasure's
sequencer syntax:

```yaml
- It:
    sequencer: |-
      - "target_T", "arange(35., 71., 5)"
    parameters:
      skip_startup: {value: true}
      vg:  *v_g
      vds: *v_ds
```

This runs `It` once per value of `target_T` in `arange(35, 71, 5)`. A parameter
is sweepable only if it appears in the procedure's `SEQUENCER_INPUTS`.

## Running and aborting

In the **Sequence Window** each step shows a color-coded status icon and two
timers (`+` time in step, `=` cumulative). Steps run one at a time. If a step
fails, an **abort dialog** appears with a countdown
(`Qt.SequenceWindow.abort_timeout`, default 30 s); it auto-continues if you
don't respond, or aborts the whole sequence if you confirm.

!!! warning "Startup/shutdown across steps"
    Instruments shut down **after the last step**, not between steps, so adjacent
    procedures can reuse a connected, warmed-up instrument. Steps use
    `skip_startup` / `skip_shutdown` to control re-initialization. If you set
    `skip_shutdown: true` on a step, make sure a later step (or the sequence
    end) leaves the hardware in a safe state.

## Built-in sequences

| Sequence | Steps | Purpose |
| --- | --- | --- |
| `TestSequence` | `FakeProcedure → Wait` | Hardware-free demo. |
| `MainSequence` | `IVg → It → IVg → Wait → IVg` | Standard LED measurement flow. |
| `ItMadness` | `IVg → It (T-sweep) → IVg` | Temperature-sweep example with `sequencer` and anchors. |

## Related

- [Procedures](procedures.md) — what each step does.
- [Registering in YAML](../developer-guide/registering.md) — adding your own
  sequences.
- [Lab Protocols](../protocols/index.md) — the real measurement recipes these
  sequences implement.
