from dataclasses import dataclass, field
from typing import Any

from ..config import DefaultPaths


@dataclass
class GUIConfig:
    style: str = 'Fusion'
    dark_mode: bool = True
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
    readme_file: str = ''
    size: list[int] = field(default_factory=lambda: [640, 480])
    widget_size: list[int] = field(default_factory=lambda: [640, 480])
    icon: str | None = None
    scripts: ScriptsType = field(default_factory=list)
    procedures: ProceduresType = field(default_factory=list)
    sequences: SequencesType = field(default_factory=dict)


@dataclass
class SequenceWindowConfig:
    abort_timeout: float = 30.
    common_procedure: Any = ''
    inputs_ignored: list[str] = field(default_factory=list)


@dataclass
class QtConfig:
    GUI: GUIConfig = GUIConfig
    MainWindow: MainWindowConfig = MainWindowConfig
    ExperimentWindow: ExperimentWindowConfig = ExperimentWindowConfig
    SequenceWindow: SequenceWindowConfig = SequenceWindowConfig
