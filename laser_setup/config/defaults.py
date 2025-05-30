import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..display.Qt import QtWidgets
from .log import default_log_config
from .parser import CLIArguments


class DefaultPaths:
    """Default paths for the configuration files."""
    CONFIG_ENV_NAME = 'CONFIG'
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
        default=os.getenv(DefaultPaths.CONFIG_ENV_NAME) or str(DefaultPaths.user_config),
        metadata={'title': 'Global configuration file', 'readonly': True}
    )
    local_config_file: str = field(
        default=str(DefaultPaths.user_config),
        metadata={'title': 'Local configuration file', 'readonly': True}
    )
    parameters_file: str = field(
        default=str(DefaultPaths.parameters),
        metadata={'title': 'Parameters file', 'type': 'file'}
    )
    procedures_file: str = field(
        default=str(DefaultPaths.procedures),
        metadata={'title': 'Procedures file', 'type': 'file'}
    )
    sequences_file: str = field(
        default=str(DefaultPaths.sequences),
        metadata={'title': 'Sequences file', 'type': 'file'}
    )
    instruments_file: str = field(
        default=str(DefaultPaths.instruments),
        metadata={'title': 'Instruments file', 'type': 'file'}
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
        default=DefaultPaths.splash,
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
        default=str(DefaultPaths.splash),
        metadata={'title': 'Icon', 'type': 'file'}
    )


@dataclass
class MenuItemConfig:
    name: str
    target: Any
    kwargs: dict[str, Any] = field(default_factory=dict)


ScriptsConfig = dict[str, MenuItemConfig]
ProceduresConfig = dict[str, Any]
SequencesConfig = dict[str, Any]


@dataclass
class InstrumentConfig:
    adapter: Any
    target: Any | None = None
    name: str | None = None
    IDN: str | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)


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
        default=str(DefaultPaths.splash),
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
    instruments: dict[str, InstrumentConfig] = field(
        default='${instruments}',
        metadata={'title': 'Instruments', 'readonly': True}
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
class TelegramConfig:
    token: str | None = field(default='', metadata={'title': 'Token'})
    chat_ids: list[str] = field(default_factory=list, metadata={'title': 'Chat IDs'})


@dataclass
class SessionConfig:
    args: CLIArguments = field(
        default_factory=CLIArguments,
        metadata={'title': 'Command line arguments', 'readonly': True}
    )
    save_path: str = field(
        default=DefaultPaths.user_config,
        metadata={'title': 'Save path', 'type': 'file'}
    )
    config_path_used: str = field(
        default='default',
        metadata={'title': 'Configuration path used', 'readonly': True}
    )


@dataclass
class AppConfig:
    Dir: DirConfig = field(default_factory=DirConfig, metadata={'title': 'Directories'})
    Qt: QtConfig = field(default_factory=QtConfig)
    Filename: FilenameConfig = field(default_factory=FilenameConfig)
    Logging: dict[str, Any] = field(
        default_factory=lambda: default_log_config,
        metadata={'title': 'Logging configuration'}
    )
    matplotlib_rcParams: dict[str, str] = field(
        default_factory=lambda: {'axes.grid': 'True', 'figure.autolayout': 'True'},
        metadata={'title': 'Matplotlib rcParams'}
    )
    Telegram: TelegramConfig = field(default_factory=TelegramConfig, metadata={'expanded': False})

    parameters: dict[str, Any] = field(
        default_factory=dict,
        metadata={'title': 'Parameters', 'readonly': True}
    )

    scripts: ScriptsConfig = field(
        default_factory=lambda: {
            'init': MenuItemConfig(
                name='Init Config',
                target='${function:laser_setup.cli.init_config.init_config}'
            ),
            'setup_adapters': MenuItemConfig(
                name="Set up Adapters",
                target='${function:laser_setup.cli.setup_adapters.setup}'
            ),
            'get_updates': MenuItemConfig(
                name="Get updates",
                target='${function:laser_setup.cli.get_updates.main}'
            ),
        },
        metadata={'title': 'Scripts', 'readonly': True}
    )
    procedures: ProceduresConfig = field(
        default_factory=lambda: {'_types': {}},
        metadata={'title': 'Procedures', 'readonly': True}
    )
    sequences: SequencesConfig = field(
        default_factory=lambda: {'_types': {}},
        metadata={'title': 'Sequences', 'readonly': True}
    )
    # OmegaConf does not support dict[str, dataclass] as default factory.
    # Elements of instruments won't have the InstrumentConfig structure.
    instruments: dict[str, InstrumentConfig] = field(
        default_factory=dict,
        metadata={'title': 'Instruments', 'readonly': True}
    )
    _session: SessionConfig = field(
        default_factory=SessionConfig,
        metadata={'title': 'Session', 'readonly': True}
    )
