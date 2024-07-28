import time
import logging

from pymeasure.experiment import Procedure, IntegerParameter, Parameter, BooleanParameter, ListParameter, Metadata

from .. import config

log = logging.getLogger(__name__)


class BaseProcedure(Procedure):
    """Base procedure for all measurements. It defines basic
    parameters that have to be present in all procedures.
    """
    # Procedure version. When modified, increment
    # <parameter name>.<parameter property>.<procedure startup/shutdown>
    procedure_version = Parameter('Procedure version', default='1.5.0')
    show_more = BooleanParameter('Show more', default=False)
    info = Parameter('Information', default='None')

    # Metadata
    start_time = Metadata('Start time', fget=time.time)

    INPUTS = ['show_more', 'info']

    def update_parameters(self):
        """Function to update the parameters after the initialization,
        but before startup. It is useful to modify the parameters
        based on the values of other parameters. It is called
        only by the ExperimentWindow.
        """
        pass


class ChipProcedure(BaseProcedure):
    """Base procedure for all device-related measurements. It defines
    parameters that involve a chip.
    """
    # config
    chip_names = list(eval(config['Chip']['names'])) + ['other']
    samples = list(eval(config['Chip']['samples']))

    # Chip Parameters
    chip_group = ListParameter('Chip group name', choices=chip_names)
    chip_number = IntegerParameter('Chip number', default=1, minimum=1)
    sample = ListParameter('Sample', choices=samples)

    INPUTS = BaseProcedure.INPUTS + ['chip_group', 'chip_number', 'sample']
