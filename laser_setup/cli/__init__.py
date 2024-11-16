from . import console, find_dp_script, setup_adapters, get_updates

Scripts = [
    (setup_adapters.setup, 'Set up Adapters'),
    (console.main, 'Console'),
    (find_dp_script.main, 'Find Dirac Point'),
    (get_updates.main, 'Get Updates'),
]
