# Registering in YAML

For the app to *see* a procedure, sequence, script or instrument, it must be
registered in the appropriate YAML file. This page is the quick reference for all
four.

!!! warning "Edit the right file"
    Changes belong in your **local** `config/*.yaml` files (created by `init` and
    copied from `config/templates/`). Editing the bundled `assets/templates/*`
    only changes the *defaults* used when no local file exists. See the
    [Configuration System](../user-guide/configuration.md).

## Procedures → `procedures.yaml`

Register the class under `_types`, then optionally override parameters:

```yaml
# 1. Make it selectable
_types:
  CountUp: ${class:laser_setup.procedures.CountUp.CountUp}

# 2. (optional) Override defaults / attributes
CountUp:
  parameters:
    n_points: {value: 100}
    step_time: {value: 0.05}
  procedure_version: 1.0.0
```

- The `_types` key is what populates the **Procedures** menu and the CLI choices.
- A top-level block named exactly like the class applies overrides via the
  [`@configurable`](internals.md) machinery.

## Sequences → `sequences.yaml`

Define the sequence, then register it with the `${sequence:...}` resolver:

```yaml
MyFlow:
  name: My Flow
  description: IVg then CountUp
  common_procedure: ${class:laser_setup.procedures.ChipProcedure}
  inputs_ignored: ['show_more', 'skip_startup', 'skip_shutdown']
  procedures:
  - IVg
  - CountUp:
      parameters:
        n_points: {value: 200}

_types:
  MyFlow: ${sequence:MyFlow}
```

The referenced procedures must themselves be registered in `procedures.yaml`.
See [Sequences](../user-guide/sequences.md) for overrides and sweeps.

## Scripts → `config.yaml`

A script is any importable function, registered under `scripts:`:

```yaml
scripts:
  my_tool:
    name: "My Tool"                                   # menu label
    target: ${function:my_package.my_module.main}     # ${function:...} resolver
    kwargs:                                            # passed as **kwargs
      dry_run: true
```

- The function is called as `main(**kwargs)`. If it accepts a `parent` argument,
  the GUI passes the parent widget (for dialogs); the CLI passes `parent=None`.
- It becomes available both in the **Scripts** menu and as
  `uv run laser_setup my_tool`.

## Instruments → `instruments.yaml`

```yaml
MyDevice:
  adapter: USB0::0x1234::0x5678::SN::INSTR
  name: Acme Widget
  IDN: ACME,WIDGET
  target: ${class:laser_setup.instruments.mydevice.MyDevice}
  kwargs: {timeout: 5000}
```

Procedures then queue it via `Instruments.MyDevice`. Full details in
[Adding an Instrument](adding-an-instrument.md).

## The resolvers, summarized

| Resolver | Use it for | Expands to |
| --- | --- | --- |
| `${class:dotted.path}` | procedure & instrument classes | the class object |
| `${function:dotted.path}` | script targets | the function object |
| `${sequence:Name}` | sequence `_types` | a generated `Sequence` subclass |

These are registered in `laser_setup/config/config.py`. See
[Configuration → Resolvers](../user-guide/configuration.md#resolvers).
