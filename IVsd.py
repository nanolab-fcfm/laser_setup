# Software to measure bipolar transfer curves
from lib.devices import K2450
import time
import numpy as np
import matplotlib.pyplot as plt

# Print possible pyvisa resources
print("The possible Pyvisa resources are:", K2450.rm.list_resources())

# Keithley 2450:
Keithley = K2450('USB0::1510::9296::04448997::0::INSTR')
# Other possible contacts: 'USB0::0x05E6::0x2450::04100331::INSTR'
# 'USB0::0x05E6::0x2614::4363274::0::INSTR'

vSD_start = -1
vSD_end = 1
vSD_step = 0.1
Irange = 1E-3       # Currently it's set to auto
NAVG = 1

Total_number_IVs = 1
Time_pause = 0  # in seconds

plt.figure()

# Configure Keithley for IV-measurement:
Keithley.reset()
Keithley.source_volt()
Keithley.set_volt_range(max(abs(vSD_start), abs(vSD_end)))
Keithley.write(':SOURce:VOLT 0')
Keithley.curr_limit(0.001)
Keithley.sense_curr()
Keithley.write('CURR:AZER OFF')
Keithley.sense_curr_nplc(1)

# Configure current range here (beginning from 10E-9):
# Irange_str = ':SENSe:CURRent:RANGe ' + str(Irange)
# obj1.write(Irange_str)
Keithley.sense_curr_range_auto(True)
time.sleep(0.1)

Keithley.write(':SOURce:VOLT 0')
Keithley.write(':OUTPut ON')

# Hasta acá está listo

for IV_number in range(Total_number_IVs):

    row_counter = 0
    VSD = np.concatenate((np.arange(0, vSD_start-vSD_step/2, -vSD_step),
                          np.arange(vSD_start+vSD_step/2, vSD_end-vSD_step/2, vSD_step),
                          np.arange(vSD_end+vSD_step/2, -vSD_step/2, -vSD_step)))
    
    for vsd in VSD:
        row_counter += 1
        vsd_string = str(vsd)
        vSD_out = ':SOURce:VOLT ' + vsd_string
        obj1.write(vSD_out)
        data = []
        for k in range(NAVG):
            data_string = obj1.query(':READ?')
            data.append(float(data_string))
        data_array[row_counter, 0] = vsd
        data_array[row_counter, IV_number+1] = np.mean(data)

    print('done')
    plt.plot(data_array[round(len(data_array)/4):round(3*len(data_array)/4), 0],
             smooth(1e9*data_array[round(len(data_array)/4):round(3*len(data_array)/4), IV_number+1], 3, 'moving'),
             '.', label=f'IV {IV_number+1}')
    plt.plot(np.concatenate((data_array[0:round(len(data_array)/4), 0], data_array[round(3*len(data_array)/4):, 0])),
             smooth(1e9*np.concatenate((data_array[0:round(len(data_array)/4), IV_number+1], data_array[round(3*len(data_array)/4):, IV_number+1])),
                    3, 'moving'),
             '.', label=f'IV {IV_number+1}')
    plt.xlabel('V_SD (V)')
    plt.ylabel('I_SD (nA)')
    plt.legend()
    plt.show(block=False)

    time.sleep(Time_pause)


