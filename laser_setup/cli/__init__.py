from typing import Callable
from . import console, find_dp_script, setup_adapters, get_updates, parameters_to_db

Scripts: list[tuple[Callable, str]] = [
    (setup_adapters.setup, 'Set up Adapters'),
    (console.main, 'Console'),
    (find_dp_script.main, 'Find Dirac Point'),
    (get_updates.main, 'Get Updates'),
    (parameters_to_db.create_db, 'Parameters to Database'),
]

script_list = [func.__module__.split('.')[-1] for func, desc in Scripts]
