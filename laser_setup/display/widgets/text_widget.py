from pathlib import Path

from pymeasure.display.widgets import TabWidget

from ..Qt import QtWidgets


class TextWidget(TabWidget, QtWidgets.QWidget):
    def __init__(
        self,
        name: str,
        parent=None,
        file: str | None = None,
    ):
        super().__init__(name, parent)
        self.view = QtWidgets.QTextEdit(self)
        self.view.setReadOnly(True)

        self.file = Path(file) if file else None
        readme_text = (
            self.file.read_text('utf-8') if self.file and self.file.is_file()
            else f'{file} not found :('
        )

        self.view.setMarkdown(readme_text)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(0)

        vbox.addWidget(self.view)
        self.setLayout(vbox)
