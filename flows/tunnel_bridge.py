"""Remote bridge server: a generic reflection bridge over the app tunnel.

This is the server flow. It serves the whole ``balthazar`` Python API to a remote
client through the Balthazar app tunnel, by reflecting attribute access, calls,
item access and context-manager use onto the real module running on the Runner.

The wire format, the value tags (``$obj`` / ``$ref`` / ``$attr`` / ``$new`` / …) and
the *parts protocol* (2 MiB zlib-compressed chunks, split and stitched in both
directions) give the client a stable wire contract. Per ``docs/SPEC.md`` the server:

* ``describe`` reports protocol 3, bridge version, user/owner/shared, the tunnel
  function names, the device indexes and the idle/call timeouts;
* long calls run in a worker thread and turn into pending jobs the client polls;
* refs are scoped per caller, with an LRU cap and an explicit ``release`` op;
* a heartbeat op and a watchdog that unwinds a silent caller's entered contexts;
* a ``tunnel`` namespace (server-side device cache + ``space_schema`` digest), run
  directly from worker threads (no main-thread job queue);
* hardening: no module-root ``set``, no ``ModuleType`` ever returned or traversed,
  secrets/context hidden unless opted in, an unpatchable audit log, and tracebacks
  only for the owner.

Stdlib only, except ``blt_analytics.digest`` which is imported lazily (and only by
``space_schema``).
"""

import base64
import collections
import collections.abc
import datetime
import fnmatch
import hashlib
import inspect
import itertools
import json
import os
import pathlib
import pickle
import secrets
import sys
import threading
import time
import traceback
import types
import weakref
import zlib
from datetime import timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import balthazar as blt

# The audit log holds a reference to ``blt.info`` captured here, at import, so a
# caller cannot silence the audit trail by patching ``blt.info`` through the bridge.
_audit_info = blt.info

BRIDGE_VERSION = "3.0.0"
MAX_DEPTH = 12
MAX_PARTS = 512
PART_TTL = 300
JOB_TTL = 600.0                      # finished, unpolled jobs expire after 10 min
DEFAULT_PART_BYTES = 2 * 1024 * 1024

# Device-cache paging constants.
DEVICE_PAGE_SIZE = 20_000             # devices per Runner search page while scanning
DEVICE_PAGE_FLOOR = 50                # smallest page size the halving-on-overflow falls to
DEVICE_REFRESH_CHUNK = 500            # ids per search_devices(id=[…]) refetch chunk
RUN_PAGE_SIZE = 250
DEFAULT_CACHE_MAX_BYTES = 2_000_000   # cached_devices / cached_devices_query byte budget
DEFAULT_QUERY_MAX_BYTES = 8_000_000   # query_devices reply byte budget
SCHEMA_SAMPLE_PER_TYPE = 2000         # at most this many devices per type feed the schema digest
_SAVE_DEBOUNCE_S = 60.0               # coalesce background cache saves to at most once per minute
_QUERY_CACHE_MAX = 32                 # LRU of (filter signature, generation) -> matching id list
_CONTAINER_OWNER_MAX = 200_000        # LRU of id(container) -> owning device, for write-through
SCHEMA_BUILD_BUDGET_S = 3600.0
DEVICE_CACHE_BUDGET_S = 3600.0
_DEFAULT_CACHE_DIR = "~/.balthazar_tunnel_cache"
_MISSING = object()
_GLOB_META = "*?["                    # a key segment with any of these is an fnmatch glob

# ----------------------------------------------------------------------------
# Configuration (flow params), applied by ``configure`` at start and in tests.
# ----------------------------------------------------------------------------
SHARED = False
ALLOWED_USERS = frozenset()
IDLE_TIMEOUT = 900.0
CALL_TIMEOUT = 45.0
MAX_REFS = 50_000
PART_BYTES = DEFAULT_PART_BYTES
EXPOSE_SECRETS = False
WARM_DEVICE_CACHE = False
DEVICE_CACHE_DIR = os.path.expanduser(_DEFAULT_CACHE_DIR)
DEVICE_INDEXES: dict = {}
HIDDEN = frozenset(
    ("serve_app", "prompt_input", "enter_new_flow_run", "context", "secrets")
)

_BASE_HIDDEN = ("serve_app", "prompt_input", "enter_new_flow_run", "context")


def _as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _parse_allowed_users(raw):
    if not raw:
        return frozenset()
    if isinstance(raw, (list, tuple, set)):
        parts = raw
    else:
        parts = str(raw).replace(";", ",").split(",")
    return frozenset(p.strip().lower() for p in parts if p and p.strip())


def configure(params=None):
    """Apply the flow params and reset all runtime state. Idempotent.

    ``params`` defaults to ``blt.params`` (a real Runner) but any mapping works, which
    is how the tests drive the different modes without a live space.
    """
    global SHARED, ALLOWED_USERS, IDLE_TIMEOUT, CALL_TIMEOUT, MAX_REFS, PART_BYTES
    global EXPOSE_SECRETS, WARM_DEVICE_CACHE, DEVICE_CACHE_DIR, DEVICE_INDEXES, HIDDEN
    if params is None:
        params = dict(getattr(blt, "params", {}) or {})
    SHARED = _as_bool(params.get("shared", False))
    ALLOWED_USERS = _parse_allowed_users(params.get("allowed_users", ""))
    IDLE_TIMEOUT = float(params.get("idle_timeout", 900) or 900)
    CALL_TIMEOUT = float(params.get("call_timeout", 45) or 45)
    MAX_REFS = int(params.get("max_refs", 50_000) or 50_000)
    PART_BYTES = int(params.get("part_bytes", DEFAULT_PART_BYTES) or DEFAULT_PART_BYTES)
    EXPOSE_SECRETS = _as_bool(params.get("expose_secrets", False))
    HIDDEN = frozenset(_BASE_HIDDEN if EXPOSE_SECRETS else _BASE_HIDDEN + ("secrets",))
    DEVICE_INDEXES = _parse_device_indexes(params.get("device_indexes", "{}"))
    DEVICE_CACHE_DIR = os.path.expanduser(
        params.get("device_cache_dir") or _DEFAULT_CACHE_DIR
    )
    WARM_DEVICE_CACHE = _as_bool(
        params.get("warm_device_cache", bool(DEVICE_INDEXES)), bool(DEVICE_INDEXES)
    )
    _reset_runtime_state()


def _reset_runtime_state():
    global _callers, _transfers, _device_store, _cache_meta, _schema_cache, _schema_build
    global _generation, _live_page_size, _query_id_cache, _query_fp_cache, _query_col_cache
    global _container_owner, _save_timer, _save_pending
    _callers = {}
    _transfers = {}
    _generation = itertools.count(1)
    _device_store = _empty_store()
    _cache_meta = {
        "state": "empty", "count": 0, "loaded": 0, "built_at": None,
        "started_at": None, "error": None, "bytes": 0, "blob_bytes": 0,
        "generation": 0, "page_size": DEVICE_PAGE_SIZE,
    }
    _live_page_size = DEVICE_PAGE_SIZE
    # LRU caches keyed by (filter signature, store generation) / plus key signature.
    _query_id_cache = collections.OrderedDict()
    _query_fp_cache = collections.OrderedDict()
    _query_col_cache = collections.OrderedDict()
    # id(container) -> owning device, for write-through through device.params / tags.
    _container_owner = collections.OrderedDict()
    _save_timer = None
    _save_pending = False
    _schema_cache = {"digest": None}
    _schema_build = {
        "state": "empty", "started_at": None,
        "loaded_flows": 0, "total_flows": None, "error": None,
    }


def owner_id():
    return str(getattr(blt, "user", "") or "").lower()


# ----------------------------------------------------------------------------
# Per-caller state: refs (LRU), entered contexts, pending jobs, last-seen.
# ----------------------------------------------------------------------------
_callers: dict = {}
_callers_lock = threading.Lock()
_ref_ids = itertools.count(1)
_local = threading.local()


class _Caller:
    __slots__ = ("lock", "refs", "entered", "jobs", "last_seen")

    def __init__(self):
        self.lock = threading.Lock()
        self.refs = collections.OrderedDict()   # ref id -> value
        self.entered = []                        # entered-context ref ids, innermost last
        self.jobs = {}                           # job id -> _Job
        self.last_seen = time.monotonic()


def caller_state(caller):
    """Return (creating if needed) the caller's state, recording the activity.

    ``last_seen`` is stamped *under* ``_callers_lock`` so the watchdog's reclaim
    decision (which re-reads it under the same lock) can never race an arriving
    request: the two are serialized.
    """
    with _callers_lock:
        state = _callers.get(caller)
        if state is None:
            state = _Caller()
            _callers[caller] = state
        state.last_seen = time.monotonic()
    return state


def remember(value):
    state = _local.state
    with state.lock:
        ref = next(_ref_ids)
        state.refs[ref] = value
        while len(state.refs) > MAX_REFS:
            state.refs.popitem(last=False)
    return ref


def recall(ref):
    state = _local.state
    with state.lock:
        if ref not in state.refs:
            raise LookupError("remote object expired, fetch it again")
        state.refs.move_to_end(ref)
        return state.refs[ref]


def release_refs(state, refs):
    with state.lock:
        for ref in refs or []:
            state.refs.pop(ref, None)
            if ref in state.entered:
                state.entered.remove(ref)


# ----------------------------------------------------------------------------
# Parts protocol (download + upload), per caller.
# ----------------------------------------------------------------------------
_transfers: dict = {}
_transfers_lock = threading.Lock()


def _forget_stale(now):
    for token in [t for t, e in _transfers.items() if e["expires"] < now]:
        del _transfers[token]


def _drop_transfers(caller):
    with _transfers_lock:
        for token in [t for t, e in _transfers.items() if e["caller"] == caller]:
            del _transfers[token]


def offer_parts(caller, body):
    packed = zlib.compress(body)
    parts = [packed[s : s + PART_BYTES] for s in range(0, len(packed), PART_BYTES)]
    token = secrets.token_hex(16)
    now = time.time()
    with _transfers_lock:
        _forget_stale(now)
        _transfers[token] = {"expires": now + PART_TTL, "caller": caller, "parts": parts}
    return {"ok": True, "parts": {"id": token, "count": len(parts)}}


def take_part(caller, token, index):
    with _transfers_lock:
        entry = _transfers.get(token)
        parts = entry.get("parts") if entry and entry["caller"] == caller else None
        if parts is None or not isinstance(index, int) or not 0 <= index < len(parts):
            return None
        if index == len(parts) - 1:
            del _transfers[token]
        return parts[index]


def add_part(caller, token, index, count, data):
    now = time.time()
    with _transfers_lock:
        _forget_stale(now)
        fresh = {"expires": now + PART_TTL, "caller": caller, "count": count, "received": {}}
        entry = _transfers.setdefault(token, fresh)
        known = entry["caller"] == caller and entry.get("count") == count
        if not known or not 0 <= index < count <= MAX_PARTS:
            raise ValueError("unexpected part of a request")
        entry["received"][index] = data
        if len(entry["received"]) < count:
            return None
        del _transfers[token]
    return zlib.decompress(b"".join(entry["received"][p] for p in range(count)))


# ----------------------------------------------------------------------------
# Encoding / decoding (ModuleType refused).
# ----------------------------------------------------------------------------
def describe(value):
    try:
        return str(value)
    except Exception:
        return "<%s>" % type(value).__name__


def snapshot_fields(value, depth):
    if callable(value) or isinstance(value, types.ModuleType):
        return {}
    cls = type(value)
    own = getattr(value, "__dict__", None)
    fields = {}
    for name in dir(value):
        if name.startswith("_"):
            continue
        if not (isinstance(own, dict) and name in own):
            try:
                if not inspect.isdatadescriptor(inspect.getattr_static(cls, name)):
                    continue
            except AttributeError:
                continue
        try:
            item = getattr(value, name)
        except Exception:
            continue
        if callable(item) or isinstance(item, types.ModuleType):
            continue
        fields[name] = encode(item, depth + 1)
    return fields


def encode_object(value, depth):
    cls = type(value)
    out = {"$": "obj", "cls": cls.__name__, "ref": remember(value)}
    if depth >= MAX_DEPTH:
        out.update(kind="object", fields={}, text=describe(value))
    elif isinstance(value, collections.abc.Mapping):
        out["kind"] = "mapping"
        out["items"] = [[encode(k, depth + 1), encode(value[k], depth + 1)] for k in list(value)]
    elif isinstance(value, collections.abc.Sequence):
        out["kind"] = "sequence"
        out["items"] = [encode(item, depth + 1) for item in list(value)]
    else:
        out["kind"] = "object"
        out["fields"] = snapshot_fields(value, depth)
        if not out["fields"] or cls.__str__ is not object.__str__:
            out["text"] = describe(value)
    return out


def encode(value, depth=0):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, types.ModuleType):
        raise AttributeError("modules are not reachable through the bridge")
    if isinstance(value, complex):
        return {"$": "complex", "v": [value.real, value.imag]}
    if isinstance(value, (bytes, bytearray)):
        return {"$": "bytes", "v": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, datetime.datetime):
        return {"$": "datetime", "v": value.isoformat()}
    if isinstance(value, datetime.date):
        return {"$": "date", "v": value.isoformat()}
    if isinstance(value, datetime.time):
        return {"$": "time", "v": value.isoformat()}
    if isinstance(value, datetime.timedelta):
        return {"$": "timedelta", "v": [value.days, value.seconds, value.microseconds]}
    if isinstance(value, pathlib.PurePath):
        return {"$": "path", "v": str(value)}
    if type(value) is list:
        return [encode(item, depth + 1) for item in value]
    if type(value) is tuple:
        return {"$": "tuple", "v": [encode(item, depth + 1) for item in value]}
    if type(value) in (set, frozenset):
        return {"$": "set", "v": [encode(item, depth + 1) for item in value]}
    if type(value) is dict:
        if "$" not in value and all(isinstance(key, str) for key in value):
            return {key: encode(item, depth + 1) for key, item in value.items()}
        pairs = [[encode(k, depth + 1), encode(v, depth + 1)] for k, v in value.items()]
        return {"$": "dict", "v": pairs}
    return encode_object(value, depth)


def public(name):
    if not isinstance(name, str) or name.startswith("_") or name in HIDDEN:
        raise AttributeError("%r is not reachable through the bridge" % (name,))
    return name


def resolve(root, path):
    target = root
    for name in path:
        target = getattr(target, public(name))
        if isinstance(target, types.ModuleType):
            raise AttributeError("modules are not reachable through the bridge")
    return target


def decode(value):
    if isinstance(value, list):
        return [decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    tag = value.get("$")
    if tag is None:
        return {key: decode(item) for key, item in value.items()}
    if tag == "ref":
        return recall(value["id"])
    if tag == "attr":
        return resolve(blt, value["path"])
    if tag == "new":
        factory = resolve(blt, value["path"])
        return factory(*decode(value.get("args", [])), **decode(value.get("kwargs", {})))
    payload = value["v"]
    if tag == "complex":
        return complex(payload[0], payload[1])
    if tag == "bytes":
        return base64.b64decode(payload)
    if tag == "datetime":
        return datetime.datetime.fromisoformat(payload)
    if tag == "date":
        return datetime.date.fromisoformat(payload)
    if tag == "time":
        return datetime.time.fromisoformat(payload)
    if tag == "timedelta":
        return datetime.timedelta(days=payload[0], seconds=payload[1], microseconds=payload[2])
    if tag == "path":
        return pathlib.Path(payload)
    if tag == "tuple":
        return tuple(decode(item) for item in payload)
    if tag == "set":
        return {decode(item) for item in payload}
    if tag == "dict":
        return {decode(key): decode(item) for key, item in payload}
    raise ValueError("unknown value tag %r" % (tag,))


def describe_module(caller):
    functions, classes = [], []
    for name in dir(blt):
        if name.startswith("_") or name in HIDDEN:
            continue
        try:
            item = getattr(blt, name)
        except Exception:
            continue
        if isinstance(item, types.ModuleType):
            continue
        if isinstance(item, type):
            classes.append(name)
        elif callable(item):
            functions.append(name)
    return {
        "functions": functions,
        "classes": classes,
        "parts": PART_BYTES,
        "protocol": 3,
        "bridge_version": BRIDGE_VERSION,
        "user": caller,
        "owner": owner_id(),
        "shared": SHARED,
        "tunnel": sorted(TUNNEL),
        "device_indexes": {name: spec["path"] for name, spec in DEVICE_INDEXES.items()},
        "idle_timeout_s": IDLE_TIMEOUT,
        "call_timeout_s": CALL_TIMEOUT,
    }


# ----------------------------------------------------------------------------
# Audit (shared mode only), through the import-time ``blt.info`` reference.
# ----------------------------------------------------------------------------
def audit(caller, state, request):
    if not SHARED:
        return
    op = request.get("op")
    if op == "tunnel":
        _audit_info("remote call by %s: tunnel %s" % (caller, request.get("name")))
        return
    parts = [str(name) for name in request.get("path", [])]
    ref = request.get("ref")
    if ref is not None:
        with state.lock:
            parts.insert(0, type(state.refs.get(ref)).__name__)
    target = ".".join(parts)
    if "key" in request:
        target += "[%s]" % json.dumps(request["key"])[:80]
    _audit_info("remote call by %s: %s %s" % (caller, op, target))


# ----------------------------------------------------------------------------
# Request handling (the op dispatch) + write-through to the device cache.
# ----------------------------------------------------------------------------
def handle(request):
    op = request.get("op")
    if op == "tunnel":
        name = request.get("name")
        fn = TUNNEL.get(name)
        if fn is None:
            raise ValueError("unknown tunnel function %r" % (name,))
        result = fn(*decode(request.get("args", [])), **decode(request.get("kwargs", {})))
        return {"ok": True, "result": encode(result)}

    ref = request.get("ref")
    root = blt if ref is None else recall(ref)
    path = request.get("path", [])
    result = None
    if op == "call":
        target = resolve(root, path)
        result = target(*decode(request.get("args", [])), **decode(request.get("kwargs", {})))
    elif op == "get":
        result = resolve(root, path)
    elif op == "set":
        if ref is None:
            raise AttributeError("assigning on the balthazar module is forbidden")
        setattr(resolve(root, path[:-1]), public(path[-1]), decode(request["value"]))
    elif op == "getitem":
        result = resolve(root, path)[decode(request["key"])]
    elif op == "contains":
        result = decode(request["key"]) in resolve(root, path)
    elif op == "setitem":
        resolve(root, path)[decode(request["key"])] = decode(request["value"])
    elif op == "delitem":
        del resolve(root, path)[decode(request["key"])]
    elif op == "enter":
        resolve(root, path).__enter__()
        if ref is not None:
            state = _local.state
            with state.lock:
                if ref not in state.entered:
                    state.entered.append(ref)
    elif op == "exit":
        failure = None
        if request.get("interrupted"):
            failure = KeyboardInterrupt()
        elif request.get("error"):
            failure = RuntimeError(request["error"])
        resolve(root, path).__exit__(type(failure) if failure else None, failure, None)
        if ref is not None:
            state = _local.state
            with state.lock:
                if ref in state.entered:
                    state.entered.remove(ref)
    else:
        raise ValueError("unknown operation %r" % (op,))

    # Track containers (device.params / tags / a nested dict) reached from a cached
    # device, so a later in-place write on one (``device.params.update(...)``,
    # ``device.tags.append(...)``) can be written through to the right device.
    if ref is not None and op in ("get", "getitem") and isinstance(result, (dict, list)):
        owner = _owning_device(root)
        if owner is not None:
            _remember_owner(result, owner)
    if ref is not None and op in ("call", "set", "setitem", "delitem"):
        _write_through(root)
    response = {"ok": True, "result": encode(result)}
    if ref is not None:
        response["self"] = encode(root)
    return response


# ----------------------------------------------------------------------------
# Jobs: run every non-control request in a worker thread; pending/poll.
# ----------------------------------------------------------------------------
class _Job:
    __slots__ = ("caller", "request", "done", "response", "finished_at")

    def __init__(self, caller, request):
        self.caller = caller
        self.request = request
        self.done = threading.Event()
        self.response = None
        self.finished_at = None


def _run_job(state, job):
    _local.caller = job.caller
    _local.state = state
    try:
        job.response = handle(job.request)
    except Exception as error:
        job.response = error_response(error, job.caller)
    job.finished_at = time.time()
    job.done.set()


def submit(state, caller, request):
    """Run the request in a worker thread; reply at once if quick, else as a job."""
    job = _Job(caller, request)
    threading.Thread(target=_run_job, args=(state, job), daemon=True).start()
    if job.done.wait(CALL_TIMEOUT):
        return job.response
    job_id = secrets.token_hex(8)
    with state.lock:
        state.jobs[job_id] = job
    return {"ok": True, "pending": job_id}


def poll(state, job_id):
    with state.lock:
        job = state.jobs.get(job_id)
    if job is None:
        raise LookupError("no pending job %r for this caller" % (job_id,))
    if job.done.wait(CALL_TIMEOUT):
        with state.lock:
            state.jobs.pop(job_id, None)
        return job.response
    return {"ok": True, "pending": job_id}


def error_response(error, caller):
    info = {"type": type(error).__name__, "message": str(error)}
    if caller == owner_id():
        info["traceback"] = traceback.format_exc()
    return {"ok": False, "error": info}


def expire_jobs(now=None):
    """Drop finished, unpolled jobs older than ``JOB_TTL`` (called by the watchdog)."""
    now = time.time() if now is None else now
    for state in list(_callers.values()):
        with state.lock:
            for job_id in [
                j for j, job in state.jobs.items()
                if job.finished_at is not None and now - job.finished_at > JOB_TTL
            ]:
                del state.jobs[job_id]


# ----------------------------------------------------------------------------
# Watchdog: unwind a silent caller's entered contexts, then reclaim it.
# ----------------------------------------------------------------------------
def _has_running_job(state):
    """True while any of the caller's jobs is still executing (not yet finished)."""
    return any(not job.done.is_set() for job in state.jobs.values())


def reclaim_silent(now=None):
    """Reclaim every caller that has been silent for longer than ``IDLE_TIMEOUT``.

    The decision is made atomically under ``_callers_lock``: a caller is detached
    only while it is *still* idle, *still* the registered state and has *no* job
    running. Because an arriving request bumps ``last_seen`` under the same lock
    (and may register a job), re-checking here right before the delete closes the
    time-of-check/time-of-use gap — an active caller is never unwound.
    """
    now = time.monotonic() if now is None else now
    for caller, state in list(_callers.items()):
        with _callers_lock:
            if _callers.get(caller) is not state:
                continue
            with state.lock:
                running = _has_running_job(state)
            idle = now - state.last_seen
            if running or idle <= IDLE_TIMEOUT:
                continue
            del _callers[caller]
        _reclaim(caller, state, "bridge client went silent for %ds" % int(idle))


def _reclaim(caller, state, reason):
    """Unwind a *detached* caller's contexts and drop its refs/jobs/transfers.

    The caller has already been removed from ``_callers`` under ``_callers_lock`` by
    :func:`reclaim_silent`, so no arriving request can attach to this state.
    """
    with state.lock:
        entered = list(state.entered)
        state.entered = []
    for ref in reversed(entered):
        with state.lock:
            ctx = state.refs.get(ref)
        if ctx is None:
            continue
        try:
            ctx.__exit__(RuntimeError, RuntimeError(reason), None)
            _audit_info("remote watchdog closed a context for %s: %s" % (caller, reason))
        except Exception as exc:
            _audit_info("remote watchdog could not close a context for %s: %s" % (caller, exc))
    with state.lock:
        state.refs.clear()
        state.jobs.clear()
    _drop_transfers(caller)


def _watchdog_loop(stop):
    while not stop.wait(1.0):
        try:
            reclaim_silent()
            expire_jobs()
        except Exception as exc:
            _audit_info("remote watchdog error: %s" % (exc,))


# ----------------------------------------------------------------------------
# Serialization helpers.
# ----------------------------------------------------------------------------
def _params_to_dict(params):
    for attempt in (lambda: dict(params),
                    lambda: {k: params[k] for k in params.keys()},
                    lambda: {k: v for k, v in params.items()}):
        try:
            return attempt()
        except Exception:
            continue
    return {}


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _enum_name(value):
    if value is None:
        return None
    return str(value).rsplit(".", 1)[-1]


def _project_params(params, keys=None):
    if keys is None:
        return params
    wanted = set(keys)
    return {k: v for k, v in params.items() if k in wanted}


def _device_to_dict(device):
    fab = getattr(device, "fabrication_date", None)
    record = {
        "id": getattr(device, "id", None),
        "name": getattr(device, "name", ""),
        "type": getattr(device, "type", "device"),
        "description": getattr(device, "description", None),
        "fabrication_date": _iso(fab),
        "tags": list(getattr(device, "tags", []) or []),
        "params": _params_to_dict(getattr(device, "params", {}) or {}),
    }
    archived = getattr(device, "archived", _MISSING)
    if archived is not _MISSING:
        record["archived"] = bool(archived) if archived is not None else None
    return record


def _flow_to_dict(flow):
    declared = {}
    for name, meta in (getattr(flow, "parameters", {}) or {}).items():
        declared[name] = {
            "type": getattr(meta, "type", None),
            "default": getattr(meta, "default", None),
            "description": getattr(meta, "description", None),
        }
    return {
        "id": getattr(flow, "id", None),
        "name": getattr(flow, "name", None),
        "description": getattr(flow, "description", None),
        "branch": getattr(flow, "branch", None),
        "script_filename": getattr(flow, "script_filename", None),
        "tags": list(getattr(flow, "tags", []) or []),
        "created_time": _iso(getattr(flow, "created_time", None)),
        "username": getattr(flow, "username", None),
        "parameters": declared,
    }


def _run_to_dict(run):
    devices = getattr(run, "devices", None)
    if devices is not None:
        device_ids = [getattr(d, "id", d) for d in devices]
    else:
        device_ids = list(getattr(run, "device_ids", []) or [])
    return {
        "id": getattr(run, "id", None),
        "flow_id": getattr(run, "flow_id", None),
        "flow_name": getattr(run, "flow_name", None),
        "status": _enum_name(getattr(run, "status", None)),
        "created_time": _iso(getattr(run, "created_time", None)),
        "started_time": _iso(getattr(run, "started_time", None)),
        "finished_time": _iso(getattr(run, "finished_time", None)),
        "username": getattr(run, "username", None),
        "tags": list(getattr(run, "tags", []) or []),
        "comment": getattr(run, "comment", None),
        "device_ids": device_ids,
        "params": _params_to_dict(getattr(run, "params", {}) or {}),
        "output": _params_to_dict(getattr(run, "output", {}) or {}),
        "visualization_ids": list(getattr(run, "visualization_ids", []) or []),
    }


# ----------------------------------------------------------------------------
# Device cache (no main-thread queue, so blt.* is called direct).
# ----------------------------------------------------------------------------
# The compact store holds every device as zlib-compressed JSON bytes (``blobs``)
# plus a slim, uncompressed index row (``slim``) carrying only what the hot filter
# paths read: name, type, tags, archived and the string value of every configured
# ``device_indexes`` path. The inverted ``index`` (name -> value -> [ids]) is kept
# for the exact-match / where lookups and ``index_values``. A monotonic generation
# counter bumps on every change, so the per-filter id-list caches key off it.
_generation = itertools.count(1)


def _empty_store():
    return {
        "blobs": {},                              # id -> (compressed_bytes, crc32)
        "slim": {},                               # id -> slim index row (see _slim_of)
        "index": {name: {} for name in DEVICE_INDEXES},
        "built_at": None,
        "generation": 0,
        "blob_bytes": 0,                          # running sum of len(compressed_bytes)
    }


_device_store = _empty_store()
_cache_meta = {
    "state": "empty", "count": 0, "loaded": 0, "built_at": None,
    "started_at": None, "error": None, "bytes": 0, "blob_bytes": 0,
    "generation": 0, "page_size": DEVICE_PAGE_SIZE,
}
_device_cache_lock = threading.Lock()   # guards _device_store + the id/fp/col caches
_build_lock = threading.Lock()          # serializes full cache (re)builds

_live_page_size = DEVICE_PAGE_SIZE
_query_id_cache = collections.OrderedDict()   # (filter_sig, generation) -> [ids] (sorted name,id)
_query_fp_cache = collections.OrderedDict()   # (filter_sig, generation) -> fingerprint
_query_col_cache = collections.OrderedDict()  # (filter_sig, keys_sig, generation) -> [columns]
_container_owner = collections.OrderedDict()  # id(container) -> owning device (write-through)

# Debounced background save state (enabled only once start() runs; tests persist
# synchronously on a full reload instead).
_save_lock = threading.Lock()
_save_timer = None
_save_pending = False
_SAVE_ENABLED = False


def _compress_record(record):
    """A device record as ``(zlib-compressed JSON bytes, crc32 of those bytes)``."""
    data = zlib.compress(json.dumps(record, default=str, separators=(",", ":")).encode("utf-8"))
    return data, zlib.crc32(data)


def _decompress_record(blob):
    return json.loads(zlib.decompress(blob[0]).decode("utf-8"))


def _slim_of(record):
    """The slim in-RAM index row for ``record`` (no params payload)."""
    idx = {}
    for name, spec in DEVICE_INDEXES.items():
        idx[name] = _index_value(record, spec.get("device_type"), spec["path"])
    return {
        "name": record.get("name") or "",
        "type": record.get("type"),
        "tags": list(record.get("tags") or []),
        "archived": record.get("archived"),
        "idx": idx,
    }


def _build_index_from_slim(slim):
    index = {name: {} for name in DEVICE_INDEXES}
    for rid, row in slim.items():
        for name, value in row["idx"].items():
            if value is not None:
                index[name].setdefault(value, []).append(rid)
    return index


def _store_from_records(records_by_id):
    """A fresh compact store built from plain ``{id: record}`` dicts (also used by tests)."""
    store = _empty_store()
    blobs, slim = store["blobs"], store["slim"]
    total = 0
    for rid, record in records_by_id.items():
        blob = _compress_record(record)
        blobs[rid] = blob
        slim[rid] = _slim_of(record)
        total += len(blob[0])
    store["index"] = _build_index_from_slim(slim)
    store["blob_bytes"] = total
    return store


def _bucket_remove(bucket, value, rid):
    ids = bucket.get(value)
    if not ids:
        return
    remaining = [i for i in ids if i != rid]
    if remaining:
        bucket[value] = remaining
    else:
        del bucket[value]


def _upsert_record(store, record):
    """Add or replace ``record`` in ``store`` (blob, slim and the inverted index)."""
    rid = record["id"]
    old_slim = store["slim"].get(rid)
    old_blob = store["blobs"].get(rid)
    new_blob = _compress_record(record)
    new_slim = _slim_of(record)
    if old_blob is not None:
        store["blob_bytes"] -= len(old_blob[0])
    store["blobs"][rid] = new_blob
    store["slim"][rid] = new_slim
    store["blob_bytes"] += len(new_blob[0])
    for name in DEVICE_INDEXES:
        old_val = old_slim["idx"].get(name) if old_slim else None
        new_val = new_slim["idx"].get(name)
        if old_val == new_val:
            continue
        bucket = store["index"].setdefault(name, {})
        if old_val is not None:
            _bucket_remove(bucket, old_val, rid)
        if new_val is not None:
            bucket.setdefault(new_val, []).append(rid)


def _remove_record(store, rid):
    old_slim = store["slim"].pop(rid, None)
    old_blob = store["blobs"].pop(rid, None)
    if old_blob is not None:
        store["blob_bytes"] -= len(old_blob[0])
    if old_slim is not None:
        for name, value in old_slim["idx"].items():
            if value is not None:
                _bucket_remove(store["index"].get(name, {}), value, rid)


def _bump_generation(store):
    store["generation"] = next(_generation)
    _cache_meta["generation"] = store["generation"]
    _cache_meta["count"] = len(store["blobs"])
    _cache_meta["blob_bytes"] = store["blob_bytes"]


def _publish_device_store(store, built_at=None):
    """Swap in ``store`` as the live device store and mirror its stats into _cache_meta."""
    global _device_store
    if built_at is not None:
        store["built_at"] = built_at
    _device_store = store
    _cache_meta["count"] = len(store["blobs"])
    _cache_meta["blob_bytes"] = store["blob_bytes"]
    _cache_meta["generation"] = store["generation"]
    _cache_meta["built_at"] = store["built_at"]


def _reset_query_caches():
    _query_id_cache.clear()
    _query_fp_cache.clear()
    _query_col_cache.clear()


def _parse_device_indexes(raw):
    if not raw:
        return {}
    spec = raw
    if isinstance(spec, str):
        try:
            spec = json.loads(spec)
        except (ValueError, TypeError) as exc:
            blt.error("[bridge] device_indexes is not valid JSON (%s); none configured" % exc)
            return {}
    if not isinstance(spec, dict):
        blt.error("[bridge] device_indexes must be a JSON object; none configured")
        return {}
    out = {}
    for name, value in spec.items():
        if isinstance(value, str) and value:
            out[str(name)] = {"path": value, "device_type": None}
        elif isinstance(value, dict) and value.get("path"):
            out[str(name)] = {"path": value["path"], "device_type": value.get("device_type")}
        else:
            blt.error("[bridge] device_indexes[%r] is malformed; skipping it" % name)
    return out


def _dig(container, dotted_path):
    current = container
    for segment in dotted_path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return _MISSING
    return current


def _index_value(record, device_type, path):
    if device_type is not None and record.get("type") != device_type:
        return None
    value = _dig(record.get("params") or {}, path)
    if value is _MISSING or value is None:
        return None
    return str(value)


def _iso_now():
    return datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _space_cache_key():
    space = getattr(blt, "space", None)
    if space is not None and getattr(space, "id", None):
        return str(space.id)
    return str(getattr(getattr(blt, "flow", None), "id", None) or "unknown")


def _device_cache_space_dir():
    return os.path.join(DEVICE_CACHE_DIR, _space_cache_key())


def _device_cache_path():
    return os.path.join(_device_cache_space_dir(), "devices.pkl")


def _device_cache_meta_path():
    return os.path.join(_device_cache_space_dir(), "meta.json")


# ----------------------------------------------------------------------------
# Persistence: a single pickle of the compact store + a JSON meta file per space.
# The full (re)build saves synchronously; frequent small changes (write-through,
# scoped refresh) only schedule a debounced background save (coalesced to once per
# minute) so a reply is never blocked re-pickling the whole store.
# ----------------------------------------------------------------------------
def _atomic_write(path, binary, writer):
    tmp = "%s.tmp" % path
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        opener = os.fdopen(fd, "wb") if binary else os.fdopen(fd, "w", encoding="utf-8")
        with opener as fh:
            writer(fh)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    os.replace(tmp, path)


def _save_device_cache_sync():
    """Persist the current store now (snapshot under the lock, write outside it)."""
    with _device_cache_lock:
        store = _device_store
        blobs = dict(store["blobs"])
        slim = dict(store["slim"])
        built_at = store["built_at"]
        generation = store["generation"]
    space_dir = _device_cache_space_dir()
    os.makedirs(space_dir, mode=0o700, exist_ok=True)
    try:
        os.chmod(space_dir, 0o700)
    except OSError:
        pass
    meta = {
        "built_at": built_at, "count": len(blobs), "generation": generation,
        "format": "compact-1", "indexes": DEVICE_INDEXES, "space_key": _space_cache_key(),
    }
    _atomic_write(
        _device_cache_path(), True,
        lambda fh: pickle.dump({"format": "compact-1", "blobs": blobs, "slim": slim,
                                "generation": generation}, fh,
                               protocol=pickle.HIGHEST_PROTOCOL),
    )
    _atomic_write(_device_cache_meta_path(), False, lambda fh: json.dump(meta, fh))


def _schedule_save():
    """Request a debounced background save (no-op until start() enables saving)."""
    global _save_timer, _save_pending
    if not _SAVE_ENABLED:
        return
    with _save_lock:
        _save_pending = True
        if _save_timer is None:
            _save_timer = threading.Timer(_SAVE_DEBOUNCE_S, _run_debounced_save)
            _save_timer.daemon = True
            _save_timer.start()


def _run_debounced_save():
    global _save_timer, _save_pending
    with _save_lock:
        _save_timer = None
        if not _save_pending:
            return
        _save_pending = False
    try:
        _save_device_cache_sync()
    except Exception as exc:
        blt.warn("[bridge] device cache save failed: %s: %s" % (type(exc).__name__, exc))


def _flush_pending_save():
    """Flush any pending debounced save immediately (clean-shutdown hook)."""
    with _save_lock:
        pending, timer = _save_pending, _save_timer
    if timer is not None:
        timer.cancel()
    if pending:
        try:
            _save_device_cache_sync()
        except Exception:
            pass


def _load_device_cache_from_disk():
    """Load a persisted compact store; discard (rebuild) an old or unreadable one."""
    pkl_path, meta_path = _device_cache_path(), _device_cache_meta_path()
    if not (os.path.exists(pkl_path) and os.path.exists(meta_path)):
        return False
    try:
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        with open(pkl_path, "rb") as fh:
            payload = pickle.load(fh)
    except Exception as exc:
        blt.warn("[bridge] could not load persisted device cache: %s" % exc)
        return False
    # Old-format pickles (pre-compact: {"records", "index"}) carry no "blobs";
    # discard them so the cache rebuilds in the new compact format.
    if not isinstance(payload, dict) or "blobs" not in payload:
        blt.warn("[bridge] persisted device cache is an old format; rebuilding")
        return False
    try:
        blobs = payload["blobs"] or {}
        store = _empty_store()
        store["blobs"] = blobs
        store["blob_bytes"] = sum(len(b[0]) for b in blobs.values())
        slim = payload.get("slim")
        if slim is None or (meta.get("indexes") or {}) != DEVICE_INDEXES:
            # Rebuild the slim rows (and so the index) when absent or the configured
            # indexes changed since the cache was written.
            store["slim"] = {rid: _slim_of(_decompress_record(b)) for rid, b in blobs.items()}
        else:
            store["slim"] = slim
        store["index"] = _build_index_from_slim(store["slim"])
    except Exception as exc:
        blt.warn("[bridge] persisted device cache is unreadable (%s); rebuilding" % exc)
        return False
    built_at = meta.get("built_at")
    with _device_cache_lock:
        _bump_generation(store)
        _publish_device_store(store, built_at)
        _reset_query_caches()
    _cache_meta.update(state="ready", count=len(blobs), loaded=len(blobs),
                       built_at=built_at, error=None, page_size=DEVICE_PAGE_SIZE,
                       blob_bytes=store["blob_bytes"])
    return True


# ----------------------------------------------------------------------------
# Scanning the Runner: page search_devices at DEVICE_PAGE_SIZE, halving the page
# on the 128 MiB gRPC cap. The Runner returns devices ordered by id, so offset
# pages are stable; each record is compressed as its page arrives, so the peak is
# about one page of device objects plus the compact store.
# ----------------------------------------------------------------------------
def _is_message_too_large(exc):
    return "message length too large" in str(exc).lower()


def _scan_into_store(progress=False):
    """Build a fresh compact store by paging every device; returns (store, page_size)."""
    store = _empty_store()
    blobs, slim = store["blobs"], store["slim"]
    page_size = DEVICE_PAGE_SIZE
    offset = 0
    while True:
        try:
            page = list(blt.search_devices(limit=page_size, offset=offset))
        except Exception as exc:
            if _is_message_too_large(exc) and page_size > DEVICE_PAGE_FLOOR:
                page_size = max(DEVICE_PAGE_FLOOR, page_size // 2)
                continue  # retry the SAME offset at the reduced size (which now sticks)
            raise
        if not page:
            break
        for device in page:
            record = _device_to_dict(device)
            rid = record["id"]
            if rid in blobs:
                store["blob_bytes"] -= len(blobs[rid][0])
            blob = _compress_record(record)
            blobs[rid] = blob
            slim[rid] = _slim_of(record)
            store["blob_bytes"] += len(blob[0])
        offset += len(page)
        if progress:
            _cache_meta["loaded"] = len(blobs)
            _cache_meta["page_size"] = page_size
            blt.info("[bridge] device cache: %d devices loaded (page size %d)"
                     % (len(blobs), page_size))
        if len(page) < page_size:
            break
    store["index"] = _build_index_from_slim(slim)
    return store, page_size


def _page_all_devices(track_progress=False):
    """Every device as a plain ``{id: record}`` dict (the schema's cache-cold path)."""
    store, _ = _scan_into_store(progress=track_progress)
    return {rid: _decompress_record(blob) for rid, blob in store["blobs"].items()}


def _reload_device_cache(force):
    with _build_lock:
        if not force and _cache_meta["state"] == "ready":
            return
        had_data = _cache_meta["state"] == "ready"
        _cache_meta.update(state="loading", started_at=_iso_now(), loaded=0, error=None)
        started = time.monotonic()
        blt.info("[bridge] building device cache...")
        try:
            store, page_size = _scan_into_store(progress=True)
        except Exception as exc:
            _cache_meta["error"] = "%s: %s" % (type(exc).__name__, exc)
            _cache_meta["state"] = "ready" if had_data else "error"
            blt.error("[bridge] device cache load failed: %s" % _cache_meta["error"])
            raise
        built_at = _iso_now()
        with _device_cache_lock:
            _bump_generation(store)
            _publish_device_store(store, built_at)
            _reset_query_caches()
        _cache_meta.update(state="ready", count=len(store["blobs"]),
                           loaded=len(store["blobs"]), built_at=built_at, error=None,
                           page_size=page_size, blob_bytes=store["blob_bytes"])
        try:
            _save_device_cache_sync()
        except Exception as exc:
            blt.warn("[bridge] device cache persist failed: %s: %s" % (type(exc).__name__, exc))
        blt.info("[bridge] device cache ready: %d device(s) in %.1fs"
                 % (len(store["blobs"]), time.monotonic() - started))


def _live_search_page(offset, kwargs):
    """One Runner search page at the current live page size, halving on the gRPC cap."""
    global _live_page_size
    size = _live_page_size
    while True:
        try:
            page = list(blt.search_devices(limit=size, offset=offset, **kwargs))
            _live_page_size = size
            return page, size
        except Exception as exc:
            if _is_message_too_large(exc) and size > DEVICE_PAGE_FLOOR:
                size = max(DEVICE_PAGE_FLOOR, size // 2)
                continue
            raise


def _refresh_index_value(index_name, value):
    # Read the ids to refresh under the lock, then fetch them from the Runner
    # *outside* the lock so concurrent write-throughs are not blocked for the whole
    # network round-trip. Merge the fresh records into the *current* store under the
    # lock (re-reading ``_device_store``), so any write-through that landed during the
    # fetch is preserved instead of being clobbered by a stale snapshot.
    with _device_cache_lock:
        known_ids = list(_device_store["index"].get(index_name, {}).get(str(value), []))
    if not known_ids:
        return
    found = {}
    for start in range(0, len(known_ids), DEVICE_REFRESH_CHUNK):
        chunk = known_ids[start:start + DEVICE_REFRESH_CHUNK]
        for d in blt.search_devices(id=chunk):
            record = _device_to_dict(d)
            found[record["id"]] = record
    with _device_cache_lock:
        store = _device_store
        for rid in known_ids:
            if rid in found:
                _upsert_record(store, found[rid])
            else:
                _remove_record(store, rid)
        _bump_generation(store)
    _schedule_save()


# ----------------------------------------------------------------------------
# Write-through: a reflected write whose root object is a cached device — or a
# container (``device.params`` / ``device.tags`` / a nested dict) reached from
# one — refreshes that device's cache record from its (now-mutated) live object.
# ----------------------------------------------------------------------------
def _remember_owner(container, device):
    """Note that ``container`` was reached from ``device`` (for later write-through)."""
    try:
        key = id(container)
    except Exception:
        return
    _container_owner[key] = device
    _container_owner.move_to_end(key)
    while len(_container_owner) > _CONTAINER_OWNER_MAX:
        _container_owner.popitem(last=False)


def _owning_device(root):
    """The device ``root`` belongs to: ``root`` itself if it is one, else its owner."""
    if getattr(root, "id", None) is not None and hasattr(root, "params"):
        return root
    return _container_owner.get(id(root))


def _write_through(root):
    """Keep the cache in step with a write whose root is a cached device/container."""
    device = _owning_device(root)
    if device is None:
        return
    rid = getattr(device, "id", None)
    if rid is None or not hasattr(device, "params"):
        return
    try:
        record = _device_to_dict(device)
    except Exception:
        return
    # Mutate the cache under ``_device_cache_lock`` and re-read ``_device_store`` under
    # it, so a concurrent reload/refresh that swapped the store object never causes the
    # write to land on a stale, detached store (and never races the index mutation).
    with _device_cache_lock:
        if _cache_meta["state"] != "ready":
            return
        store = _device_store
        if rid not in store["blobs"]:
            return
        _upsert_record(store, record)
        _bump_generation(store)
    _schedule_save()


# ----------------------------------------------------------------------------
# Filtering + key projection over the compact store.
# ----------------------------------------------------------------------------
def _as_glob_list(name):
    if name is None:
        return None
    return [name] if isinstance(name, str) else [str(n) for n in name]


def _as_type_list(type_):
    if type_ is None:
        return None
    return [type_] if isinstance(type_, str) else list(type_)


def _filter_ids(store, *, name=None, type=None, tags=None, where=None, archived=False):
    """Matching device ids, sorted by (name, id). Narrows by the inverted index first."""
    candidate = None
    if where:
        for index_name, want in where.items():
            _require_index(index_name)
            wants = [str(w) for w in (want if isinstance(want, (list, tuple, set)) else [want])]
            bucket = store["index"].get(index_name, {})
            ids = set()
            for w in wants:
                ids.update(bucket.get(w, []))
            candidate = ids if candidate is None else (candidate & ids)
        if not candidate:
            return []
    slim = store["slim"]
    name_globs = _as_glob_list(name)
    types = _as_type_list(type)
    tagset = list(tags) if tags else None
    source = candidate if candidate is not None else slim.keys()
    out = []
    for rid in source:
        row = slim.get(rid)
        if row is None:
            continue
        if archived is not None:
            flag = row.get("archived")
            if flag is not None and bool(flag) != bool(archived):
                continue
        if types is not None and row["type"] not in types:
            continue
        if name_globs is not None:
            nm = row["name"] or ""
            if not any(fnmatch.fnmatchcase(nm, g) for g in name_globs):
                continue
        if tagset is not None:
            dtags = row["tags"] or []
            if not all(t in dtags for t in tagset):
                continue
        out.append(rid)
    out.sort(key=lambda i: (slim[i]["name"] or "", i))
    return out


def _filter_signature(filters):
    norm = {}
    for key in ("name", "type", "tags", "where", "archived"):
        value = filters.get(key)
        if isinstance(value, (list, tuple, set)):
            value = sorted(str(v) for v in value)
        elif isinstance(value, dict):
            value = {k: (sorted(str(x) for x in v) if isinstance(v, (list, tuple, set)) else str(v))
                     for k, v in value.items()}
        norm[key] = value
    return json.dumps(norm, sort_keys=True, default=str)


def _cached_filter_ids(store, filters):
    """``_filter_ids`` memoized per (filter signature, generation), under the lock."""
    key = (_filter_signature(filters), store["generation"])
    cached = _query_id_cache.get(key)
    if cached is not None:
        _query_id_cache.move_to_end(key)
        return cached
    ids = _filter_ids(store, **filters)
    _query_id_cache[key] = ids
    while len(_query_id_cache) > _QUERY_CACHE_MAX:
        _query_id_cache.popitem(last=False)
    return ids


def _cached_fingerprint(store, filters, ids):
    """sha1 over the sorted (id, crc32) pairs of the matching records (cached)."""
    key = (_filter_signature(filters), store["generation"])
    cached = _query_fp_cache.get(key)
    if cached is not None:
        _query_fp_cache.move_to_end(key)
        return cached
    blobs = store["blobs"]
    hasher = hashlib.sha1()
    for rid in sorted(ids):
        blob = blobs.get(rid)
        crc = blob[1] if blob is not None else 0
        hasher.update(("%s:%d;" % (rid, crc)).encode("utf-8"))
    fingerprint = hasher.hexdigest()
    _query_fp_cache[key] = fingerprint
    while len(_query_fp_cache) > _QUERY_CACHE_MAX:
        _query_fp_cache.popitem(last=False)
    return fingerprint


def _record_matches(record, filters):
    """Apply the full filter set to one plain record (live post-filter + refresh scope)."""
    name_globs = _as_glob_list(filters.get("name"))
    if name_globs is not None:
        nm = record.get("name") or ""
        if not any(fnmatch.fnmatchcase(nm, g) for g in name_globs):
            return False
    types = _as_type_list(filters.get("type"))
    if types is not None and record.get("type") not in types:
        return False
    tags = filters.get("tags")
    if tags:
        dtags = record.get("tags") or []
        if not all(t in dtags for t in tags):
            return False
    where = filters.get("where")
    if where:
        for index_name, want in where.items():
            spec = DEVICE_INDEXES[index_name]
            value = _index_value(record, spec.get("device_type"), spec["path"])
            wants = [str(w) for w in (want if isinstance(want, (list, tuple, set)) else [want])]
            if value not in wants:
                return False
    archived = filters.get("archived")
    if archived is not None:
        flag = record.get("archived")
        if flag is not None and bool(flag) != bool(archived):
            return False
    return True


def _is_glob(segment):
    return any(ch in segment for ch in _GLOB_META)


def _expand_key(params, segments):
    """Every concrete ``(dotted_path, value)`` a dotted key (with optional globs) matches.

    A segment is a literal key unless it contains an fnmatch metacharacter; a path is
    emitted only when every segment resolves. A matched value that is a dict is kept
    whole (not flattened further).
    """
    frontier = [([], params)]
    for segment in segments:
        glob = _is_glob(segment)
        nxt = []
        for prefix, node in frontier:
            if not isinstance(node, dict):
                continue
            if glob:
                for key in node:
                    if fnmatch.fnmatchcase(str(key), segment):
                        nxt.append((prefix + [str(key)], node[key]))
            elif segment in node:
                nxt.append((prefix + [segment], node[segment]))
        frontier = nxt
    return [(".".join(path), value) for path, value in frontier]


def _dig_literal(params, segments):
    current = params
    for segment in segments:
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return None
    return current


_IDENTITY_COLUMNS = ("id", "name", "type", "tags")


def _discover_param_columns(blobs, ids, keys):
    """The concrete projected columns across all matching records, in key then sorted order."""
    per_key = [set() for _ in keys]
    segmented = [key.split(".") for key in keys]
    for rid in ids:
        blob = blobs.get(rid)
        if blob is None:
            continue
        params = _decompress_record(blob).get("params") or {}
        for i, segments in enumerate(segmented):
            for concrete, _value in _expand_key(params, segments):
                per_key[i].add(concrete)
    columns, seen = [], set()
    for found in per_key:
        for concrete in sorted(found):
            if concrete not in seen:
                seen.add(concrete)
                columns.append(concrete)
    return columns


def _columns_for(store, filters, ids, keys):
    """The ordered column list for a projection, cached per (filter, keys, generation)."""
    if keys is None:
        return list(_IDENTITY_COLUMNS) + ["params"]
    key = (_filter_signature(filters), json.dumps(list(keys)), store["generation"])
    cached = _query_col_cache.get(key)
    if cached is not None:
        _query_col_cache.move_to_end(key)
        return cached
    columns = list(_IDENTITY_COLUMNS) + _discover_param_columns(store["blobs"], ids, keys)
    _query_col_cache[key] = columns
    while len(_query_col_cache) > _QUERY_CACHE_MAX:
        _query_col_cache.popitem(last=False)
    return columns


def _row_values(record, keys, columns):
    """A ``{column: value}`` row for ``record`` over the fixed ``columns`` list."""
    row = {
        "id": record.get("id"),
        "name": record.get("name"),
        "type": record.get("type"),
        "tags": record.get("tags") or [],
    }
    if keys is None:
        row["params"] = record.get("params") or {}
        return row
    params = record.get("params") or {}
    for column in columns:
        if column in _IDENTITY_COLUMNS:
            continue
        row[column] = _dig_literal(params, column.split("."))
    return row


# ----------------------------------------------------------------------------
# Status / paging primitives.
# ----------------------------------------------------------------------------
def _device_cache_status():
    store = _device_store
    indexes = {}
    for name, spec in DEVICE_INDEXES.items():
        indexes[name] = {
            "path": spec["path"],
            "device_type": spec.get("device_type"),
            "values": len(store["index"].get(name, {})),
        }
    blob_bytes = _cache_meta.get("blob_bytes", 0)
    approx_bytes = blob_bytes + len(store["slim"]) * 160  # + slim/index estimate
    return {
        "state": _cache_meta["state"],
        "count": _cache_meta["count"],
        "loaded": _cache_meta["loaded"],
        "built_at": _cache_meta["built_at"],
        "indexes": indexes,
        "persisted_path": _device_cache_path(),
        "error": _cache_meta["error"],
        "bytes": approx_bytes,
        "generation": _cache_meta.get("generation", 0),
        "page_size": _cache_meta.get("page_size", DEVICE_PAGE_SIZE),
    }


def _budget_page_ids(blobs, ids, offset, max_bytes, projector):
    """Decompress ``ids`` from ``offset``, projecting each, until the JSON byte budget.

    Returns ``(page, next_offset)``; always yields at least one row when any remain.
    """
    page, size, i, total = [], 0, offset, len(ids)
    while i < total:
        blob = blobs.get(ids[i])
        if blob is None:
            i += 1
            continue
        row = projector(_decompress_record(blob))
        row_bytes = len(json.dumps(row, default=str).encode("utf-8"))
        if page and size + row_bytes > max_bytes:
            break
        page.append(row)
        size += row_bytes
        i += 1
    return page, (i if i < total else None)


def _require_index(index_name):
    if index_name not in DEVICE_INDEXES:
        configured = ", ".join(sorted(DEVICE_INDEXES)) or "(none configured)"
        raise ValueError("unknown device index %r. Configured: %s." % (index_name, configured))


def _start_device_cache_load_async():
    if _cache_meta["state"] in ("loading", "ready"):
        return

    def _bg():
        try:
            _reload_device_cache(force=False)
        except Exception:
            pass

    threading.Thread(target=_bg, name="bridge-device-cache-load", daemon=True).start()


# ----------------------------------------------------------------------------
# space_schema (builds the digest in the background).
# ----------------------------------------------------------------------------
_schema_cache = {"digest": None}
_schema_build = {
    "state": "empty", "started_at": None,
    "loaded_flows": 0, "total_flows": None, "error": None,
}
_schema_lock = threading.Lock()


def _ensure_blt_analytics_on_path():
    flow_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(flow_dir)
    if repo_root not in sys.path:
        sys.path.append(repo_root)


def _import_digest():
    _ensure_blt_analytics_on_path()
    from blt_analytics import digest
    return digest


def _page_flow_runs(flow_id, max_runs):
    by_id = {}
    offset = 0
    while True:
        page = [_run_to_dict(r) for r in
                blt.search_flow_run_history(flow_id=flow_id, limit=RUN_PAGE_SIZE, offset=offset)]
        if not page:
            break
        for record in page:
            by_id[record["id"]] = record
        offset += len(page)
        if len(page) < RUN_PAGE_SIZE or (max_runs and len(by_id) >= max_runs):
            break
    records = list(by_id.values())
    hit_cap = bool(max_runs and len(records) >= max_runs)
    return (records[:max_runs] if max_runs else records), hit_cap


def _build_space_schema(refresh, max_runs_per_flow):
    with _schema_lock:
        if not refresh and _schema_cache.get("digest") is not None:
            _schema_build["state"] = "ready"
            return _schema_cache["digest"]
        _schema_build.update(state="building", started_at=_iso_now(),
                             loaded_flows=0, total_flows=None, error=None)
        try:
            digest_mod = _import_digest()
        except Exception as exc:
            _schema_build.update(state="error", error="%s: %s" % (type(exc).__name__, exc))
            raise RuntimeError("space_schema unavailable on this Runner: %s" % exc) from exc
        try:
            # When the device cache is ready, sample at most SCHEMA_SAMPLE_PER_TYPE
            # records per device type from it (never pages all 400k devices) and feed
            # the true per-type counts so the digest's counts stay exact. Otherwise
            # page the Runner (the cache-cold fallback).
            if _cache_meta["state"] == "ready":
                device_records, device_counts = _sample_device_records_for_schema()
            else:
                device_records, device_counts = list(_page_all_devices().values()), None
            flow_records = [_flow_to_dict(f) for f in blt.search_flows()]
            _schema_build["total_flows"] = len(flow_records)
            run_records, truncated = [], set()
            for flow in flow_records:
                records, hit_cap = _page_flow_runs(flow["id"], max_runs_per_flow)
                run_records.extend(records)
                if hit_cap:
                    truncated.add(flow["id"])
                _schema_build["loaded_flows"] += 1
            digest = digest_mod.build_digest(
                device_records, flow_records, run_records, device_counts=device_counts
            )
            if truncated:
                digest["totals"]["runs_truncated"] = True
                key_by_id = digest_mod.flow_key(flow_records)
                for flow_id in truncated:
                    entry = digest["flows"].get(key_by_id.get(flow_id))
                    if entry is not None:
                        entry["truncated"] = True
                        entry["runs_sampled"] = entry.get("run_count", 0)
        except Exception as exc:
            _schema_build.update(state="error", error="%s: %s" % (type(exc).__name__, exc))
            raise
        _schema_cache["digest"] = digest
        _schema_build.update(state="ready", error=None)
        return digest


def _space_schema_status_dict():
    state = _schema_build["state"]
    if state != "building" and _schema_cache.get("digest") is not None:
        state = "ready"
    out = {
        "state": state,
        "progress": {
            "loaded_flows": _schema_build["loaded_flows"],
            "total_flows": _schema_build["total_flows"],
            "started_at": _schema_build["started_at"],
        },
        "error": _schema_build["error"],
    }
    if state == "ready":
        out["digest"] = _schema_cache["digest"]
    return out


def _start_schema_build_async(refresh, max_runs_per_flow):
    if _schema_build["state"] == "building":
        return
    _schema_build["state"] = "building"

    def _bg():
        try:
            _build_space_schema(refresh, max_runs_per_flow)
        except Exception:
            pass

    threading.Thread(target=_bg, name="bridge-space-schema-build", daemon=True).start()


# ----------------------------------------------------------------------------
# Tunnel functions (the ``tunnel`` op namespace).
# ----------------------------------------------------------------------------
def tn_refresh_device_cache(wait=False):
    if wait:
        try:
            _reload_device_cache(force=True)
        except Exception:
            pass
        return _device_cache_status()

    def _bg():
        try:
            _reload_device_cache(force=True)
        except Exception:
            pass

    threading.Thread(target=_bg, name="bridge-device-cache-refresh", daemon=True).start()
    return _device_cache_status()


def tn_cached_devices(index=None, value=None, *, refresh=False, offset=0,
                      max_bytes=DEFAULT_CACHE_MAX_BYTES):
    _require_index(index)
    if _cache_meta["state"] != "ready":
        _start_device_cache_load_async()
        return {"state": "loading", "devices": [], "next_offset": None, "total": 0,
                "offset": int(offset or 0), "loaded": _cache_meta["loaded"],
                "count": _cache_meta["count"], "error": _cache_meta["error"]}
    if refresh:
        _refresh_index_value(index, value)
    with _device_cache_lock:
        store = _device_store
        slim = store["slim"]
        ids = [i for i in store["index"].get(index, {}).get(str(value), []) if i in store["blobs"]]
        ids.sort(key=lambda i: (slim[i]["name"] or "", i))
        blobs = store["blobs"]
    offset = int(offset or 0)
    page, next_offset = _budget_page_ids(
        blobs, ids, offset, int(max_bytes or DEFAULT_CACHE_MAX_BYTES), lambda r: r
    )
    return {"state": "ready", "devices": page, "next_offset": next_offset,
            "total": len(ids), "offset": offset}


def tn_cached_devices_query(device_type=None, keys=None, offset=0,
                            max_bytes=DEFAULT_CACHE_MAX_BYTES, limit=0):
    if _cache_meta["state"] != "ready":
        _start_device_cache_load_async()
        return {"state": "loading", "devices": [], "total": 0,
                "next_offset": None, "offset": int(offset or 0)}
    with _device_cache_lock:
        store = _device_store
        ids = list(store["blobs"].keys())
        if device_type is not None:
            wanted = set(device_type if isinstance(device_type, (list, tuple, set)) else [device_type])
            slim = store["slim"]
            ids = [i for i in ids if slim[i]["type"] in wanted]
        ids.sort()  # by id, the stable order this op has always used
        blobs = store["blobs"]
    total = len(ids)
    offset = int(offset or 0)
    # ``limit`` is a TOTAL cap counted from offset 0, not a per-page size: the client
    # re-sends the same limit with each next_offset page, so the window must stop at
    # ``cap`` and next_offset must be None once the cap is reached.
    cap = min(int(limit), total) if limit else total
    window = ids[:cap]
    projector = (lambda r: r) if keys is None else (
        lambda r: {**r, "params": _project_params(r.get("params") or {}, keys)}
    )
    page, next_offset = _budget_page_ids(
        blobs, window, offset, int(max_bytes or DEFAULT_CACHE_MAX_BYTES), projector
    )
    return {"devices": page, "total": total, "offset": offset, "next_offset": next_offset}


# --- query_devices / query_fingerprint / index_values / refresh_devices -----
def _loading_query_page(offset):
    return {"state": "loading", "source": "cache", "columns": {}, "count": 0,
            "total": None, "offset": int(offset or 0), "next_offset": None,
            "fingerprint": None, "generation": None}


def _query_devices_cache(filters, keys, offset, max_bytes):
    with _device_cache_lock:
        store = _device_store
        ids = _cached_filter_ids(store, filters)
        fingerprint = _cached_fingerprint(store, filters, ids)
        columns = _columns_for(store, filters, ids, keys)
        generation = store["generation"]
        blobs = store["blobs"]
    total = len(ids)
    col_lists = {column: [] for column in columns}
    size, i, count = 0, offset, 0
    while i < total:
        blob = blobs.get(ids[i])
        if blob is None:
            i += 1
            continue
        values = _row_values(_decompress_record(blob), keys, columns)
        row_bytes = len(json.dumps([values.get(c) for c in columns], default=str).encode("utf-8"))
        if count and size + row_bytes > max_bytes:
            break
        for column in columns:
            col_lists[column].append(values.get(column))
        size += row_bytes
        i += 1
        count += 1
    return {"state": "ready", "source": "cache", "columns": col_lists, "count": count,
            "total": total, "offset": offset, "next_offset": (i if i < total else None),
            "fingerprint": fingerprint, "generation": generation}


def _query_devices_live(filters, keys, offset, max_bytes):
    kwargs = {}
    globs = _as_glob_list(filters.get("name"))
    if globs and len(globs) == 1:
        kwargs["name"] = globs[0]
    types = _as_type_list(filters.get("type"))
    if types and len(types) == 1:
        kwargs["type"] = types[0]
    if filters.get("tags"):
        kwargs["tags"] = list(filters["tags"])
    if filters.get("archived") is not None:
        kwargs["archived"] = bool(filters["archived"])
    page_devices, size = _live_search_page(offset, kwargs)
    records = [r for r in (_device_to_dict(d) for d in page_devices) if _record_matches(r, filters)]
    if keys is None:
        columns = list(_IDENTITY_COLUMNS) + ["params"]
    else:
        columns = list(_IDENTITY_COLUMNS) + _discover_param_columns(
            {r["id"]: _compress_record(r) for r in records}, [r["id"] for r in records], keys
        )
    col_lists = {column: [] for column in columns}
    for record in records:
        values = _row_values(record, keys, columns)
        for column in columns:
            col_lists[column].append(values.get(column))
    next_offset = offset + len(page_devices) if len(page_devices) == size else None
    return {"state": "ready", "source": "live", "columns": col_lists, "count": len(records),
            "total": None, "offset": offset, "next_offset": next_offset,
            "fingerprint": None, "generation": None}


def tn_query_devices(*, name=None, type=None, tags=None, where=None, archived=False,
                     keys=None, source="auto", refresh=False, offset=0,
                     max_bytes=DEFAULT_QUERY_MAX_BYTES):
    if where:
        for index_name in where:
            _require_index(index_name)
    filters = {"name": name, "type": type, "tags": tags, "where": where, "archived": archived}
    keys = list(keys) if keys is not None else None
    offset = int(offset or 0)
    max_bytes = int(max_bytes or DEFAULT_QUERY_MAX_BYTES)
    if source == "live":
        return _query_devices_live(filters, keys, offset, max_bytes)
    ready = _cache_meta["state"] == "ready"
    if source == "cache":
        if not ready:
            _start_device_cache_load_async()
            return _loading_query_page(offset)
        if refresh:
            _refresh_devices_scope(filters)
        return _query_devices_cache(filters, keys, offset, max_bytes)
    # source == "auto": the cache when ready, else kick off the load and go live.
    if ready:
        if refresh:
            _refresh_devices_scope(filters)
        return _query_devices_cache(filters, keys, offset, max_bytes)
    _start_device_cache_load_async()
    return _query_devices_live(filters, keys, offset, max_bytes)


def tn_query_fingerprint(*, name=None, type=None, tags=None, where=None, archived=False):
    if where:
        for index_name in where:
            _require_index(index_name)
    filters = {"name": name, "type": type, "tags": tags, "where": where, "archived": archived}
    if _cache_meta["state"] != "ready":
        _start_device_cache_load_async()
        return {"state": "loading", "fingerprint": None, "count": 0, "generation": None}
    with _device_cache_lock:
        store = _device_store
        ids = _cached_filter_ids(store, filters)
        fingerprint = _cached_fingerprint(store, filters, ids)
        generation = store["generation"]
    return {"state": "ready", "fingerprint": fingerprint, "count": len(ids),
            "generation": generation}


def tn_index_values(index):
    _require_index(index)
    if _cache_meta["state"] != "ready":
        _start_device_cache_load_async()
        return {"state": "loading", "values": {}}
    with _device_cache_lock:
        bucket = _device_store["index"].get(index, {})
        values = {value: len(ids) for value, ids in bucket.items()}
    return {"state": "ready", "values": values}


def _refresh_devices_scope(filters):
    """Re-pull the live scope, upsert every returned device, drop vanished ids."""
    kwargs = {}
    globs = _as_glob_list(filters.get("name"))
    if globs and len(globs) == 1:
        kwargs["name"] = globs[0]
    types = _as_type_list(filters.get("type"))
    if types and len(types) == 1:
        kwargs["type"] = types[0]
    if filters.get("tags"):
        kwargs["tags"] = list(filters["tags"])
    if filters.get("archived") is not None:
        kwargs["archived"] = bool(filters["archived"])
    pulled = {}
    offset = 0
    while True:
        page, size = _live_search_page(offset, kwargs)
        if not page:
            break
        for device in page:
            record = _device_to_dict(device)
            pulled[record["id"]] = record
        offset += len(page)
        if len(page) < size:
            break
    with _device_cache_lock:
        store = _device_store
        existing_matching = set(_filter_ids(store, **filters))
        added = updated = 0
        for rid, record in pulled.items():
            old = store["blobs"].get(rid)
            _upsert_record(store, record)
            if old is None:
                added += 1
            elif store["blobs"][rid][1] != old[1]:
                updated += 1
        removed_ids = [rid for rid in existing_matching if rid not in pulled]
        for rid in removed_ids:
            _remove_record(store, rid)
        _bump_generation(store)
        generation = store["generation"]
    _schedule_save()
    return {"updated": updated, "added": added, "removed": len(removed_ids),
            "generation": generation}


def tn_refresh_devices(*, name=None, type=None, tags=None, where=None, archived=None):
    if where:
        for index_name in where:
            _require_index(index_name)
    filters = {"name": name, "type": type, "tags": tags, "where": where, "archived": archived}
    if _cache_meta["state"] != "ready":
        _start_device_cache_load_async()
        return {"state": "loading", "updated": 0, "added": 0, "removed": 0,
                "generation": _cache_meta.get("generation", 0)}
    return {"state": "ready", **_refresh_devices_scope(filters)}


def _sample_device_records_for_schema():
    """Up to SCHEMA_SAMPLE_PER_TYPE records per device type, plus the true per-type counts."""
    with _device_cache_lock:
        store = _device_store
        counts, sample_ids = {}, []
        buckets = {}
        for rid, row in store["slim"].items():
            dtype = row["type"] or "device"
            counts[dtype] = counts.get(dtype, 0) + 1
            bucket = buckets.setdefault(dtype, [])
            if len(bucket) < SCHEMA_SAMPLE_PER_TYPE:
                bucket.append(rid)
        for bucket in buckets.values():
            sample_ids.extend(bucket)
        blobs = store["blobs"]
        sample = [_decompress_record(blobs[rid]) for rid in sample_ids if rid in blobs]
    return sample, counts


def tn_space_schema(refresh=False, max_runs_per_flow=2000):
    if not refresh and _schema_cache.get("digest") is not None:
        return _space_schema_status_dict()
    _start_schema_build_async(bool(refresh), int(max_runs_per_flow))
    return _space_schema_status_dict()


TUNNEL = {
    "device_cache_status": _device_cache_status,
    "refresh_device_cache": tn_refresh_device_cache,
    "cached_devices": tn_cached_devices,
    "cached_devices_query": tn_cached_devices_query,
    "query_devices": tn_query_devices,
    "query_fingerprint": tn_query_fingerprint,
    "index_values": tn_index_values,
    "refresh_devices": tn_refresh_devices,
    "space_schema": tn_space_schema,
}


# ----------------------------------------------------------------------------
# HTTP handler.
# ----------------------------------------------------------------------------
INDEX_PAGE = b"""<!doctype html>
<meta charset="utf-8">
<title>Balthazar remote bridge</title>
<body style="font-family: system-ui, sans-serif; max-width: 820px; margin: 48px auto; padding: 0 16px">
<h2>Remote bridge is running</h2>
{note}
<p>Call the Balthazar Python API from a script on your computer while this flow run is alive:</p>
<pre id="snippet" style="background: #f4f4f5; padding: 16px; border-radius: 8px; overflow-x: auto"></pre>
<script>
document.getElementById("snippet").textContent = [
  "import balthazar_remote",
  "",
  'blt = balthazar_remote.connect("' + window.location.href + '")',
  "",
  "for device in blt.search_devices():",
  "    print(device.name, device.params)",
].join("\\n");
</script>
"""
SHARED_NOTE = (
    b"<p><b>This bridge is shared.</b> Every call runs as the user who started it "
    b"and is written to the log of this flow run with the id of the caller.</p>"
)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def reply(self, status, body, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def caller(self):
        return (self.headers.get("X-Blt-User-Id") or "").lower()

    def is_allowed(self):
        caller = self.caller()
        if not caller:
            return False
        if SHARED:
            return True
        return caller == owner_id() or caller in ALLOWED_USERS

    def from_browser(self):
        return bool(self.headers.get("Origin") or self.headers.get("Sec-Fetch-Site"))

    def read_body(self):
        if "chunked" not in (self.headers.get("Transfer-Encoding") or "").lower():
            return self.rfile.read(int(self.headers.get("Content-Length") or 0))
        chunks = []
        while True:
            size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
            if size == 0:
                while self.rfile.readline().strip():
                    pass
                return b"".join(chunks)
            chunks.append(self.rfile.read(size))
            self.rfile.readline()

    def do_GET(self):
        if self.path.split("?")[0] != "/":
            self.reply(404, b"Not found", "text/plain")
        elif not self.is_allowed():
            self.reply(403, b"This remote bridge belongs to another user", "text/plain")
        else:
            page = INDEX_PAGE.replace(b"{note}", SHARED_NOTE if SHARED else b"")
            self.reply(200, page, "text/html; charset=utf-8")

    def do_POST(self):
        body = self.read_body()
        if self.path.split("?")[0] != "/call":
            self.reply(404, b"Not found", "text/plain")
            return
        if not self.is_allowed():
            self.reply(403, b"This remote bridge belongs to another user", "text/plain")
            return
        if self.from_browser():
            self.reply(403, b"The remote bridge does not accept calls from a browser", "text/plain")
            return
        caller = self.caller()
        state = caller_state(caller)
        try:
            upload = self.headers.get("X-Bridge-Upload")
            if upload:
                index = int(self.headers.get("X-Bridge-Index"))
                count = int(self.headers.get("X-Bridge-Count"))
                body = add_part(caller, upload, index, count, body)
            if body is None:
                response = {"ok": True, "result": None}
            else:
                request = json.loads(body)
                op = request.get("op")
                if op == "part":
                    part = take_part(caller, request.get("id"), request.get("index"))
                    if part is None:
                        self.reply(410, b"This part is no longer kept, repeat the call", "text/plain")
                    else:
                        self.reply(200, part, "application/octet-stream")
                    return
                if op == "describe":
                    response = {"ok": True, "result": describe_module(caller)}
                elif op == "heartbeat":
                    response = {"ok": True, "result": None}
                elif op == "release":
                    release_refs(state, request.get("refs", []))
                    response = {"ok": True, "result": None}
                elif op == "poll":
                    response = poll(state, request.get("job"))
                else:
                    audit(caller, state, request)
                    response = submit(state, caller, request)
        except Exception as error:
            response = error_response(error, caller)
        answer = json.dumps(response).encode()
        if len(answer) > PART_BYTES and self.headers.get("X-Bridge-Parts"):
            answer = json.dumps(offer_parts(caller, answer)).encode()
        self.reply(200, answer)


# ----------------------------------------------------------------------------
# Startup.
# ----------------------------------------------------------------------------
def _warm_cache_async():
    def _bg():
        try:
            if not _load_device_cache_from_disk():
                _reload_device_cache(force=False)
        except Exception as exc:
            blt.warn("[bridge] device cache warm failed: %s: %s" % (type(exc).__name__, exc))

    threading.Thread(target=_bg, name="bridge-warm", daemon=True).start()


def start():
    """Configure from the flow params, start the background threads and serve."""
    global _SAVE_ENABLED
    configure()
    _SAVE_ENABLED = True  # from here on, small changes schedule a debounced save
    if DEVICE_INDEXES:
        try:
            if _load_device_cache_from_disk():
                blt.info("[bridge] loaded %d device(s) from %s"
                         % (_cache_meta["count"], _device_cache_path()))
            elif WARM_DEVICE_CACHE:
                _warm_cache_async()
        except Exception as exc:
            blt.warn("[bridge] device cache init failed: %s: %s" % (type(exc).__name__, exc))
    stop = threading.Event()
    threading.Thread(target=_watchdog_loop, args=(stop,), name="bridge-watchdog", daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server._bridge_stop = stop
    blt.serve_app(server.server_address[1])
    return server


if __name__ == "__main__":
    server = start()
    blt.info("Remote bridge is running, open the app to get the connection snippet")
    try:
        server.serve_forever()
    finally:
        server._bridge_stop.set()
        _flush_pending_save()  # clean shutdown: persist any debounced changes
        server.server_close()
