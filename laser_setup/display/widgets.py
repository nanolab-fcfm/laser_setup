import time

from pymeasure.display.widgets import TabWidget
from .Qt import QtWidgets, QtCore, QtSql


class ProgressBar(QtWidgets.QDialog):
    """A simple progress bar dialog."""
    def __init__(self, parent=None, title="Waiting", text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(self)
        self.label.setText(text)
        self.progress = QtWidgets.QProgressBar(self)
        self._layout.addWidget(self.label)
        self._layout.addWidget(self.progress)
        self.setLayout(self._layout)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_progress)

    def start(self, wait_time: float, fps: float = 30., decimals: int = 0):
        self.wait_time = wait_time
        self.frame_interval = 1 / fps
        self.total_frames = int(fps * wait_time)
        self.start_time = time.perf_counter()
        self.progress.setRange(0, self.total_frames)
        self.show()
        self.timer.start(max(1, round(1000 / fps)))
        self.d = decimals

    def _update_progress(self):
        elapsed_time = time.perf_counter() - self.start_time
        current_frame = int(elapsed_time / self.frame_interval)

        if current_frame >= self.total_frames:
            self.progress.setValue(self.total_frames)
            self.progress.setFormat(
                f"{self.wait_time:.{self.d}f} / {self.wait_time:.{self.d}f} s"
            )
            self.timer.stop()
            self.close()
        else:
            self.progress.setValue(current_frame)
            self.progress.setFormat(
                f"{elapsed_time:.{self.d}f} / {self.wait_time:.{self.d}f} s"
            )


class TextWidget(TabWidget, QtWidgets.QWidget):
    def __init__(self, name: str = None, parent=None, file: str = None):
        super().__init__(name, parent)
        self.view = QtWidgets.QTextEdit(self, readOnly=True)
        self.view.setReadOnly(True)
        self.view.setStyleSheet("""
            font-size: 12pt;
        """)
        try:
            with open(file, encoding='utf-8') as f:
                readme_text = f.read()
        except:
            readme_text = f'{file} not found :('
        self.view.setMarkdown(readme_text)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(0)

        vbox.addWidget(self.view)
        self.setLayout(vbox)


class SQLiteWidget(QtWidgets.QWidget):
    """Widget to display and interact with the contents of a SQLite database."""
    select_text = "Select a table..."
    def __init__(self, database: str, default_table: str = None, parent=None):
        super().__init__(parent)

        # Initialize database connection
        self.database = database
        self.con = QtSql.QSqlDatabase.addDatabase('QSQLITE')
        self.con.setDatabaseName(self.database)

        if not self.con.open():
            raise Exception(f"Unable to open database: {self.database}")

        # Initialize model
        self.model = QtSql.QSqlTableModel(self, self.con)
        if default_table:
            self.model.setTable(default_table)
            self.model.select()

        # Set up the table view
        self.view = QtWidgets.QTableView(self)
        self.view.setModel(self.model)
        self.view.resizeColumnsToContents()

        # Enable sorting on columns
        self.view.setSortingEnabled(True)

        # Make the table read-only
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        # Layout setup
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(0)
        vbox.addWidget(self.view)
        self.setLayout(vbox)

        # Add a combo box to select different tables
        self.add_table_selector()

    def add_table_selector(self):
        """Add a combo box to select different tables."""
        self.table_selector = QtWidgets.QComboBox(self)
        self.table_selector.addItem(self.select_text)

        # Populate combo box with available tables
        self.populate_table_selector()

        # Connect table selection change event
        self.table_selector.currentIndexChanged.connect(self.change_table)

        # Layout for the combo box
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(QtWidgets.QLabel(self.select_text))
        hbox.addWidget(self.table_selector)

        # Add combo box to layout
        self.layout().addLayout(hbox)

    def populate_table_selector(self):
        """Populate the combo box with available table names."""
        query = QtSql.QSqlQuery(self.con)
        query.exec("SELECT name FROM sqlite_master WHERE type='table';")

        while query.next():
            table_name = query.value(0)
            self.table_selector.addItem(table_name)

    def change_table(self):
        """Change the table displayed by the model."""
        table_name = self.table_selector.currentText()
        if table_name and table_name != self.select_text:
            self.model.setTable(table_name)
            self.model.select()

    def update(self):
        """Update the model data by re-selecting the table."""
        self.model.select()
