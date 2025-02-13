from ..Qt import QtWidgets, QtSql


class SQLiteWidget(QtWidgets.QWidget):
    """Widget to display and interact with the contents of a SQLite database."""
    select_text = "Select a table..."

    def __init__(self, database: str, default_table: str | None = None, parent=None):
        super().__init__(parent)

        # Initialize database connection
        self.con_name = f"con_{id(self)}"
        self.con = QtSql.QSqlDatabase.addDatabase('QSQLITE', self.con_name)
        self.con.setDatabaseName(database)

        if not self.con.open():
            raise Exception(f"Unable to open database: {database}")

        # Initialize model
        self.model = QtSql.QSqlTableModel(self, self.con)
        if default_table:
            self.model.setTable(default_table)
            self.model.select()

        # Set up the table view
        self.view = QtWidgets.QTableView(self)
        self.view.setModel(self.model)
        self.view.resizeColumnsToContents()
        self.view.setSortingEnabled(True)
        self.view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        self.table_selector = QtWidgets.QComboBox(self)
        self.table_selector.addItem(self.select_text)

        self.populate_table_selector()

        self.table_selector.currentIndexChanged.connect(self.change_table)

        # Layout setup
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(0)
        vbox.addWidget(self.view)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(QtWidgets.QLabel(self.select_text))
        hbox.addWidget(self.table_selector)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

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

    def closeEvent(self, event):
        """Close the database connection when the widget is closed."""
        self.con.close()
        super().closeEvent(event)
