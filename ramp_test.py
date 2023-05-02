import matplotlib.pyplot as plt
import numpy as np

from lib.devices import vg_ramp

ramp = vg_ramp(-35, 35, 0.5)

plt.scatter(np.linspace(-35, 35, len(ramp)), ramp)
plt.show()
