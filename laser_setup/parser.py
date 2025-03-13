"""Module to parse CLI arguments"""
import argparse

from . import __version__
from .config import config

experiment_list = [i.alias for i in config.Qt.MainWindow.procedures]
script_list = [i.alias for i in config.Qt.MainWindow.scripts]

parser = argparse.ArgumentParser(description='Laser Setup')
parser.add_argument('procedure', nargs='?', help='Procedure to run',
                    choices=experiment_list + script_list)
parser.add_argument(
    '-v', '--version', action='version', version=f'%(prog)s {__version__}'
)
parser.add_argument('-d', '--debug', action='store_true',
                    default=False, help='Enable debug mode')
