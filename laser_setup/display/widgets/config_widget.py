from dataclasses import fields, is_dataclass
from typing import Any

from omegaconf import OmegaConf
from pyqtgraph.parametertree import Parameter, ParameterTree

from ... import config
from ...config import ConfigHandler
from ...display.Qt import QtWidgets


class ConfigWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_handler = ConfigHandler(parent=parent, config=config)

        # Layout
        self._layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self._layout)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # Toolbar
        self.toolbar = QtWidgets.QToolBar()
        self._layout.addWidget(self.toolbar)

        save_action: QtWidgets.QWidgetAction = self.toolbar.addAction("Save")
        save_action.triggered.connect(self.save_config)
        save_action.setShortcut("Ctrl+S")

        # Parameter tree
        self.tree = ParameterTree()
        self._layout.addWidget(self.tree)

        self.root = Parameter.create(**self.create_parameter_opts())
        self.tree.setParameters(self.root, showTop=False)

    def extract_schema(self, dc: Any) -> dict:
        """Recursively build a schema from dataclass metadata."""
        schema = {}
        if not is_dataclass(dc):
            return schema
        for f in fields(dc):
            schema[f.name] = {**f.metadata}
            value = getattr(dc, f.name, None)
            if is_dataclass(value):
                schema[f.name]['children'] = self.extract_schema(value)

        return schema

    def create_parameter_opts(self) -> dict:
        config_container = OmegaConf.to_container(config)
        config_container.pop('_session', None)

        data_dc = OmegaConf.to_object(config)
        schema = {'config': {'children': self.extract_schema(data_dc)}}
        return self.parameterize('config', config_container, schema)

    def parameterize(self, key: str, obj, schema: dict = None) -> dict:
        """Recursively convert container into a ParameterTree dict, guided by schema.
        """
        param = {'name': key}
        sub_schema = {}
        if schema and key in schema:
            sub_schema = schema[key]

        sub_schema_children = sub_schema.pop('children', {})
        param.update(sub_schema)

        if isinstance(obj, (dict, list)):
            param['type'] = 'group'
            iterable = obj.items() if isinstance(obj, dict) else enumerate(obj)
            param['children'] = [
                self.parameterize(str(k), v, sub_schema_children) for k, v in iterable
            ]
        else:
            param['type'] = param.get('type', self.type_to_str(obj))
            param['value'] = obj
        return param

    def type_to_str(self, value: Any) -> str:
        if isinstance(value, (bool, int, float)):
            return type(value).__name__
        else:
            return 'str'

    def extract_parameters(self, param: Parameter):
        """Recursively converts a ParameterTree node back into a plain container.
        If the parameter type is list, children are sorted by their index.
        """
        ptype = param.opts.get('type', 'group')
        value = param.value()
        if ptype == 'group':
            value = {
                child.opts['name']: self.extract_parameters(child) for child in param.children()
            }
            if all(k.isdigit() for k in value.keys()):
                value = [value[k] for k in sorted(value.keys(), key=int)]

        elif ptype == 'font' and not isinstance(value, str):
            return value.family()   # QFont

        return value

    def save_config(self):
        new_container = self.extract_parameters(self.root)
        try:
            self.config_handler.save_config(new_container)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.parent(), "Error", str(e))
            breakpoint()
            return

        if not hasattr(self.parent(), 'reload'):
            QtWidgets.QMessageBox.information(self, "Success", "Config updated successfully!")
            return

        res = QtWidgets.QMessageBox.question(
            self, "Success", "Config updated successfully!\nReload the app?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        if res == QtWidgets.QMessageBox.StandardButton.Yes:
            self.parent().reload.click()
        else:
            self.parent().suggest_reload()
