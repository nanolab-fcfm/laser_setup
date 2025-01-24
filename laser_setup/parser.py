"""Module to parse CLI arguments"""
import argparse

from .config import Qt_config
from .config.Qt import MenuItemConfig
from . import __version__

experiment_list = [i.alias for i in Qt_config.MainWindow.procedures]
script_list = [i.alias for i in Qt_config.MainWindow.scripts]

parser = argparse.ArgumentParser(description='Laser Setup')
parser.add_argument('procedure', nargs='?', help='Procedure to run',
                    choices=experiment_list + script_list)
parser.add_argument(
    '-v', '--version', action='version', version=f'%(prog)s {__version__}'
)
parser.add_argument('-d', '--debug', action='store_true',
                    default=False, help='Enable debug mode')

args = parser.parse_args()

if args.debug:
    Qt_config.MainWindow.procedures.extend((
        MenuItemConfig(
            name='Fake Procedure',
            target='${class:laser_setup.procedures.FakeProcedure.FakeProcedure}',
            alias='FakeProcedure'
        ),
        MenuItemConfig(
            name='Fake IVg',
            target='${class:laser_setup.procedures.FakeProcedure.FakeIVg}',
            alias='FakeIVg'
        )
    ))
