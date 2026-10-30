"""Build a measurement-free *space digest* from plain records.

This module is **stdlib only** on purpose: it runs both on the Runner (inside the
``space_schema`` tunnel op) and locally (the client's fallback when a Runner is
too old to host it), and the two must agree byte-for-byte. Keeping it free of
pandas/numpy guarantees the same answer in both places and lets the schema tools
import it without pulling in the analytics stack.

What the digest says, and what it withholds
-------------------------------------------
For every device type and every flow it reports *structure*: which dotted param /
input / output paths exist, each path's ``kind`` (number, string, list, matrix,
map, …), how many records cover it, distinct-value *counts* for strings and
bools, and date ranges. It never emits a measurement value — no number, no string
value, no min/max/mean of numbers, and no *data-like* key below a collapsed
``map`` (a map's own keys are only counted; of its entries' keys, only the
*structural* ones — shared by most entries — survive, the rest are counted as
``other_keys``; see ``_map_value_dict``). The only values that appear are
timestamps (date ``first``/``last``),
which §3 of the spec sanctions explicitly, plus schema-ish strings the caller
puts in the records themselves (units, declared-parameter descriptions, type
names). That boundary is what lets a coding agent learn the shape of a space
without ever reading its data.

The structural describer here is a descendant of Planckian's
``describe_structure`` (prompt_plotting/prompt_plot_flow.py): same instinct —
report kind, shape and identifiers, never a leaf value — adapted to merge a
*collection* of records into one field per path and to the kinds this spec names.

``build_digest`` is pure and deterministic: the same input yields a byte-identical
``json.dumps(..., sort_keys=True)``.
"""

from __future__ import annotations

import numbers
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

__all__ = ["build_digest", "flow_key"]

VERSION = 1

# An ISO-8601 date or datetime. Deliberately a regex rather than
# ``datetime.fromisoformat`` because the latter rejects a trailing ``Z`` before
# Python 3.11, and we must classify dates identically across 3.10+.
_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)


def _is_number(value: Any) -> bool:
    # ``numbers.Real`` (minus ``bool``) catches Python ``int``/``float`` and also
    # numpy scalars (``np.int64``/``np.float64`` register as ``numbers`` ABCs)
    # without this stdlib-only module importing numpy.
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _is_iso_date(value: str) -> bool:
    return bool(_ISO_RE.match(value))


def _is_matrix(value: Any) -> bool:
    """A matrix is a non-empty list of equal-length, non-empty numeric rows."""
    if not isinstance(value, (list, tuple)) or not value:
        return False
    if not all(isinstance(row, (list, tuple)) for row in value):
        return False
    ncols = len(value[0])
    if ncols == 0:
        return False
    return all(len(row) == ncols and all(_is_number(x) for x in row) for row in value)


def _full_kind(value: Any) -> str:
    """The kind label of a single value, used when merging across records.

    Numeric classification goes through the ``numbers`` ABCs rather than the
    concrete ``int``/``float`` types, so numpy scalars (``np.int64`` is an
    ``Integral``, ``np.float64`` a ``Real``) land on ``integer``/``number`` — all
    without this stdlib-only module importing numpy. ``bool`` is an ``Integral``
    too, so it must be ruled out first. Anything we cannot otherwise place (an
    opaque object, a ``Decimal``, bytes, …) is ``"other"`` rather than being
    silently mislabelled a string.
    """
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, numbers.Integral):
        return "integer"
    if isinstance(value, numbers.Real):
        return "number"
    if isinstance(value, str):
        return "date" if _is_iso_date(value) else "string"
    if isinstance(value, (list, tuple)):
        return "matrix" if _is_matrix(value) else "list"
    if isinstance(value, dict):
        return "dict"
    return "other"


def _pct(n: int, total: int) -> int:
    """Integer coverage percentage; 0 when the denominator is 0."""
    if total <= 0:
        return 0
    return int(round(100 * n / total))


def _unit_of(container: dict) -> str | None:
    """The sibling ``unit``/``units`` string of a dict, if any — never a number."""
    for key in ("unit", "units"):
        value = container.get(key)
        if isinstance(value, str):
            return value
    return None


def _pick_unit(units: list[str | None]) -> str | None:
    """The dominant unit across records; most common, ties broken lexically."""
    present = [u for u in units if u]
    if not present:
        return None
    counts = Counter(present)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


# ---------------------------------------------------------------------------
# Field (one dotted path) and dict (a collection of path maps) describers
# ---------------------------------------------------------------------------


def _scalar_field(kind: str, values: list, coverage: int) -> dict:
    """A leaf field. Strings/bools get a distinct *count*; dates get a range."""
    field: dict[str, Any] = {"kind": kind, "coverage": coverage}
    if kind in ("string", "bool"):
        # A COUNT of distinct values — never the values themselves.
        field["distinct"] = len({v for v in values})
    elif kind == "date":
        isos = sorted(str(v) for v in values)
        if isos:
            field["first"] = isos[0]
            field["last"] = isos[-1]
    return field


def _list_field(lists: list, coverage: int) -> dict:
    """A list or matrix field, by shape only."""
    if lists and all(_is_matrix(lst) for lst in lists):
        rows = [len(lst) for lst in lists]
        cols = [len(lst[0]) for lst in lists]
        return {
            "kind": "matrix",
            "coverage": coverage,
            "shape": {"rows": [min(rows), max(rows)], "cols": [min(cols), max(cols)]},
        }
    lengths = [len(lst) for lst in lists]
    field: dict[str, Any] = {
        "kind": "list",
        "coverage": coverage,
        "length": {"min": min(lengths), "max": max(lengths)},
    }
    items = [item for lst in lists for item in lst]
    if items:
        item_kinds = {_full_kind(item) for item in items}
        field["item_kind"] = item_kinds.pop() if len(item_kinds) == 1 else "mixed"
    return field


def _describe_path(
    values: list, total: int, *, depth: int, max_keys: int, max_depth: int, under_map: bool = False
) -> dict[str, dict]:
    """Describe one path across records as a ``{relative_subpath: field}`` map.

    A leaf, list, matrix, mixed path or collapsed/maxed-out dict returns a single
    ``{"": field}``. A dict that is flattened returns one entry per (dotted) child
    and *no* ``""`` entry. ``values`` holds the present, non-None values at this
    path; ``total`` is the record count that coverage is measured against.
    ``under_map`` is set once we have descended below a collapsed ``map``: there a
    dict is never flattened and its keys are kept only when they are *structural*
    (see :func:`_map_value_dict`), so data-like keys never surface.
    """
    coverage = _pct(len(values), total)
    if not values:
        return {"": {"kind": "null", "coverage": coverage}}

    if all(isinstance(v, dict) for v in values):
        return _describe_dict(
            values, total, coverage, depth=depth, max_keys=max_keys,
            max_depth=max_depth, under_map=under_map,
        )
    if all(isinstance(v, (list, tuple)) for v in values):
        return {"": _list_field(values, coverage)}

    kinds = Counter(_full_kind(v) for v in values)
    if len(kinds) == 1:
        return {"": _scalar_field(next(iter(kinds)), values, coverage)}
    # Kind varies across records — report the mix, with counts, and stop.
    return {"": {"kind": "mixed", "coverage": coverage, "kinds": dict(kinds)}}


def _describe_single(
    values: list, total: int, *, depth: int, max_keys: int, max_depth: int, under_map: bool
) -> dict:
    """Describe values as exactly one field, never flattening a dict.

    Used where a single field is required even for a dict value — a ``map``'s
    merged ``value``. It is always called with ``under_map=True``, so a dict value
    reports its *structural* key names (or collapses to a nested map) instead of
    expanding into dotted paths.
    """
    return _describe_path(
        values, total, depth=depth, max_keys=max_keys, max_depth=max_depth, under_map=under_map
    )[""]


def _map_value_dict(
    dicts: list, union: set, coverage: int, *, depth: int, max_keys: int, max_depth: int
) -> dict:
    """Describe the dict entries *below* a collapsed ``map`` as a single field.

    The map's own keys are data (a run id, a wafer id, …) and are only counted.
    But the *entries* of a map are often uniform records, and their field names
    (``peak``, ``ts``, …) are structure worth reporting. The rule that keeps those
    while still hiding data-like keys:

    * A key is *structural* only if it occurs in at least half of the map's dict
      entries. Keys below that threshold are data (a value smuggled in as a key)
      and are dropped, their number reported as ``other_keys``.
    * The surviving names are listed in ``keys`` — but only if there are at most
      ``max_keys`` of them. If none survive, or too many do, the entries are
      themselves map-like, so the value collapses to a nested ``map`` carrying
      only ``key_count`` (never keys, never a further value).
    * At the depth budget we never list keys below a map either, for the same
      reason; only the count.

    Recursion re-applies the whole rule: a map whose entries are themselves
    collapsing dicts yields ``map`` → ``value`` → nested ``map``.
    """
    n = len(dicts)
    if depth >= max_depth:
        return {"kind": "map", "coverage": coverage, "key_count": len(union)}

    # Structural keys: present in >= 50% of the map's dict entries. ``* 2 >= n``
    # is the integer form of ``count / n >= 0.5`` and needs no float rounding.
    passing = sorted(k for k in union if sum(1 for d in dicts if k in d) * 2 >= n)
    other = len(union) - len(passing)

    if not passing or len(passing) > max_keys:
        return {"kind": "map", "coverage": coverage, "key_count": len(union)}

    field: dict[str, Any] = {"kind": "dict", "coverage": coverage, "keys": passing}
    if other:
        field["other_keys"] = other
    return field


def _describe_dict(
    dicts: list, total: int, coverage: int, *, depth: int, max_keys: int,
    max_depth: int, under_map: bool = False,
) -> dict[str, dict]:
    """Describe a collection of dicts: flatten, collapse to a map, or list keys."""
    union: set = set()
    for d in dicts:
        union |= set(d.keys())

    # Already below a collapsed map: never flatten, keep only structural keys.
    if under_map:
        return {
            "": _map_value_dict(
                dicts, union, coverage, depth=depth, max_keys=max_keys, max_depth=max_depth
            )
        }

    # Too many keys (in one record or across the union) means the keys are data,
    # not schema — a measurements-by-run dict, say. Collapse to a map: report how
    # many keys there are and the merged shape of the values, but never the keys.
    if len(union) > max_keys:
        inner = [v for d in dicts for v in d.values() if v is not None]
        value_field = (
            _describe_single(
                inner, len(inner), depth=depth, max_keys=max_keys,
                max_depth=max_depth, under_map=True,
            )
            if inner
            else {"kind": "null", "coverage": 0}
        )
        return {
            "": {
                "kind": "map",
                "coverage": coverage,
                "key_count": len(union),
                "value": value_field,
            }
        }

    # At the depth budget, stop flattening: list the child key names (a bounded,
    # schema-only summary — these are structural paths, not below a map) rather
    # than recursing further.
    if depth >= max_depth:
        return {"": {"kind": "dict", "coverage": coverage, "keys": sorted(union)[:max_keys]}}

    return _flatten_keys(
        dicts, total, child_depth=depth + 1, max_keys=max_keys, max_depth=max_depth
    )


def _flatten_keys(
    dicts: list, total: int, *, child_depth: int, max_keys: int, max_depth: int
) -> dict[str, dict]:
    """Flatten each key of a dict collection into its own dotted path field."""
    union: set = set()
    for d in dicts:
        union |= set(d.keys())

    out: dict[str, dict] = {}
    for key in sorted(union):
        present = [(d[key], _unit_of(d)) for d in dicts if key in d and d[key] is not None]
        values = [v for v, _ in present]
        unit = _pick_unit([u for _, u in present])
        sub = _describe_path(
            values, total, depth=child_depth, max_keys=max_keys, max_depth=max_depth
        )
        for subpath, field in sub.items():
            # A unit sibling annotates numeric leaves only — it is the unit of the
            # measurement, not of a label or a nested structure.
            if (
                unit
                and subpath == ""
                and field.get("kind") in ("number", "integer")
                and "unit" not in field
            ):
                field = {**field, "unit": unit}
            full = key if subpath == "" else f"{key}.{subpath}"
            out[full] = field
    return out


def _fieldmap(containers: list[dict], total: int, *, max_keys: int, max_depth: int) -> dict:
    """Flatten top-level containers (params / inputs / outputs) into path fields.

    The top level is always flattened: the map-collapse rule is for *nested*
    dicts whose keys are data. A container is the per-record ``params`` (or run
    ``params``/``output``) dict; a missing one is passed as ``{}`` by the caller.
    """
    return _flatten_keys(
        containers, total, child_depth=1, max_keys=max_keys, max_depth=max_depth
    )


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _device_types(devices: list[dict], *, max_keys: int, max_depth: int,
                  counts: dict | None = None) -> dict:
    by_type: dict[str, list[dict]] = {}
    for device in devices:
        by_type.setdefault(device.get("type", "device"), []).append(device)

    out: dict[str, dict] = {}
    for dtype, devs in by_type.items():
        # When ``counts`` is given (a sampled build) the records are a per-type
        # sample: the reported ``count`` is the true population from ``counts``,
        # while coverage/field denominators stay over the sample that was seen.
        sample_size = len(devs)
        count = counts.get(dtype, sample_size) if counts is not None else sample_size

        fabs = [d.get("fabrication_date") for d in devs]
        present_fabs = sorted(f for f in fabs if f)
        fab_field: dict[str, Any] = {"coverage": _pct(len(present_fabs), sample_size)}
        if present_fabs:
            fab_field["first"] = present_fabs[0]
            fab_field["last"] = present_fabs[-1]

        distinct_tags: set = set()
        with_tags = 0
        for d in devs:
            tags = d.get("tags") or []
            if tags:
                with_tags += 1
            distinct_tags |= set(tags)

        params = [d.get("params") or {} for d in devs]
        out[dtype] = {
            "count": count,
            "fabrication_date": fab_field,
            "tags": {"count_distinct": len(distinct_tags), "coverage": _pct(with_tags, sample_size)},
            "params": _fieldmap(params, sample_size, max_keys=max_keys, max_depth=max_depth),
        }
    return out


def flow_key(flows: list[dict]) -> dict[str, str]:
    """Map each flow ``id`` to the stable, unique key it takes in the digest.

    Flows are keyed by name, so a human reads ``digest["flows"]["IV sweep"]``. Two
    pitfalls the raw name has: it can be falsy (``None`` or ``""``), and it can
    collide with another flow's. So:

    * a falsy name falls back to the flow ``id``;
    * when several flows share a name, *every* colliding flow is keyed
      ``"{name} [{id}]"`` — disambiguating all of them, not just the later ones,
      so no flow silently overwrites another.

    Public so callers that build the digest (the Runner's ``space_schema`` op)
    can map a flow id back to its digest key without re-deriving the rule.
    """
    base: dict[str, str] = {}
    counts: Counter = Counter()
    for flow in flows:
        fid = flow["id"]
        name = flow.get("name") or fid
        base[fid] = name
        counts[name] += 1
    return {
        fid: (f"{name} [{fid}]" if counts[name] > 1 else name)
        for fid, name in base.items()
    }


def _declared_parameters(flow: dict) -> dict:
    """Declared params as ``{name: {type, description}}`` — never their defaults.

    Defaults are omitted deliberately: a default can be a measurement-shaped value
    and has no place in a schema-only digest. Types and descriptions are schema.
    """
    declared: dict[str, dict] = {}
    for name, meta in (flow.get("parameters") or {}).items():
        meta = meta or {}
        entry: dict[str, Any] = {}
        if meta.get("type") is not None:
            entry["type"] = meta["type"]
        if meta.get("description") is not None:
            entry["description"] = meta["description"]
        declared[name] = entry
    return declared


def _flows(
    flows: list[dict], runs: list[dict], devices: list[dict], *, max_keys: int, max_depth: int
) -> dict:
    device_type_by_id = {d["id"]: d.get("type", "device") for d in devices}

    runs_by_flow: dict[str, list[dict]] = {}
    for run in runs:
        runs_by_flow.setdefault(run.get("flow_id"), []).append(run)

    keys = flow_key(flows)
    out: dict[str, dict] = {}
    for flow in flows:
        flow_runs = runs_by_flow.get(flow["id"], [])
        run_count = len(flow_runs)

        status_counts = Counter(str(r.get("status")) for r in flow_runs if r.get("status"))
        created = sorted(r["created_time"] for r in flow_runs if r.get("created_time"))
        with_plots = sum(1 for r in flow_runs if r.get("visualization_ids"))

        device_type_counts: Counter = Counter()
        for run in flow_runs:
            types_in_run = {
                device_type_by_id[did]
                for did in (run.get("device_ids") or [])
                if did in device_type_by_id
            }
            device_type_counts.update(types_in_run)

        entry: dict[str, Any] = {
            "id": flow["id"],
            "run_count": run_count,
            "runs_sampled": run_count,
            "truncated": False,
            "status": dict(status_counts),
            "runs_with_plots": with_plots,
            "device_types": dict(device_type_counts),
            "declared_parameters": _declared_parameters(flow),
            "inputs": _fieldmap(
                [r.get("params") or {} for r in flow_runs],
                run_count,
                max_keys=max_keys,
                max_depth=max_depth,
            ),
            "outputs": _fieldmap(
                [r.get("output") or {} for r in flow_runs],
                run_count,
                max_keys=max_keys,
                max_depth=max_depth,
            ),
        }
        if created:
            entry["first_run"] = created[0]
            entry["last_run"] = created[-1]
        out[keys[flow["id"]]] = entry
    return out


def build_digest(
    devices: list[dict],
    flows: list[dict],
    runs: list[dict],
    *,
    built_at: str | None = None,
    max_keys: int = 50,
    max_depth: int = 4,
    device_counts: dict | None = None,
) -> dict:
    """Build the space digest from plain device / flow / run records.

    Parameters
    ----------
    devices, flows, runs
        Records in the §1 wire format (plain JSON-able dicts). ``build_digest``
        reads nothing beyond these — it is the single source of truth for the
        shape, so the Runner-side op and the local fallback stay in lockstep.
    built_at
        The timestamp stamped into the digest. Pass it for determinism; when
        omitted it defaults to now (UTC), which is the one non-deterministic
        input.
    max_keys
        A dict with more than this many keys (per record or across the union)
        collapses to a ``map``.
    max_depth
        How deep dict children are flattened into dotted paths.

    Returns
    -------
    dict
        The digest (spec §3). Deterministic: identical records (and ``built_at``)
        yield a byte-identical ``json.dumps(..., sort_keys=True)``.
    """
    if built_at is None:
        built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ``device_counts`` (a sampled build) overrides the population totals so the
    # digest's counts stay exact even though ``devices`` is only a per-type sample.
    if device_counts is not None:
        total_devices = sum(device_counts.values())
        total_types = len(device_counts)
    else:
        total_devices = len(devices)
        total_types = len({d.get("type", "device") for d in devices})

    return {
        "version": VERSION,
        "built_at": built_at,
        "totals": {
            "devices": total_devices,
            "device_types": total_types,
            "flows": len(flows),
            "runs": len(runs),
            "runs_truncated": False,
        },
        "device_types": _device_types(devices, max_keys=max_keys, max_depth=max_depth,
                                      counts=device_counts),
        "flows": _flows(flows, runs, devices, max_keys=max_keys, max_depth=max_depth),
    }
