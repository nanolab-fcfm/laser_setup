import logging
import time

from pymeasure.experiment import FloatParameter

from .BaseProcedure import BaseProcedure

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class FakeProcedure(BaseProcedure):
    """A fake procedure for testing purposes."""
    name = 'Fake Procedure'
    fake_parameter = FloatParameter('Fake parameter', units='V', default=1., group_by='show_more')
    total_time = FloatParameter('Total time', units='s', default=10.)
    INPUTS = BaseProcedure.INPUTS + ['total_time', 'fake_parameter']
    DATA_COLUMNS = ['t (s)', 'fake_data']
    DATA = [[0], [0]]

    def startup(self):
        log.info("Starting fake procedure.")

    def execute(self):
        log.info("Executing fake procedure.")
        t0 = time.time()
        tc = t0
        while tc - t0 < self.total_time:
            if self.should_stop():
                log.warning('Measurement aborted')
                break

            self.emit('progress', (tc - t0)/self.total_time*100)
            data = self.fake_parameter + hash(tc-t0) % 1000 / 1000
            self.DATA[0].append(tc - t0)
            self.DATA[1].append(data)
            self.emit('results', dict(zip(self.DATA_COLUMNS, [tc - t0, data])))
            time.sleep(0.2)
            tc = time.time()

    def shutdown(self):
        log.info("Shutting down fake procedure.")

    def get_estimates(self):
        estimates = [
            ('Fake Estimate', f"{self.fake_parameter + hash(time.time()) % 1000 / 1000:.2f}"),
            ('Data average', f"{sum(self.DATA[1])/len(self.DATA[1]):.2f}")
        ]
        return estimates
