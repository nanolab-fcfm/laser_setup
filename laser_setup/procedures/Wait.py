import time
import logging

from pymeasure.experiment import FloatParameter

from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)


class Wait(BaseProcedure):
    """Literally just waits for a specified amount of time."""
    wait_time = FloatParameter('Wait time', units='s', default=1.)
    INPUTS = ['wait_time']

    def execute(self):
        log.info(f"Waiting for {self.wait_time} seconds.")
        t0 = time.time()
        tc = t0
        while tc - t0 < self.wait_time:
            self.emit('progress', (tc - t0)/self.wait_time*100)
            tc = time.time()
