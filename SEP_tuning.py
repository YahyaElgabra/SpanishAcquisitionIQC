# from spacq.interface.units import Quantity
# # initialize voltage source
# from spacq.devices.basel.dacsp927 import dacsp927
# kwargs1 = {'host_address':'192.168.0.5'}
# vsource = dacsp927(**kwargs1)
# port1 = vsource.subdevices['port1']
# # initialize multimeter
# from spacq.devices.agilent.dm34410a import DM34410A
# kwargs2 = {'ip_address':'192.168.0.7'}
# multimeter = DM34410A(**kwargs2)
# import time
# target = Quantity(1, units='V')
# while True:
#     v_set = port1.voltage
#     v_meas = multimeter.reading
#     print(v_meas)
#     next_step = target - v_meas
#     if next_step < Quantity(1.2, 'uV'): #limit of DAC resolution
#         break
#     else:
#         next_voltage = v_set + next_step
#         port1.voltage = next_voltage
#         time.sleep(1)
# time.sleep(5)
# port1.voltage = Quantity(0, units='V')
# time.sleep(0.5)
# v_meas = multimeter.reading

import random
import numpy as np
import pandas as pd
import seaborn as sb
import matplotlib.pyplot as plt
folder = 'SEP_tuning_files/'
filename = '2D_sweep_RF_DC.csv'

num_data_points = 51
num_extra = 30
step = 0.002
v_rf = [round(0 + step*x,3) for x in range(num_data_points + num_extra)]
v_dc = [round(0 + step*x,3) for x in range(num_data_points + num_extra)]

imported_data = pd.read_csv(folder + filename)
imported_data = pd.pivot_table(imported_data, index ="Vdc [V]", columns="Vrf [V]", values="I  [nA]")
imported_data = imported_data.to_numpy()

for i in range(10):
    add_y = random.randint(0,num_extra)
    add_x = random.randint(0,num_extra)
    data = np.zeros(shape=(num_data_points + num_extra,num_data_points + num_extra))
    data[add_x:add_x+num_data_points, add_y:add_y+num_data_points] = imported_data
    data = pd.DataFrame(data=data, columns=v_rf, index=v_dc)

    threshold = 0.5
    for i, j in zip(v_rf, v_dc):
        current = float(data[i][j])
        if current > threshold:
            point = (i, j)
            threshold_2 = 0.1
            count_1 = 1
            new_point = [i, j]
            while True:
                new_index = round(j-count_1*step,3)
                current = float(data[i][new_index])
                if current <= threshold_2:
                    new_point[1] = new_index
                    break
                count_1 += 1
            count_2 = 1
            while True:
                new_index = round(i-count_2*step,3)
                current = float(data[new_index][j])
                if current < threshold_2:
                    new_point[0] = new_index
                    break
                count_2 += 1
            break

    f, ax = plt.subplots(1,1)
    sb.heatmap(data)
    ax.axes.invert_yaxis()

    ax2 = ax.twinx().twiny()
    sb.scatterplot(x=[point[0]], y=[point[1]], ax=ax2)
    sb.scatterplot(x=[new_point[0]], y=[new_point[1]], ax=ax2)
    ax2.set_xlim([v_rf[0], v_rf[-1]])
    ax2.set_ylim([v_dc[0], v_dc[-1]])
    ax2.get_yaxis().set_ticks([])
    ax2.get_xaxis().set_ticks([])
    plt.show()