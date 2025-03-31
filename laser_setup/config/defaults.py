import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from omegaconf import MISSING

from ..display.Qt import QtWidgets
from .parameters import ParameterCatalog


class DefaultPaths:
    """Default paths for the configuration files."""
    _parent = Path(__file__).parent
    assets: Path = _parent.parent / 'assets'
    new_config: Path = assets / 'new_config.yaml'
    allowed_files: str = 'YAML files (*.yaml)'
    templates: Path = assets / 'templates'
    config: Path = templates / 'config.yaml'
    user_config = Path('config') / 'config.yaml'
    parameters: Path = templates / 'parameters.yaml'
    procedures: Path = templates / 'procedures.yaml'
    sequences: Path = templates / 'sequences.yaml'
    instruments: Path = templates / 'instruments.yaml'
    logs: Path = Path('log') / 'std.log'
    splash: Path = assets / 'img' / 'splash.png'


@dataclass
class DirConfig:
    global_config_file: str = field(
        default=os.getenv('CONFIG') or DefaultPaths.user_config.as_posix(),
        metadata={'title': 'Global configuration file', 'readonly': True}
    )
    local_config_file: str = field(
        default=DefaultPaths.user_config.as_posix(),
        metadata={'title': 'Local configuration file', 'readonly': True}
    )
    parameters_file: str = field(
        default=DefaultPaths.parameters.as_posix(),
        metadata={'title': 'Parameters file', 'type': 'file'}
    )
    procedures_file: str = field(
        default=DefaultPaths.procedures.as_posix(),
        metadata={'title': 'Procedures file', 'type': 'file'}
    )
    sequences_file: str = field(
        default=DefaultPaths.sequences.as_posix(),
        metadata={'title': 'Sequences file', 'type': 'file'}
    )
    data_dir: str = field(
        default='data',
        metadata={'title': 'Data directory', 'type': 'file'}
    )
    database: str = field(
        default='database.db',
        metadata={'title': 'Database file', 'type': 'str'}
    )


@dataclass
class AdapterConfig:
    keithley2450: str = ''
    tenma_neg: str = ''
    tenma_pos: str = ''
    tenma_laser: str = ''
    power_meter: str = ''
    pt100_port: str = ''
    clicker: str = ''
    light_source: str = ''


@dataclass
class GUIConfig:
    style: str = field(
        default='Fusion',
        metadata={'title': 'Style', 'type': 'list', 'limits': QtWidgets.QStyleFactory.keys()}
    )
    dark_mode: bool = field(
        default=True,
        metadata={'title': 'Dark mode', 'type': 'bool'}
    )
    font: str = field(
        default='Segoe UI',
        metadata={'title': 'Font', 'type': 'font'}
    )
    font_size: int = field(
        default=12,
        metadata={'title': 'Font size', 'type': 'int'}
    )
    splash_image: str = field(
        default=DefaultPaths.splash.as_posix(),
        metadata={'title': 'Splash image', 'type': 'file'}
    )


@dataclass
class ExperimentWindowConfig:
    title: str = field(
        default='',
        metadata={'title': 'Title', 'type': 'str'}
    )
    inputs_in_scrollarea: bool = field(
        default=True,
        metadata={'title': 'Inputs in scroll area', 'type': 'bool'}
    )
    enable_file_input: bool = field(
        default=False,
        metadata={'title': 'Enable file input', 'type': 'bool'}
    )
    dock_plot_number: int = field(
        default=2,
        metadata={'title': 'Number of plots in dock tab', 'type': 'int'}
    )
    info_file: str = field(
        default='',
        metadata={'title': 'Info file', 'type': 'file'}
    )
    icon: str = field(
        default='',
        metadata={'title': 'Icon', 'type': 'file'}
    )


@dataclass
class MenuItemConfig:
    name: str
    target: Any


ScriptsConfig = dict[str, MenuItemConfig]
ProceduresConfig = dict[str, Any]
SequencesConfig = dict[str, Any]


@dataclass
class MainWindowConfig:
    title: str = field(
        default='Laser Setup',
        metadata={'title': 'Title'}
    )
    readme_file: str = field(
        default='README.md',
        metadata={'title': 'Readme file', 'type': 'file'}
    )
    size: tuple[int, int] = field(
        default=(640, 480),
        metadata={'title': 'Size'}
    )
    widget_size: tuple[int, int] = field(
        default=(640, 480),
        metadata={'title': 'Widget size'}
    )
    icon: str = field(
        default='',
        metadata={'title': 'Icon', 'type': 'file'}
    )
    scripts: ScriptsConfig = field(
        default='${scripts}',
        metadata={'title': 'Scripts', 'readonly': True}
    )
    procedures: ProceduresConfig = field(
        default='${procedures}',
        metadata={'title': 'Procedures', 'readonly': True}
    )
    sequences: SequencesConfig = field(
        default='${sequences}',
        metadata={'title': 'Sequences', 'readonly': True}
    )


@dataclass
class SequenceWindowConfig:
    abort_timeout: float = field(
        default=30.,
        metadata={'title': 'Abort timeout'}
    )


@dataclass
class QtConfig:
    GUI: GUIConfig = field(default_factory=GUIConfig)
    MainWindow: MainWindowConfig = field(
        default_factory=MainWindowConfig,
        metadata={'title': 'Main Window'}
    )
    ExperimentWindow: ExperimentWindowConfig = field(
        default_factory=ExperimentWindowConfig,
        metadata={'title': 'Experiment Window'}
    )
    SequenceWindow: SequenceWindowConfig = field(
        default_factory=SequenceWindowConfig,
        metadata={'title': 'Sequence Window'}
    )


@dataclass
class FilenameConfig:
    prefix: str = field(default='', metadata={'title': 'Prefix'})
    suffix: str = field(default='', metadata={'title': 'Suffix'})
    ext: str = field(default='csv', metadata={'title': 'Extension'})
    dated_folder: bool = field(
        default=True,
        metadata={'title': 'Dated folder'}
    )
    index: bool = field(default=True, metadata={'title': 'Index'})
    datetimeformat: str = field(
        default='%Y-%m-%d',
        metadata={'title': 'Datetime format'}
    )


@dataclass
class LoggingConfig:
    console: bool = field(default=True, metadata={'title': 'Console'})
    console_level: str = field(default='INFO', metadata={'title': 'Console level'})
    filename: str = field(default=DefaultPaths.logs, metadata={'title': 'Filename', 'type': 'file'})
    file_level: str = field(default='INFO', metadata={'title': 'File level'})


@dataclass
class TelegramConfig:
    token: str | None = field(default='', metadata={'title': 'Token'})
    chat_ids: list[str] = field(default_factory=list, metadata={'title': 'Chat IDs'})


@dataclass
class AppConfig:
    Dir: DirConfig = field(default_factory=DirConfig, metadata={'title': 'Directories'})
    Adapters: AdapterConfig = field(default_factory=AdapterConfig, metadata={'expanded': False})
    Qt: QtConfig = field(default_factory=QtConfig)
    Filename: FilenameConfig = field(default_factory=FilenameConfig)
    Logging: LoggingConfig = field(default_factory=LoggingConfig)
    matplotlib_rcParams: dict[str, str] = field(
        default_factory=lambda: {'axes.grid': 'True', 'figure.autolayout': 'True'},
        metadata={'title': 'Matplotlib rcParams'}
    )
    Telegram: TelegramConfig = field(default_factory=TelegramConfig, metadata={'expanded': False})

    parameters: ParameterCatalog = field(
        default=MISSING,
        metadata={'title': 'Parameters', 'readonly': True}
    )

    scripts: ScriptsConfig = field(
        default_factory=lambda: {
            'init': MenuItemConfig(
                name='Init Config',
                target='${function:laser_setup.cli.init_config.init_config}',
            )
        },
        metadata={'title': 'Scripts'}
    )
    procedures: ProceduresConfig = field(
        default_factory=lambda: {
            'FakeProcedure': MenuItemConfig(
                name='Fake Procedure',
                target='${class:laser_setup.procedures.FakeProcedure.FakeProcedure}',
            )
        },
        metadata={'title': 'Procedures'}
    )
    sequences: SequencesConfig = field(
        default_factory=lambda: {
            'TestSequence': {
                'procedures': [
                    '${class:laser_setup.procedures.FakeProcedure.FakeProcedure}',
                    '${class:laser_setup.procedures.Wait}'
                ]
            }
        },
        metadata={'title': 'Sequences'}
    )
    _session: dict = field(default_factory=dict, metadata={'title': 'Session', 'readonly': True})
