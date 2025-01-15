from . import find_dp_script, get_updates, parameters_to_db, setup_adapters

Scripts: list[callable] = [
    setup_adapters.main,
    find_dp_script.main,
    get_updates.main,
    parameters_to_db.main,
]

script_list = [func.__module__.split('.')[-1] for func in Scripts]
