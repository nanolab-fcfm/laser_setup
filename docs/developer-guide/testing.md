# Testing

The `tests/` directory holds **standalone scripts**, not a `pytest` suite. Each
file connects to hardware or a PyMeasure simulation and prints/plots results. Run
them through `uv` so they use the project environment.

!!! warning "Most tests expect hardware"
    Several tests talk to real instruments (Keithley, PT100, the VISA bus). On a
    machine without that hardware they will warn or fail at the connection step —
    that's expected. The GUI and PyMeasure tests run without instruments.

## Running a test

```bash
uv run python -m tests.gui_test        # module form
# or
uv run python tests/gui_test.py        # path form
```

## What each test covers

| Test | Needs hardware? | What it does |
| --- | --- | --- |
| `gui_test.py` | No | Opens an experiment window for PyMeasure's `RandomProcedure` — a quick GUI smoke test. |
| `pymeasure_test.py` | No | Runs a PyMeasure `Experiment` with a random procedure end-to-end. |
| `ramp_test.py` | No | Generates and plots a voltage-sweep ramp. |
| `device_test.py` | VISA | Lists VISA resources and checks device availability. |
| `test_connection.py` | Serial | Connects to the PT100 serial temperature sensor. |
| `keithley_time_test.py` | Keithley | Benchmarks Keithley 2450 time synchronization. |
| `telegram_test.py` | Network | Sends a test Telegram alert (needs a configured token). |

!!! tip "Develop against debug mode instead"
    For most day-to-day development you don't need these hardware tests — run the
    app itself in debug mode (`uv run laser_setup -d <Procedure>`) to exercise
    the full stack with simulated instruments. See
    [Instruments → Debug mode](../user-guide/instruments.md#debug-mode).

## Linting

`flake8` is configured in `.flake8` (`max-line-length = 100`,
`max-complexity = 15`; `F401` ignored in `__init__.py`). Run it from the dev
group:

```bash
uv run --group dev flake8 laser_setup
```

## Adding tests

Keep new tests as runnable scripts under `tests/`, importing from `laser_setup`.
If you introduce a `pytest`-style suite, add `pytest` to the `dev` dependency
group in `pyproject.toml` and run it with `uv run --group dev pytest`.

## Verifying the docs build

The documentation itself should build cleanly before you push:

```bash
uv run --group docs mkdocs build --strict
```

`--strict` turns warnings (e.g. a broken internal link) into errors. See
[Building & deploying these docs](../building-and-deploying-docs.md).
