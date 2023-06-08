import random
import logging
from time import sleep
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter, Experiment, Procedure

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class RandomProcedure(Procedure):

    iterations = IntegerParameter('Loop Iterations')
    delay = FloatParameter('Delay Time', units='s', default=0.2)
    seed = Parameter('Random Seed', default='12345')

    DATA_COLUMNS = ['Iteration', 'Random Number']

    def startup(self):
        log.info("Setting the seed of the random number generator")
        random.seed(self.seed)

    def execute(self):
        log.info(f"Starting the loop of {self.iterations} iterations")
        for i in range(self.iterations):
            data = {
                'Iteration': i,
                'Random Number': random.random()
            }
            self.emit('results', data)
            log.debug(f"Emitting results: {data}")
            self.emit('progress', 100 * i / self.iterations)
            sleep(self.delay)

    def shutdown(self):
        log.info("Finished")


def test_procedure():
    procedure = RandomProcedure(iterations=100, delay=0.01)
    experiment = Experiment('test', procedure)
    experiment.start()
    return procedure


if __name__ == "__main__":
    test_procedure()
