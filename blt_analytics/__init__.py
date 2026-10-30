"""Schema-only analytics over the Balthazar reflection bridge.

The public API is re-exported lazily (PEP 562 ``__getattr__``) for two reasons:

* **No heavy imports at import time.** ``frames`` needs pandas and ``mcp_server``
  needs the mcp SDK; neither should load merely because someone did
  ``import blt_analytics``. Each name pulls in its module only when first touched.
* **Sibling modules may not exist yet.** This package is built by several agents
  in parallel; ``schema``/``frames``/``publish`` land after this file. A plain
  ``from .schema import ...`` would make the whole package unimportable until then,
  which would block the modules that *are* ready. With lazy lookup, only accessing
  a not-yet-written name fails, and with a clear message.
"""

from __future__ import annotations

import importlib

# Public name -> the submodule that defines it.
_EXPORTS = {
    # digest (stdlib-only; present now)
    "build_digest": "digest",
    # tunnel locator (present now)
    "get_blt": "_blt",
    "is_tunnel": "_blt",
    # schema tools
    "get_digest": "schema",
    "overview": "schema",
    "device_schema": "schema",
    "describe_param": "schema",
    "flow_schema": "schema",
    "describe_output": "schema",
    "find": "schema",
    "load_snippet": "schema",
    "set_digest": "schema",
    "reset": "schema",
    # data frames
    "devices_df": "frames",
    "query_devices_df": "frames",
    "runs_df": "frames",
    "explode_devices": "frames",
    "series_to_df": "frames",
    "matrix_to_df": "frames",
    # publishing figures back to a flow run
    "publish": "publish",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(f".{module_name}", __name__)
    return getattr(module, name)


def __dir__():
    return sorted(list(globals()) + __all__)
