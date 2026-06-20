# Internals

This page documents the cross-cutting machinery that makes the rest of the
project work: the `@configurable` decorator, the PyMeasure patches, and shared
helper utilities.

## The `@configurable` decorator

Defined in `laser_setup/config/parser.py`, this decorator lets a class pull its
configuration out of the global `CONFIG` automatically.

```python
@configurable('procedures', on_definition=False)
class BaseProcedure(Procedure):
    ...
```

What the options do:

| Option | Effect |
| --- | --- |
| `config_key` | Which `CONFIG` section to read (e.g. `'procedures'`). |
| `on_definition` | Configure the decorated class itself when defined. |
| `subclasses` | Configure each **subclass** when it's defined (the default). |
| `instances` | Apply a `config_dict` kwarg to instances in `__init__`. |
| `instance_kwargs` | Merge config into `__init__` kwargs. |
| `error_ok` | Swallow instantiation errors and fall back to defaults. |

Because `BaseProcedure` is `configurable('procedures', subclasses=True)`, when
you define `class CountUp(BaseProcedure)`, the framework looks up
`CONFIG.procedures.CountUp` and calls `CountUp.configure_class(...)`. That method
(on `BaseProcedure`) deep-copies inherited parameters (so subclasses don't share
parameter instances), applies the `parameters:` overrides, and sets any other
attributes. This is why a YAML block like:

```yaml
CountUp:
  parameters: {n_points: {value: 100}}
  procedure_version: 1.0.0
```

changes the class without any Python.

## PyMeasure patches (`patches.py`)

`laser_setup/__init__.py` imports `patches` **first**, monkey-patching a few
PyMeasure classes so the rest of the app can rely on the improvements:

- A **`Status` IntEnum** on `Procedure` for ordered status comparisons
  (`self.status >= self.RUNNING`), used e.g. by `ChipProcedure.shutdown`.
- Tweaks to `Results.__init__` and header parsing so saved files round-trip
  cleanly.
- `Parameter.__init__` gains a `description` field.
- `Input.set_parameter` adjustments for the GUI input widgets.

!!! note
    Patches are applied on import, before any procedure or window is created.
    Keep `from . import patches` at the top of `laser_setup/__init__.py`.

## Helper utilities (`utils.py`)

`laser_setup/utils.py` collects data/instrument helpers used across procedures:

| Function | Purpose |
| --- | --- |
| `read_pymeasure(file)` | Split a results CSV into its header dict and a DataFrame. |
| `read_file_parameters(file)` | Extract just the parameter dict from a file header. |
| `get_latest_DP(chip_group, chip_number, sample, ...)` | Find the most recent measured Dirac point for a device (used by `VgMixin` to resolve `DP`). |
| `send_telegram_alert(message)` | Send a notification via the configured Telegram bot (used by `ChipProcedure` on finish). |
| voltage-ramp helpers | Generate stepped voltage sweeps. |

## Config helpers (`config/utils.py`)

| Function | Purpose |
| --- | --- |
| `instantiate(config, level=2)` | Recursively run `hydra.utils.instantiate`; `level` controls how many passes (resolve interpolation, then build). |
| `load_yaml(path, struct=None, ...)` | Load a YAML file into an `OmegaConf` object, optionally structured. |
| `save_yaml(obj, path)` | Write an `OmegaConf`/dict back to YAML. |
| `load_and_merge(path, config, section)` | Merge a YAML file into a section of `CONFIG`. |
| `get_type(name, bases, ...)` | Build a class dynamically (powers `${sequence:...}`). |
| `safeget(dic, *keys, default)` | Nested dict lookup that won't raise. |

## The configuration objects (`config/defaults.py`)

`AppConfig` is the structured schema for the whole configuration; every nested
dataclass (`DirConfig`, `QtConfig`, `FilenameConfig`, `SessionConfig`, …) defines
keys, defaults and metadata (titles, widget types) that the
[`ConfigWidget`](../user-guide/gui.md) uses to render an editor. `DefaultPaths`
centralizes the locations of the bundled templates and assets.

## Logging (`config/log.py`)

Sets up two handlers from the `Logging` dict-config: a **colored console**
formatter (`ColoredFormatter`) at `INFO`, and a **file** handler at `DEBUG`
(`log/laser_setup.log`). Tune levels in the `Logging` section of `config.yaml`.

## Reading order for new contributors

1. `laser_setup/__main__.py` — the whole control flow in ~20 lines.
2. `config/config.py` + `config/defaults.py` — how `CONFIG` is built.
3. `procedures/BaseProcedure.py` — the procedure contract.
4. `instruments/manager.py` — the proxy/connect/shutdown lifecycle.
5. `display/windows/experiment_window.py` — how a run is driven and plotted.
