import matplotlib.pyplot as plt
import numpy as np

from laser_setup.utils import voltage_sweep_ramp

def test_ramp():
    ramp = voltage_sweep_ramp(-35, 35, 0.5)
    return ramp

if __name__ == '__main__':
    ramp = test_ramp()
    plt.scatter(np.linspace(-35, 35, len(ramp)), ramp)
    plt.show()
