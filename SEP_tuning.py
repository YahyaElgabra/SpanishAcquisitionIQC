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
num_extra = 35
num_random = 30
qpc_shift = 25
voltage_limit = 0.2

step = 0.002
v_rf = [round(0 + step*x,3) for x in range(num_data_points + num_extra)]
v_dc = [round(0 + step*x,3) for x in range(num_data_points + num_extra)]

imported_data = pd.read_csv(folder + filename)
imported_data = pd.pivot_table(imported_data, index ="Vdc [V]", columns="Vrf [V]", values="I  [nA]")
imported_data = imported_data.to_numpy()

for k in range(1):
    add_y = random.randint(0,num_random)
    add_x = random.randint(0,num_random)
    count_qpc = -1
    qpc_cond = True
    while qpc_cond:
        count_qpc+=1
        data = np.zeros(shape=(num_data_points + num_extra,num_data_points + num_extra))
        data[add_x + count_qpc * qpc_shift:add_x + num_data_points + count_qpc * qpc_shift, add_y + count_qpc * qpc_shift:add_y + num_data_points + count_qpc * qpc_shift] = imported_data
        data = pd.DataFrame(data=data, columns=v_rf, index=v_dc)

        threshold = 0.5
        for v_1, v_2 in zip(v_rf, v_dc):
            current = float(data[v_1][v_2])
            if v_1 > voltage_limit or v_2 > voltage_limit:
                qpc_cond = False
                break
            if current > threshold and qpc_cond is True:
                point = (v_1, v_2)
                threshold_2 = 0.1
                count_1 = 1
                new_point = [v_1, v_2]
                while True:
                    new_index = round(v_2-count_1*step,3)
                    current = float(data[v_1][new_index])
                    if current <= threshold_2:
                        new_point[1] = new_index
                        break
                    count_1 += 1
                count_2 = 1
                while True:
                    new_index = round(v_1-count_2*step,3)
                    current = float(data[new_index][v_2])
                    if current < threshold_2:
                        new_point[0] = new_index
                        break
                    count_2 += 1
                break

        if qpc_cond==True:
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

# Ideal

from spacq.interface.units import Quantity
# initialize virtual voltage source
from spacq.devices.virtual.virtinst import virtinst

def pumping_point(threshold_1, threshold_2):
    """
    threshold_1 : Determines when V_rf and V_dc should stop being increased in tandem. Current through device will not exceed this value.
    threshold_2 : Low limit. We wish to attempt pumping near this value of current.
    """

    # This for loop steps v_rf and v_dc in tandem until turn on is achieved
    for v_rf_, v_dc_ in zip(v_rf_vals, v_dc_vals):

        virtual_inst.set_v_rf(v_rf_)
        virtual_inst.set_v_dc(v_dc_)
        current = virtual_inst.get_current()
        # Once the current threshold for turn on is achieved, lower each individually until turn off occurs
        if current.value > threshold_1.value:
            turn_on_point = (v_rf_, v_dc_)
            print turn_on_point

            count_rf = 1
            pumping_point = [v_rf_, v_dc_]
            # Drop the voltage of v_rf until the current is below the second threshold
            while True:
                virtual_inst.set_v_rf(round(v_rf_ - count_rf * step, 3))
                current = virtual_inst.get_current()
                if current.value <= threshold_2.value:
                    pumping_point[0] = v_rf_ - count_rf * step
                    break
                count_rf += 1

            count_dc = 1
            # Drop the voltage of v_dc until the current is below the second threshold
            while True:
                virtual_inst.set_v_dc(round(v_dc_ - count_dc * step, 3))
                current = virtual_inst.get_current()
                if current.value < threshold_2.value:
                    pumping_point[1] = v_dc_ - count_rf * step
                    break
                count_dc += 1
            print pumping_point
            break

    else:
        print "current not found"

#Implementation of pumping

if __name__ == "__main__":
    # Define 2 thresholds for corner finding
    threshold_1 = Quantity(0.5, units = "nA")
    threshold_2 = Quantity(0.05, units = "nA")

    # Define voltage range we want to step over 
    # (In practice this can be anything, but for current data, this must not be changed)
    step = 0.002
    num_data_points = 51
    v_rf_vals = [round(0.63 + step*x,3) for x in range(num_data_points)]
    v_dc_vals = [round(0.63 + step*x,3) for x in range(num_data_points)]

    # Specify where data is stored
    folder = 'SEP_tuning_files/'
    filename = '2D_sweep_RF_DC.csv'
    kwargs = {'data_file':folder+filename}

    #Initialize virtual instrument
    virtual_inst = virtinst(**kwargs)

    pumping_point(threshold_1, threshold_2)
