# Tutorial 3 · Running a Sequence

**Goal:** run several procedures automatically, one after another. **Time:**
~10 minutes. **Hardware:** none (`-d`).

!!! abstract "What you'll learn"
    - What a *sequence* is and when to use one.
    - How to launch the built-in `TestSequence`.
    - How common vs. per-procedure parameters work.

## What is a sequence?

A **sequence** chains procedures so they run in order without you re-queueing
each one. Sequences are perfect for measurement *protocols*, like the
[LED protocol](../led_protocol.md): *IVg → It → IVg → Wait → IVg*.

Sequences are defined in `sequences.yaml`. The repository ships three examples:

| Sequence | Runs | Purpose |
| --- | --- | --- |
| `TestSequence` | `FakeProcedure → Wait` | A safe, hardware-free demo. |
| `MainSequence` | `IVg → It → IVg → Wait → IVg` | The standard LED measurement flow. |
| `ItMadness` | `IVg → It×N (temperature sweep) → IVg` | A parameter-sweep example. |

## Step 1 — Launch the demo sequence

Start the app's main window (sequences are launched from there):

```bash
uv run laser_setup -d
```

In the menu bar, open **Sequences → Test Sequence** (or press
++ctrl+shift+1++). A **Sequence Window** appears showing the procedures it will
run, each with a status icon and timers.

## Step 2 — Understand the layout

```text
┌──────────────────────────────────────────────┐
│ Common parameters (shared by all procedures)  │
│   Chip group ▼   Chip number   Sample ▼       │
├──────────────────────────────────────────────┤
│  1. FakeProcedure   2. Wait                   │
│   ◴ running          ◴ pending                │
│   +0:03  =0:03       +0:00  =0:03             │
│   (its inputs)       (its inputs)             │
├──────────────────────────────────────────────┤
│              [ Queue ]   [ Abort ]            │
└──────────────────────────────────────────────┘
```

- **Common parameters** come from the sequence's `common_procedure`
  (here, `ChipProcedure`). They are set **once** and applied to every procedure
  in the sequence — so you enter the chip/sample only one time.
- **Per-procedure inputs** are the parameters unique to each step.
- Each step shows a **status icon** (color-coded: running, finished, aborted)
  and two timers: `+` time in the current step and `=` cumulative time.

!!! info "`inputs_ignored`"
    Sequences hide noisy parameters (`show_more`, `skip_startup`,
    `skip_shutdown`) from the common panel via `inputs_ignored`. You'll see this
    key in `sequences.yaml`.

## Step 3 — Queue the sequence

Pick a chip/sample in the common panel, then click **Queue**. Watch the steps
light up one by one: `FakeProcedure` runs to completion, then `Wait` runs.

If a step fails, an **abort dialog** appears with a countdown (default 30 s,
set by `Qt.SequenceWindow.abort_timeout`). If you don't respond it defaults to
*continue*; click **Yes** to abort the whole sequence.

!!! warning "Instruments shut down at the end"
    The sequence powers instruments down **after the last step**, not between
    steps. This lets consecutive procedures reuse a warmed-up, connected
    instrument — but it means a step that leaves an instrument in a bad state
    can affect the next. Procedures use `skip_startup`/`skip_shutdown` to manage
    this (see `ItMadness` in `sequences.yaml`).

## Step 4 — Peek at the definition

Open `laser_setup/assets/templates/sequences.yaml` and find `TestSequence`:

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

That's the whole thing: a name, a common base procedure, which inputs to hide,
and an ordered list of procedures. You can override any parameter for a specific
step, and even sweep a parameter across many runs with a `sequencer` block — see
[Sequences](../user-guide/sequences.md) for the full syntax.

## Recap

- A sequence runs procedures in order from a single window.
- `common_procedure` factors out shared inputs (chip, sample…).
- Steps show live status and timers; aborting is guarded by a countdown.
- Sequences are plain YAML — easy to read, copy and extend.

Next: stop editing the bundled templates and make your **own** configuration →
[Tutorial 4: Your own configuration](04-your-config.md).
