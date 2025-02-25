import balthazar as blt
import matplotlib.pyplot as plt
import numpy as np

from laser_setup.utils import voltage_sweep_ramp

v_start = blt.params["v_start"]
v_stop = blt.params["v_stop"]
spacing = blt.params["spacing"]


def test_ramp():
    ramp = voltage_sweep_ramp(v_start, v_stop, v_points)
    return ramp

if __name__ == '__main__':
    ramp = test_ramp()
    plt.scatter(np.linspace(v_start, v_stop, len(ramp)), ramp)
    plt.show()
