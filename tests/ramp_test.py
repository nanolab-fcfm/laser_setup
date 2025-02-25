import balthazar as blt
import matplotlib.pyplot as plt
import numpy as np

from laser_setup.utils import voltage_sweep_ramp

v_start = blt.params["v_start"]
v_stop = blt.params["v_stop"]
spacing = blt.params["spacing"]
msg = input("What's your name? ")


def test_ramp():
    ramp = voltage_sweep_ramp(v_start, v_stop, spacing)
    return ramp

if __name__ == '__main__':
    ramp = test_ramp()
    array = np.linspace(v_start, v_stop, len(ramp))
    plt.scatter(array, ramp)
    plt.show()
    
    fig, ax = plt.subplots()
    ax.scatter(array, array, c='red')
    plt.show()
    with open('file.txt', mode='w') as f:
        f.write(str(msg))
