from pymeasure.display.widgets import InputsWidget
from pymeasure.experiment import Procedure

from ..Qt import QtWidgets


class _InputsWidget(InputsWidget):
    """Wraps PyMeasure's InputsWidget to allow for both
    procedure_class or procedure as inputs.
    """
    def __init__(
        self, procedure_class: type[Procedure] | None = None,
        procedure: Procedure | None = None, inputs=(), parent=None, hide_groups=True,
        inputs_in_scrollarea=False
    ):
        QtWidgets.QWidget.__init__(self, parent)
        if procedure_class is None and procedure is None:
            raise ValueError("Either procedure_class or procedure must be provided.")

        elif procedure_class is None:
            procedure_class = type(procedure)

        elif procedure is None:
            procedure = procedure_class()

        if procedure_class is not type(procedure):
            raise ValueError(
                "procedure_class and procedure must be of the same class."
                f" Got {type(procedure)} and {procedure_class}."
            )

        self._procedure_class = procedure_class
        self._procedure = procedure
        self._inputs = inputs
        self._setup_ui()
        self._layout(inputs_in_scrollarea)
        self._hide_groups = hide_groups
        self._setup_visibility_groups()
