import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


class DefaultPaths:
    """Default paths for the configuration files."""
    _parent = Path(__file__).parent
    assets: Path = _parent.parent / 'assets'
    allowed_files: str = 'YAML files (*.yaml)'
    config: Path = assets / 'templates' / 'config.yaml'
    parameters: Path = assets / 'templates' / 'parameters.yaml'
    instruments: Path = assets / 'templates' / 'instruments.yaml'
    splash: Path = assets / 'img' / 'splash.png'


@dataclass
class DirConfig:
    global_config_file: str = os.getenv('CONFIG') or 'config/config.yaml'
    local_config_file: str = 'config/config.yaml'
    parameters_file: str = DefaultPaths.parameters.as_posix()
    procedure_config_file: str = ''
    data_dir: str = 'data'
    database: str = 'database.db'


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
    style: str = 'Fusion'
    dark_mode: bool = True
    font: str = ''
    font_size: int = 12
    splash_image: str = DefaultPaths.splash.as_posix()


@dataclass
class ExperimentWindowConfig:
    title: str | None = None
    inputs_in_scrollarea: bool = True
    enable_file_input: bool = True
    dock_plot_number: int = 2
    info_file: str = ''
    icon: str | None = None


@dataclass
class MenuItemConfig:
    name: str
    target: Any
    alias: str


ScriptsType = list[MenuItemConfig]
ProceduresType = list[MenuItemConfig]
SequencesType = dict[str, list[Any]]


@dataclass
class MainWindowConfig:
    title: str = 'Laser Setup'
    readme_file: str = 'README.md'
    size: tuple[int, int] = (640, 480)
    widget_size: tuple[int, int] = (640, 480)
    icon: str | None = None
    scripts: ScriptsType = field(
        default_factory=lambda: [
            MenuItemConfig(
                name='Init Config',
                target='${function:laser_setup.cli.init_config.init_config}',
                alias='init'
            )
        ]
    )
    procedures: ProceduresType = field(default_factory=list)
    sequences: SequencesType = field(default_factory=dict)


@dataclass
class SequenceWindowConfig:
    abort_timeout: int = 30
    common_procedure: Any = ''
    inputs_ignored: list[str] = field(default_factory=list)


@dataclass
class QtConfig:
    GUI: GUIConfig = field(default_factory=GUIConfig)
    MainWindow: MainWindowConfig = field(default_factory=MainWindowConfig)
    ExperimentWindow: ExperimentWindowConfig = field(default_factory=ExperimentWindowConfig)
    SequenceWindow: SequenceWindowConfig = field(default_factory=SequenceWindowConfig)


@dataclass
class FilenameConfig:
    prefix: str = ''
    suffix: str = ''
    ext: str = 'csv'
    dated_folder: bool = True
    index: bool = True
    datetimeformat: str = '%Y-%m-%d'


@dataclass
class LoggingConfig:
    console: bool = True
    console_level: str = 'INFO'
    filename: str = 'log/std.log'
    file_level: str = 'INFO'


@dataclass
class TelegramConfig:
    token: Optional[str] = ''
    chat_ids: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    Dir: DirConfig = field(default_factory=DirConfig)
    Adapters: AdapterConfig = field(default_factory=AdapterConfig)
    Qt: QtConfig = field(default_factory=QtConfig)
    Filename: FilenameConfig = field(default_factory=FilenameConfig)
    Logging: LoggingConfig = field(default_factory=LoggingConfig)
    matplotlib_rcParams: dict[str, str] = field(
        default_factory=lambda: {'axes.grid': 'True', 'figure.autolayout': 'True'}
    )
    Telegram: TelegramConfig = field(default_factory=TelegramConfig)
    _session: dict = field(default_factory=dict)
