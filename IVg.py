# Software to measure bipolar transfer curves
from lib.devices import K2450, TENMA
import time
import numpy as np
import matplotlib.pyplot as plt

# Keithley 2450:
Keithley = K2450('USB0::1510::9296::04448997::0::INSTR')
# Other possible contacts: 'USB0::0x05E6::0x2450::04100331::INSTR'
# 'USB0::0x05E6::0x2614::4363274::0::INSTR'

# TENMA 1:      Positive voltage
Tenma1 = 0