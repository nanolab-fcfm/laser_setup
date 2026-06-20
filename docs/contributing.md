# Contributing

Contributions are welcome — new procedures, instrument drivers, bug fixes and
documentation.

## Set up a dev environment

```bash
git clone https://github.com/nanolab-fcfm/laser_setup.git
cd laser_setup
uv sync                 # runtime + dev dependencies, Python 3.12 (pinned)
```

Run the app and tests through `uv` so nothing is installed system-wide:

```bash
uv run laser_setup -d            # the app in debug mode
uv run python -m tests.gui_test  # a test script
```

## Workflow

1. Create a branch off `main`.
2. Make your change. Keep edits consistent with the surrounding code.
3. **Lint:**

    ```bash
    uv run --group dev flake8 laser_setup
    ```

4. **Build the docs** if you touched them:

    ```bash
    uv run --group docs mkdocs build --strict
    ```

5. Open a pull request describing the change.

## Code style

- `flake8`: `max-line-length = 100`, `max-complexity = 15`. `F401` (unused
  import) is ignored in `__init__.py` files (which re-export symbols).
- Add module-level loggers: `log = logging.getLogger(__name__)` with a
  `NullHandler`, matching existing modules.
- Build on PyMeasure idioms; prefer config (YAML) over hard-coding.

## Adding things

| You want to add… | Read |
| --- | --- |
| A measurement | [Creating a New Procedure](developer-guide/creating-a-procedure.md) |
| An instrument | [Adding an Instrument](developer-guide/adding-an-instrument.md) |
| A parameter | [Defining Parameters](developer-guide/parameters.md) |
| A sequence / script | [Registering in YAML](developer-guide/registering.md) |

## Dependencies

- Runtime deps → `[project].dependencies` in `pyproject.toml`.
- Dev tools → the `dev` dependency group; docs tools → the `docs` group.
- After editing dependencies, refresh the lockfile:

    ```bash
    uv lock
    ```

## Documentation

The docs are MkDocs Material in [`docs/`](building-and-deploying-docs.md). Prose
lives in Markdown; keep examples runnable and link generously between pages.
Preview locally with:

```bash
uv run --group docs mkdocs serve
```

## Versioning

The version is `laser_setup.__version__` (exposed dynamically in
`pyproject.toml`). Bump it in `laser_setup/__init__.py` when releasing.
