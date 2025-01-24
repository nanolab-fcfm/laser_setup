import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class DefaultPaths:
    """Default paths for the configuration files."""
    default_config_lookup: list[tuple[str, str]] = [
        ('Dir', 'global_config_file'),
        ('Dir', 'local_config_file')
    ]
    _parent = Path(__file__).parent
    assets: Path = _parent.parent / 'assets'
    allowed_files: str = 'YAML files (*.yaml)'
    config: Path = assets / 'templates' / 'config.yaml'
    parameters: Path = assets / 'templates' / 'parameters.yaml'
    procedures: Path = assets / 'templates' / 'procedures.yaml'
    instruments: Path = assets / 'templates' / 'instruments.yaml'
    Qt: Path = assets / 'templates' / 'Qt.yaml'
    splash: Path = assets / 'img' / 'splash.png'


@dataclass
class DirConfig:
    global_config_file: str = os.getenv('CONFIG') or 'config/config.yaml'
    local_config_file: str = 'config/config.yaml'
    parameters_file: str = DefaultPaths.parameters.as_posix()
    procedure_config_file: str = DefaultPaths.procedures.as_posix()
    Qt_file: str = DefaultPaths.Qt.as_posix()
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


@dataclass
class TelegramConfig:
    token: Optional[str] = ''
    name: Optional[str] = ''
    name2: Optional[str] = ''


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
class AppConfig:
    Dir: DirConfig = DirConfig
    Adapters: AdapterConfig = AdapterConfig
    Telegram: TelegramConfig = TelegramConfig
    Filename: FilenameConfig = FilenameConfig
    Logging: LoggingConfig = LoggingConfig
    matplotlib_rcParams: dict[str, str] = field(
        default_factory=lambda: {'axes.grid': 'True', 'figure.autolayout': 'True'}
    )
    _session: dict = field(default_factory=dict)
