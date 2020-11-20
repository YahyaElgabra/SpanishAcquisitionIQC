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

#Logical

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

def conduction_corner(v_rf_vals, v_dc_vals, V_dc_Instrument, V_rf_Instrument, CurrentReader, gain, turn_on_threshold, pinchoff_threshold):
    """
    Algorithm which determines which v_rf and which v_dc values we should use to attempt pumping.

    Parameters:
    v_rf_vals : Interable of numbers in Volts that we wish v_rf to sweep over. 
                Works best if the length of v_rf_vals and v_dc_vals are the same.
    v_dc_vals : Interable of numbers in Volts that we wish v_dc to sweep over. 
                Works best if the length of v_rf_vals and v_dc_vals are the same.
    V_dc_Setter : Device object that is used to to adjust V_dc. 
                  Must have a setter/getter attribute called 'voltage'
    V_rf_Setter : Device object that is used to to adjust V_rf.
                  Must have a setter/getter attribute called 'voltage'
    CurrentReader: Device object that is used to read current. Must have an attribute called 'reading'. 
                   It is assumed that we will be using a current preamp, which converts from current to voltage
    gain: Gain of current preamp. Used to convert from current through device to voltage.
    turn_on_threshold : Current threshold that we attribute to turn on of the device. Current through device will not exceed this value.
    pinchoff_threshold: Percentage which tells us how close to
                        Low limit of current where we achieve pinch off. We wish to attempt pumping near this value of current.

    Returns:
    corner_point or None: Dictionary with 2 elements (V_rf and V_dc) which are the voltages where the corner of the conduction map is located.
                          If corner was not found, return None. 

    """

    # This for loop steps v_rf and v_dc in tandem until turn on is achieved
    for v_rf_, v_dc_ in zip(v_rf_vals, v_dc_vals):

        # Find index in list of current elements (useful for later)
        v_rf_index = v_rf_vals.index(v_rf_)
        v_dc_index = v_dc_vals.index(v_dc_)

        # Set voltages to current values in loop
        V_rf_Instrument.voltage = v_rf_
        V_dc_Instrument.voltage = v_dc_

        # Measure the voltage from preamp and then convert to current
        current = _get_current(CurrentReader, gain)

        # Once the current threshold for turn on is achieved, lower each DC gate individually until pinch off occurs
        if current.value > turn_on_threshold.value:
            print 'Turn on occurring at V_rf = ' + v_rf_ + ', V_dc = ' + v_dc_

            # Create empty dict which will store the corner point of the conduction map
            corner_point = dict()

            ## Drop the voltage of v_rf until the current is below the pinch off threshold

            # Set a counting variable for the for while loop
            v_rf_decrease_count = 1
            while True:

                # If we have decreased V_rf all the way, break out of for loop
                if v_rf_decrease_count >= v_rf_index:
                    print "V_rf decreased to minimum value but pinch off was not found."
                    break

                # Set V_rf to lower value and measure current through device
                V_rf_Instrument.voltage = v_rf_vals[v_rf_index - v_rf_decrease_count]
                current = _get_current(CurrentReader, gain)

                # If current is below the pinch off threshold, save that value of V_rf and 
                if current.value <= pinchoff_threshold.value:
                    corner_point['v_rf'] = v_rf_vals[v_rf_index - v_rf_decrease_count]
                    break

                # Increase count in for loop, which will drop V_rf to lower values
                v_rf_decrease_count += 1

            ## Drop the voltage of v_dc until the current is below the pinch off threshold

            # Set a counting variable for the for while loop
            v_dc_decrease_count = 1
            while True:

                # If we have decreased V_dc all the way, break out of for loop
                if v_dc_decrease_count >= v_dc_index:
                    print "V_dc decreased to minimum value but pinch off was not found."
                    break

                # Set V_rf to lower value and measure current through device
                V_dc_Instrument.voltage = v_dc_vals[v_dc_index - v_dc_decrease_count]
                current = _get_current(CurrentReader, gain)

                # If current is below the pinch off threshold, save that value of V_dc and 
                if current.value <= pinchoff_threshold.value:
                    corner_point['v_dc'] = v_dc_vals[v_dc_index - v_dc_decrease_count]
                    break

                # Increase count in for loop, which will drop V_dc to lower values
                v_dc_decrease_count += 1

            # Verify that corner point is found
            if len(corner_point) == 2:
                print "Corner point of conduction map was found at" + str(corner_point)
                return corner_point
            break

    else:
        print "Turn on of device was not found."

    return None

def dc_optimization(v_qpc_vals, v_rf_vals, v_dc_vals, V_qpc_Instrument, V_dc_Instrument, V_rf_Instrument, CurrentReader, gain, turn_on_threshold, pinchoff_threshold, offset):
    '''
    Algorithm which determines which v_rf and which v_dc values we should use to attempt pumping.

    Parameters:
    v_qpc_vals : Interable of numbers in Volts that we wish v_qpc to sweep over. 
    v_rf_vals : Interable of numbers in Volts that we wish v_rf to sweep over. 
                Works best if the length of v_rf_vals and v_dc_vals are the same.
    v_dc_vals : Interable of numbers in Volts that we wish v_dc to sweep over. 
                Works best if the length of v_rf_vals and v_dc_vals are the same.
    V_qpc_Instrument : Device object that is used to to adjust V_qpc. 
                       Must have a setter/getter attribute called 'voltage'
    V_dc_Instrument : Device object that is used to to adjust V_dc. 
                      Must have a setter/getter attribute called 'voltage'
    V_rf_Instrument : Device object that is used to to adjust V_rf.
                      Must have a setter/getter attribute called 'voltage'
    CurrentReader: Device object that is used to read current. Must have an attribute called 'reading'. 
                   It is assumed that we will be using a current preamp, which converts from current to voltage
    gain: Gain of current preamp. Used to convert from current through device to voltage.
    turn_on_threshold : Current threshold that we attribute to turn on of the device. Current through device will not exceed this value.
    pinchoff_threshold: Percentage which tells us how close to
                        Low limit of current where we achieve pinch off. We wish to attempt pumping near this value of current.
    offset: Quantity object which dictates how far back in V_rf and V_dc we go from the corner of the condutance map to the 

    Returns:
    pumping_point or None: Dictionary with 3 elements (V_rf, V_dc and v_qpc) which are the voltages where we should start looking for pumping.
                          If corner was not found, return None.
    '''
    # Loop over possible v_qpc values
    for v_qpc_ in v_qpc_vals:

        # Set v_qpc to value
        V_qpc_Instrument.voltage = v_qpc_

        # Use the pumping_corner fucntion to find corner of conduction map 
        temp = conduction_corner(v_rf_vals, v_dc_vals, V_dc_Instrument, V_rf_Instrument, CurrentReader, gain, turn_on_threshold, pinchoff_threshold)

        # If temp is not None, then we have not pushed v_rf and v_dc to the limits, so save those values of v_rf and v_dc to corner point
        if temp is not None:
            corner_point = temp
        # If temp is None, then we have found the point where v_rf and v_dc must be pushed too high to induce turn on.
        # Therefore, this triple of V_rf, V_dc and V_qpc is where we should attempt pumping (with the offset added)
        else:
            # This corner point will be the pumping point, so add the v_qpc value
            pumping_point = corner_point
            pumping_point['v_qpc'] = v_qpc_

            # Apply pumping offset
            pumping_point['v_rf'] -= offset
            pumping_point['v_dc'] -= offset
            return pumping_point

def pumping_single_sweep(v_pp_val, v_ent_vals, V_pp_Instrument, V_ent_Instrument, CurrentReader, gain, max_current):
    
    # Set V_pp
    V_pp_Instrument.TODO = v_pp_val

    # Initialize list that will store currents
    currents = []

    # Get 1D sweep over v_ent_vals
    for v_ent_val_ in v_ent_vals:
        
        # Set value of v_ent and then measure the current and save for later
        V_ent_Instrument.voltage = v_ent_val_
        current = _get_current(CurrentReader, gain)

        # Check that current is not exceeding maximum current and that 
        if current.value <= max_current:
            raise ValueError("Current value exceeding max current allowed. Aborting sweep")

        # Check that current is not negative, which indicates that the channel is fully opened
        if current.value <= 0:
            raise ValueError("Current value less than 0, which indicates that the channel is fully opened. Aborting sweep")

        # If both thosse checks are good, add current to list
        currents.append(current)
    
    # If no issues arise, we can perform analysis on the acquired currents
    
    



def rf_optimization(v_pp_vals, v_ent_vals, v_ext_vals, V_pp_Instrument, V_ent_Instrument, V_ext_Instrument, CurrentReader, gain, frequency, max_plateau_current):
    '''
    Algorithm which determines the V_ent, V_ext and V_pp which generates the best pumping.

    Parameters:
    v_pp_vals : Interable of numbers in Volts that we wish v_pp to sweep over. 
    v_ent_vals : Interable of numbers in Volts that we wish v_ent to sweep over. 
    v_ext_vals : Interable of numbers in Volts that we wish v_ext to sweep over. 
    V_pp_Instrument : Device object that is used to to adjust V_pp. 
                    Must have a setter/getter attribute called 'TODO'
    V_ent_Instrument : Device object that is used to to adjust V_ent. 
                    Must have a setter/getter attribute called 'voltage'
    V_ext_Instrument : Device object that is used to to adjust V_ext.
                    Must have a setter/getter attribute called 'voltage'
    CurrentReader: Device object that is used to read current. Must have an attribute called 'reading'. 
                It is assumed that we will be using a current preamp, which converts from current to voltage
    gain: Gain of current preamp. Used to convert from current through device to voltage.
    frequency : Frequency in Hertz of the signal generated by V_pp_Instument
    max_plateau_current: Maximum current allowed in terms of plateaus. So I_max = max_plateau_current * electron_charge * frequency

    Returns:
    pumping_point or None: Dictionary with 3 elements (v_pp, v_ent and v_ext) where resonable pumping occured.
                        If no pumping is detected, return None.
    '''

    # Calculate the maximum current allowed through the device
    electron_charge = 1.60217662 * 10**-19
    max_current = Quantity(max_plateau_current * electron_charge * frequency, 'A')

    # Loop over possible v_ext_vals
    for v_ext_ in v_ext_vals:

        # Set v_ext to value
        V_ext_Instrument.voltage = v_ext_

        # Now sweep over the various v_pp values
        for v_pp_val_ in v_pp_vals:

            # Now do a single sweep of v_ent, with a fixed v_pp and a fixed v_ext, storing the ouput to a temporary variable
            temp = pumping_single_sweep(v_pp_val_, v_ent_vals, V_pp_Instrument, V_ent_Instrument, CurrentReader, gain, max_current)

            # If temp is not None, then we believe that we have found pumping. Save these values in a dictionary and return it
            if temp is not None:
                pumping_point = dict()
                pumping_point['v_ext'] = v_ext_
                pumping_point['v_pp'] = v_pp_val_
                return pumping_point


def _get_current(CurrentReader, gain): #TODO make sure this works
    '''
    Function which gets current, taking into account gain of the preamp

    Parameters:
    CurrentReader
    '''
    current = CurrentReader.reading
    current = current/gain
    return current

#Implementation of pumping
#TODO Adjust for new code
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
