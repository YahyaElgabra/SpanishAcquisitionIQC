'''
Older versions of scripts related to auto-tuning that may be useful for later, but should not be in the main auto-tuning script
'''

from spacq.interface.units import Quantity
# initialize voltage source
from spacq.devices.basel.dacsp927 import dacsp927
kwargs1 = {'host_address':'192.168.0.5'}
vsource = dacsp927(**kwargs1)
port1 = vsource.subdevices['port1']
# initialize multimeter
from spacq.devices.agilent.dm34410a import DM34410A
kwargs2 = {'ip_address':'192.168.0.7'}
multimeter = DM34410A(**kwargs2)
import time
target = Quantity(1, units='V')
while True:
    v_set = port1.voltage
    v_meas = multimeter.reading
    print(v_meas)
    next_step = target - v_meas
    if next_step < Quantity(1.2, 'uV'): #limit of DAC resolution
        break
    else:
        next_voltage = v_set + next_step
        port1.voltage = next_voltage
        time.sleep(1)
time.sleep(5)
port1.voltage = Quantity(0, units='V')
time.sleep(0.5)
v_meas = multimeter.reading

#Logical

# import random
# import numpy as np
# import pandas as pd
# import seaborn as sb
# import matplotlib.pyplot as plt
# folder = 'SEP_tuning_files/'
# filename = '2D_sweep_RF_DC.csv'

# num_data_points = 51
# num_extra = 35
# num_random = 30
# qpc_shift = 25
# voltage_limit = 0.2

# step = 0.002
# v_rf = [round(0 + step*x,3) for x in range(num_data_points + num_extra)]
# v_dc = [round(0 + step*x,3) for x in range(num_data_points + num_extra)]

# imported_data = pd.read_csv(folder + filename)
# imported_data = pd.pivot_table(imported_data, index ="Vdc [V]", columns="Vrf [V]", values="I  [nA]")
# imported_data = imported_data.to_numpy()

# for k in range(1):
#     add_y = random.randint(0,num_random)
#     add_x = random.randint(0,num_random)
#     count_qpc = -1
#     qpc_cond = True
#     while qpc_cond:
#         count_qpc+=1
#         data = np.zeros(shape=(num_data_points + num_extra,num_data_points + num_extra))
#         data[add_x + count_qpc * qpc_shift:add_x + num_data_points + count_qpc * qpc_shift, add_y + count_qpc * qpc_shift:add_y + num_data_points + count_qpc * qpc_shift] = imported_data
#         data = pd.DataFrame(data=data, columns=v_rf, index=v_dc)

#         threshold = 0.5
#         for v_1, v_2 in zip(v_rf, v_dc):
#             current = float(data[v_1][v_2])
#             if v_1 > voltage_limit or v_2 > voltage_limit:
#                 qpc_cond = False
#                 break
#             if current > threshold and qpc_cond is True:
#                 point = (v_1, v_2)
#                 threshold_2 = 0.1
#                 count_1 = 1
#                 new_point = [v_1, v_2]
#                 while True:
#                     new_index = round(v_2-count_1*step,3)
#                     current = float(data[v_1][new_index])
#                     if current <= threshold_2:
#                         new_point[1] = new_index
#                         break
#                     count_1 += 1
#                 count_2 = 1
#                 while True:
#                     new_index = round(v_1-count_2*step,3)
#                     current = float(data[new_index][v_2])
#                     if current < threshold_2:
#                         new_point[0] = new_index
#                         break
#                     count_2 += 1
#                 break

#         if qpc_cond==True:
#             f, ax = plt.subplots(1,1)
#             sb.heatmap(data)
#             ax.axes.invert_yaxis()

#             ax2 = ax.twinx().twiny()
#             sb.scatterplot(x=[point[0]], y=[point[1]], ax=ax2)
#             sb.scatterplot(x=[new_point[0]], y=[new_point[1]], ax=ax2)
#             ax2.set_xlim([v_rf[0], v_rf[-1]])
#             ax2.set_ylim([v_dc[0], v_dc[-1]])
#             ax2.get_yaxis().set_ticks([])
#             ax2.get_xaxis().set_ticks([])
#             plt.show()