# Installation

This page explains, step by step, how to install and run Laser Setup **without
installing anything system-wide**. Everything lives inside a project-local
virtual environment managed by [`uv`](https://docs.astral.sh/uv/), or inside a
Docker container. You can delete the project folder (or the container) and your
system is left exactly as it was.

!!! abstract "TL;DR"
    ```bash
    git clone https://github.com/nanolab-fcfm/laser_setup.git
    cd laser_setup
    uv sync
    uv run laser_setup
    ```
    The first three commands set everything up; the last one launches the app.

---

## Why `uv`?

[`uv`](https://docs.astral.sh/uv/) is a fast Python project manager. We use it
because it:

- **Never touches your system Python** — it creates an isolated `.venv` folder
  inside the project.
- **Installs the exact dependency versions** recorded in `uv.lock`, so everyone
  gets a reproducible environment.
- **Picks the right Python version automatically** — this repository ships a
  `.python-version` file pinning **Python 3.12**, which has prebuilt wheels for
  every dependency (so nothing has to be compiled from source).

You run project commands by prefixing them with `uv run`. That guarantees they
execute inside the project environment, not against any global install.

---

## Step 0 — Install `uv`

`uv` is a single, self-contained binary. Installing it does **not** install
Python packages globally.

=== "macOS / Linux"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows (PowerShell)"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

=== "Already have Homebrew / pipx"

    ```bash
    brew install uv        # macOS
    # or
    pipx install uv        # any OS
    ```

Verify it works:

```bash
uv --version
```

!!! tip "Prefer Docker?"
    If you would rather not install `uv` at all, jump to
    [Option B: Docker](#option-b-docker). You only need Docker installed.

---

## Step 1 — Get the source code

```bash
git clone https://github.com/nanolab-fcfm/laser_setup.git
cd laser_setup
```

If you don't have `git`, download the repository as a ZIP from GitHub and unzip
it, then `cd` into the folder.

---

## Option A: `uv` (recommended)

### Step 2 — Create the environment

```bash
uv sync
```

This single command:

1. Reads `.python-version` and makes sure **Python 3.12** is available
   (downloading a private copy if needed — still not system-wide).
2. Creates an isolated virtual environment in `./.venv`.
3. Installs all dependencies pinned in `uv.lock`, plus the `laser_setup` package
   itself.

!!! question "Want the documentation tools too?"
    The docs site uses an isolated dependency group. Install it on demand with
    `uv sync --group docs` (or just use `uv run --group docs ...`). The runtime
    application never depends on the docs tools.

### Step 3 — Run the application

```bash
uv run laser_setup
```

This launches the **main window** (the GUI hub). The first time you run it,
there is no user configuration yet — that's expected. The
[First Steps](first-steps.md) guide walks you through creating one.

You can also run a specific procedure or script directly:

```bash
uv run laser_setup FakeProcedure   # open a demo experiment window
uv run laser_setup init            # create your config files
uv run laser_setup -d              # launch in DEBUG mode (no hardware needed)
```

### Step 4 — Verify the install

```bash
uv run laser_setup --version
```

You should see something like:

```text
laser_setup 0.6.0-alpha
```

🎉 You're installed. Continue to [First Steps](first-steps.md).

---

## Option B: Docker

Use Docker when you don't want to install `uv`/Python on the host at all, or to
**build the documentation** in a clean environment. A ready-to-use setup for the
documentation site lives in [`docs/`](../building-and-deploying-docs.md).

!!! warning "Running the **GUI** inside Docker"
    The application is a **PyQt6 desktop GUI**. Showing a GUI from a container
    requires forwarding your display (X11/Wayland), which is platform-specific
    and fiddly. For day-to-day use of the *application* we strongly recommend
    **Option A (`uv`)**. Docker is the recommended path for the **documentation
    site** and for **headless/CI** tasks (linting, tests in debug mode).

### Build the documentation with Docker

From the repository root:

```bash
docker compose -f docs/docker-compose.yml up
```

Then open <http://localhost:8000>. Edits to files under `docs/` reload live.
See [Building & deploying these docs](../building-and-deploying-docs.md) for
details and for the one-shot static build.

### Headless application use (Linux, advanced)

On Linux you can run the app headlessly (for example to exercise debug mode in
CI) by setting an offscreen Qt platform:

```bash
docker run --rm -e QT_QPA_PLATFORM=offscreen \
  -v "$PWD":/app -w /app ghcr.io/astral-sh/uv:debian \
  uv run laser_setup --version
```

For a *visible* GUI on Linux, additionally share the X11 socket
(`-e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix`) and grant access with
`xhost +local:`.

---

## Instrument drivers (only for real hardware)

You do **not** need any of this to follow the tutorials — debug mode simulates
every instrument. You only need drivers when talking to **real** equipment.

| Connection type | Instruments | What you need |
| --- | --- | --- |
| USB / GPIB (VISA) | Keithley 2450, Keithley 6517B, Thorlabs PM100 | A VISA backend (see below) |
| Serial (COM port) | TENMA supplies, PT100 sensor, Clicker | Nothing extra — `pyserial` is bundled |
| Proprietary USB | Bentham TLS120Xe | The vendor's `bendev` driver |

### VISA backend

VISA instruments need a VISA backend. Two choices:

- **NI-VISA** — the vendor driver from National Instruments. It *is* a
  system-level driver and is **not** installable via `uv`. Install it only on
  the lab computer that connects to real instruments:
  [download NI-VISA](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html).
- **`pyvisa-py`** — a pure-Python backend you *can* install with `uv`, useful
  for development and some USB devices:

    ```bash
    uv add pyvisa-py        # adds it to the project, or…
    uv run --with pyvisa-py laser_setup
    ```

!!! note
    NI-VISA being system-level is unavoidable — it is a hardware driver, not a
    Python package. The *application itself* and all of its Python dependencies
    remain fully contained in `uv`/Docker. If you are only learning the software
    or developing procedures, you never need NI-VISA.

---

## Updating

Inside the project folder:

```bash
git pull              # fetch the latest code
uv sync               # re-install any changed dependencies
```

There is also an in-app **“Get updates”** script (and the `get_updates` CLI
command) that checks whether your clone is behind the GitHub remote — see
[CLI & Scripts](../user-guide/cli-and-scripts.md).

---

## Uninstalling / cleaning up

Because nothing was installed globally, cleanup is just:

```bash
rm -rf .venv          # remove the environment
# delete the cloned folder to remove everything else
```

Your global Python and system remain untouched.

---

## Troubleshooting

??? failure "`uv` tries to compile `scipy`/`numpy` from source and fails (asks for a Fortran compiler)"
    This happens when `uv` selects a Python version that is *newer* than the
    available prebuilt wheels (for example a brand-new system Python). The
    repository's `.python-version` pins **3.12** to avoid this. If you still hit
    it, force the version explicitly:

    ```bash
    uv run --python 3.12 laser_setup
    # or pin it for the whole project:
    uv python pin 3.12 && uv sync
    ```

??? failure "The window doesn't appear / `qt.qpa.plugin` errors on Linux"
    Install the system Qt/X11 runtime libraries your distro requires for Qt
    apps (e.g. `libxcb`, `libgl1`), or run headless commands with
    `QT_QPA_PLATFORM=offscreen`.

??? failure "`command not found: laser_setup`"
    Always launch it through `uv run laser_setup` from inside the project
    directory. The bare `laser_setup` command only exists if you installed it
    as a `uv tool` (see below).

??? info "I just want the command available everywhere (end users)"
    If you won't be developing and simply want to *use* the app, you can install
    it as an isolated `uv` tool (still not system-wide — it lives in `uv`'s
    private tools directory):

    ```bash
    uv tool install --python 3.12 \
      git+https://github.com/nanolab-fcfm/laser_setup.git
    laser_setup
    ```

More fixes are collected in [Troubleshooting & FAQ](../troubleshooting.md).
