# Developer Guide

This section is for **extending** Laser Setup: writing new measurement
procedures, adding instruments, defining parameters, and understanding the
internals.

<div class="grid cards" markdown>

-   :material-flask-plus: **[Creating a New Procedure](creating-a-procedure.md)**

    The main event — build your own measurement from scratch, step by step.

-   :material-tune-variant: **[Defining Parameters](parameters.md)**

    The `parameters.yaml` schema and how parameters reach procedures.

-   :material-connection: **[Adding an Instrument](adding-an-instrument.md)**

    Wrap a new piece of hardware as a PyMeasure instrument.

-   :material-file-code: **[Registering in YAML](registering.md)**

    Make procedures, sequences and scripts appear in the app.

-   :material-cog-box: **[Internals](internals.md)**

    The `@configurable` decorator, PyMeasure patches, and helper utilities.

-   :material-test-tube: **[Testing](testing.md)**

    How the test scripts work and how to run them with `uv`.

</div>

## Prerequisites

- You've followed the [Tutorials](../tutorials/index.md) and understand the
  experiment window, configuration and instruments.
- You have a working dev environment: `uv sync` (see
  [Installation](../getting-started/installation.md)).

## Development conventions

- **Style:** `flake8` with `max-line-length = 100`, `max-complexity = 15`;
  `F401` (unused import) is ignored in `__init__.py` files. Run it with:

    ```bash
    uv run --group dev flake8 laser_setup
    ```

- **Dependencies:** add runtime deps to `[project].dependencies` and dev/docs
  tools to the matching `[dependency-groups]` in `pyproject.toml`, then
  `uv lock` to refresh `uv.lock`.
- **Python version:** the repo pins **3.12** via `.python-version` so wheels are
  available for every dependency.
- **Build on PyMeasure.** Before writing a procedure or instrument, skim the
  [PyMeasure docs](https://pymeasure.readthedocs.io/en/latest/) — Laser Setup
  reuses its `Procedure`, `Parameter`, `Instrument` and managed-window classes.
