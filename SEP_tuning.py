''' File which contains functions to implement automated tuning of single electron pumps
'''

# Import relevant modules
import time
import numpy as np
from scipy.constants import e

from spacq.interface.units import Quantity

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
    # Safely move voltages to beginning of sweep value
    ramp_to_voltage(v_rf_vals[0], V_rf_Instrument)
    ramp_to_voltage(v_dc_vals[0], V_dc_Instrument)

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
            print 'Turn on occurring at V_rf = ' + str(v_rf_) + ', V_dc = ' + str(v_dc_)

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
    # Safely move voltages to beginning of sweep value
    ramp_to_voltage(v_qpc_vals[0], V_qpc_Instrument)

    corner_point = None
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

    # If we have gone through all V_qpc values and the device still turned on, then take the lowest value of V_qpc that we can pass
    else:
        # This corner point will be the pumping point, so add the v_qpc value
        pumping_point = corner_point
        pumping_point['v_qpc'] = v_qpc_vals[-1]

        # Apply pumping offset
        pumping_point['v_rf'] -= offset
        pumping_point['v_dc'] -= offset
        return pumping_point

def _get_current(CurrentReader, gain):
    '''
    Function which gets current, taking into account gain of the preamp

    Parameters:
    CurrentReader: Device object that is used to read current. Must have an attribute called 'reading'. 
                   It is assumed that we will be using a current preamp, which converts from current to voltage
    gain: Gain of current preamp. Used to convert from current through device to voltage.

    Returns:
    current: Current measured by the current reader in Amps
    '''
    current = CurrentReader.reading
    current = Quantity(current.value/gain, units="A")
    return current

def ramp_to_voltage(value, Instrument, resolution=51):
    '''
    Function which will gently ramp an Instrument to a target voltage, taking into account it's current voltage.

    Parameters:
    value: Value in Volts that we wish to ramp the Instrument to
    Instrument: Instrument whose voltage should be set

    Keyword arguments:
    resolution: Integer number of intermediate points that the slow ramp should take (default 51)
    '''
    initial = Instrument.voltage
    dummy_ramp = np.linspace(initial.value, value.value, resolution)
    dummy_ramp_quantities = [Quantity(i, units="V") for i in dummy_ramp]
    for value in dummy_ramp_quantities:
        Instrument.voltage = value

def fixed_vpp_sweep(v_rf_vals, v_dc_vals, V_dc_Instrument, V_rf_Instrument, CurrentReader, gain, frequency):
    '''
    Algorithm which sweeps over v_rf and v_dc values for a fixed v_pp value which looks for pumped current.

    Parameters: 
    v_rf_vals : Interable of numbers in Volts that we wish v_rf to sweep over. 
                Works best if the length of v_rf_vals and v_dc_vals are the same.
    v_dc_vals : Interable of numbers in Volts that we wish v_dc to sweep over. 
                Works best if the length of v_rf_vals and v_dc_vals are the same.
    V_dc_Instrument : Device object that is used to to adjust V_dc. 
                      Must have a setter/getter attribute called 'voltage'
    V_rf_Instrument : Device object that is used to to adjust V_rf.
                      Must have a setter/getter attribute called 'voltage'
    CurrentReader: Device object that is used to read current. Must have an attribute called 'reading'. 
                   It is assumed that we will be using a current preamp, which converts from current to voltage
    gain: Gain of current preamp. Used to convert from current through device to voltage.
    frequency: Frequency of RF component on V_rf in Hz.

    Returns:
    pumping_point or None: Dictionary with 2 elements (V_rf, V_dc) if pumping is found.
                          If pumping did not occur, return None.
    '''
    # Safely move voltages to beginning of sweep value
    ramp_to_voltage(v_rf_vals[0], V_rf_Instrument)
    ramp_to_voltage(v_dc_vals[0], V_dc_Instrument)

    # Current from 2 electron per cycle is set as condition for pumping
    I_1 = 2 * e * frequency

    # Sweep over V_dc (V_ent) in outer loop
    for v_dc_val_ in v_dc_vals:

        # Set voltage on DC gate
        V_dc_Instrument.voltage = v_dc_val_
        
        # Ramp to initial voltage (since V_rf could be at maximum value from previous V_dc value)
        ramp_to_voltage(v_rf_vals[0], V_rf_Instrument)
        
        # Sweep over V_rf in inner loop
        for v_rf_val_ in v_rf_vals:

            # Set voltage on RF gate
            V_rf_Instrument.voltage = v_rf_val_

            # Measure the current
            current = _get_current(CurrentReader, gain)

            # If current is negative, that means the channel is opening, so abort this V_rf sweep, set the next V_dc and start over
            if current.value < -0.2e-9:
                print("Channel opening, skipping to next V_dc value")
                break

            # If the current is positive and exceed the threshold, then we may have achieved single electron pumping
            if current.value > I_1:

                # Make sure that the reading we get isn't noise and that it is consistent over many measurements
                time.sleep(0.1)
                current_1 = _get_current(CurrentReader, gain)
                time.sleep(0.1)
                current_2 = _get_current(CurrentReader, gain)
                time.sleep(0.1)
                current_3 = _get_current(CurrentReader, gain)

                # If current is consistent, we have achieved pumped current
                if current_1.value > I_1 and current_2.value > I_1 and current_3.value > I_1:
                    print("Pumped current occuring at V_rf = " + str(v_rf_val_) + ", V_dc = " + str(v_dc_val_))
                    return {"V_rf":v_rf_val_, "V_dc":v_dc_val_}

    else:
        print ("No pumping observed")
        return


#Implementation of auto-tuning
if __name__ == "__main__":

    # Initialize multimeter
    from spacq.devices.agilent.dm34410a import DM34410A
    kwargs2 = {'ip_address':'192.168.0.7'}
    multimeter = DM34410A(**kwargs2)

    # Initialalize voltage source
    from spacq.devices.basel.dacsp927 import dacsp927
    kwargs1 = {'host_address':'192.168.0.5'}
    vsource = dacsp927(**kwargs1)

    # Set up Instruments
    V_rf_Instrument = vsource.subdevices['port1']
    V_dc_Instrument = vsource.subdevices['port2']
    V_qpc_Instrument = vsource.subdevices['port3']
    CurrentReader = multimeter

    ## Define variables used in sweep
    gain = 1e8
    turn_on_threshold = Quantity(3 ,units="nA")
    pinchoff_threshold = Quantity(0.01 ,units="nA")
    offset = Quantity(50, units="mV")
    
    # Make a list of just values first, and then make them quantities
    initial_v = 0 # in V
    final_v = 1.7 # in V
    v_rf_numbers = np.linspace(initial_v, final_v, 301)
    v_rf_vals = [Quantity(i, units="V") for i in v_rf_numbers]

    v_dc_numbers = np.linspace(initial_v, final_v, 301)
    v_dc_vals = [Quantity(i, units="V") for i in v_dc_numbers]

    V_qpc_start = 0.55 # in V
    V_qpc_end = 0.4 # in V
    v_qpc_numbers = np.linspace(V_qpc_start, V_qpc_end, 51) 
    v_qpc_vals = [Quantity(i, units="V") for i in v_qpc_numbers]

    # Call function which implements optimization of DC values for gates
    pumping_point = dc_optimization(v_qpc_vals, v_rf_vals, v_dc_vals, V_qpc_Instrument, V_dc_Instrument, V_rf_Instrument, CurrentReader, gain, turn_on_threshold, pinchoff_threshold, offset)

    ## To observe pumped current

    # Define values for V_rf in pumping map
    initial_v_rf = 1.352 # in V
    final_v_rf = 1.552 # in V
    v_rf_numbers = np.linspace(initial_v_rf, final_v_rf, 101)
    v_rf_vals = [Quantity(i, units="V") for i in v_rf_numbers]

    # Define values for V_dc in pumping map
    initial_v_dc = 1.394 # in V
    final_v_dc = 1.594 # in V
    v_dc_numbers = np.linspace(initial_v_dc, final_v_dc, 101)
    v_dc_vals = [Quantity(i, units="V") for i in v_dc_numbers]

    # Define freqency
    frequency = 200e6

    values = fixed_vpp_sweep(v_rf_vals, v_dc_vals, V_dc_Instrument, V_rf_Instrument, CurrentReader, gain, frequency)
