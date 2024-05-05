import time
import logging

from pymeasure.experiment import Procedure, IntegerParameter, Parameter, BooleanParameter, ListParameter, Metadata

from .. import config

log = logging.getLogger(__name__)


class BaseProcedure(Procedure):
    """Base procedure for all device-related measurements. It defines the basic
    parameters that are common to all the measurements, such as chip
    parameters.
    """
    # Procedure version. When modified, increment
    # <parameter name>.<parameter property>.<procedure startup/shutdown>
    procedure_version = Parameter('Procedure version', default='1.4.0')

    # config 
    chip_names = list(eval(config['Chip']['names'])) + ['other']
    samples = list(eval(config['Chip']['samples']))

    # Chip Parameters
    show_more = BooleanParameter('Show more', default=False)
    chip_group = ListParameter('Chip group name', choices=chip_names)
    chip_number = IntegerParameter('Chip number', default=1, minimum=1)
    sample = ListParameter('Sample', choices=samples)
    info = Parameter('Information', default='None')

    # Metadata
    start_time = Metadata('Start time', fget=time.time)

    INPUTS = ['show_more', 'chip_group', 'chip_number', 'sample', 'info']
    
    def update_parameters(self):
        """Function to update the parameters after the initialization,
        but before startup. It is useful to modify the parameters
        based on the values of other parameters. It is called
        only by the ExperimentWindow.
        """
        pass


class MetaProcedure(BaseProcedure):
    """Manages a multiple procedures to be executed in sequence. It is used to
    run a sequence of procedures, such as a burn-in followed by an IVg and
    It measurements. Performs a unique startup, executes the procedures in
    sequence, and performs a unique shutdown.
    """
    procedures: list[BaseProcedure] = []
