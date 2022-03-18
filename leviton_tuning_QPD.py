'''
File which performs auto-tuning of a PN-junction to a single electron per cycle RF cycle
'''
## Import relevant modules
# From built-ins
import time

# From external packages
import numpy as np
from scipy.constants import e

# From home-built package 
from spacq.interface.units import Quantity

def _ramp_to_voltage(value, Instrument, resolution=101, wait_time=None):
    '''
    Function which will gently ramp an Instrument to a target voltage, taking into account it's current voltage

    Parameters:
    value: Value in Volts that we wish to ramp the Instrument to
    Instrument: Instrument whose voltage should be set. Must have an attribute called 'voltage'.

    Keyword arguments:
    resolution: Integer number of intermediate points that the slow ramp should take (default 101)
    wait_time: Time in seconds to wait at each ramping point. If None, does not wait (default None)
    '''
    # Find initial voltage and make smooth ramp between initial and final voltages
    initial = Instrument.voltage
    dummy_ramp = np.linspace(initial.value, value.value, resolution)
    dummy_ramp_quantities = [Quantity(i, units="V") for i in dummy_ramp]

    # Ramp from initial to final, waiting if necessary
    print("Beginning ramping from " + str(initial) + " to " + str(value))
    for value in dummy_ramp_quantities:
        Instrument.voltage = value
        if wait_time is not None:
            time.sleep(wait_time)

def _get_current(CurrentReader, gain):
    '''
    Function which gets current, taking into account gain of the current preamp

    Parameters:
    CurrentReader: Device object that is used to read current. Must have an attribute called 'reading'. It 
                   is assumed that we will be using a current preamp, which converts from current to voltage
    gain: Gain of current preamp. Used to convert from current through device to voltage

    Returns:
    current: Current measured by the current reader in Amps
    '''
    # Take reading from instrument, then convert to current while taking into accoun the gain of the current preamp
    current = CurrentReader.reading
    current = Quantity(current.value/gain, units="A")
    return current   

#Implementation of auto-tuning
if __name__ == "__main__":

    def _set_all_down():
        '''
        Function which will set all initialized sources to their default values, skipping any insturments that are missing
        Not defined outside the script since it is dependent on the particular names of the instrument objects.
        '''
        try:
            Oscillator.typeNEnable = "off"
        # If NameError occured, Oscillator was never defined, so skip to the next instrument
        except NameError: 
            pass

        try:
            _ramp_to_voltage(Quantity(0, units='V'), V_pn_bias, resolution=51, wait_time=0.1)
        # If NameError occured, V_pn_bias was never defined, so skip to the next instrument
        except NameError:
            pass

    # Put auto-tuning script try-except block to catch any errors and 
    # set all voltages to default values if they occur
    try:
        ## Define variables used in sweep
        gain = 1e9
        frequency = Quantity(50e6, 'Hz')
        turn_on_threshold = Quantity(-0.0004 ,units="nA") # 1 pA
        RF_target = Quantity(-(e * frequency.value * 1e9), units='nA')
        RF_turn_on = Quantity(-(e * frequency.value * 1e9) - 0.0005, units='nA')

        ## Initialize Equipement
        # Initialize and Configure Multimeter
        from spacq.devices.agilent import dm34401a
        CurrentReader = dm34401a.DM34401A(gpib_pad=21)

        # Initialize and Configure Signal Generator
        from spacq.devices.stanford_research_systems import sg382
        Oscillator = sg382.SG382(gpib_pad=27)
        Oscillator.frequency = frequency
        Oscillator.BNCEnable = "off"
        Oscillator.typeNEnable = "off"

        # Configure DAC outputs used for DC output
        from spacq.devices.stanford_research_systems import sim900
        VoltSources = sim900.sim900(gpib_pad=3)
        V_pn_bias = VoltSources.subdevices['port08']

        # For transients that arise during equipement initialization
        print("Let equipement rest for 1 seconds")
        time.sleep(1)

        ## Find bias induced turn on
        # Configure value for the bias
        initial_v_bias = 0 # in V
        final_v_bias = -1.6 # in V
        v_bias_numbers = np.linspace(initial_v_bias, final_v_bias, 201)
        v_bias_vals = [Quantity(i, units='V') for i in v_bias_numbers]

        # Step both top gates through configured values
        for i in range(len(v_bias_vals)):
            print("Setting bias voltage to " + str(v_bias_vals[i]))
            V_pn_bias.voltage = v_bias_vals[i]

            # When we are getting near the turn on point, sleep for 10 seconds to allow transients to dissipate
            if i > 150:
                time.sleep(5)
            # Otherwise, sweep through the point quickly
            else:
                time.sleep(0.1)

            # Measure current to see if turn on has occured, breaking out of the for loop if it has
            current = _get_current(CurrentReader, gain)
            if current.value < turn_on_threshold.value: # negative since current is negative
                print('Channel opening at a bias value of {0} V'.format(V_pn_bias.voltage.value))
                V_pn_bias.voltage = prev_value
                break
            
            # Set the bias voltage to 2 values previous
            # Going 2 steps back instead of one ensures that we are in the pinch off region when we move on to the next step
            prev_value = v_bias_vals[i-1]
    
        # If not DC turn on was found, sweep all voltages to 0
        else:
            print('End of voltage range reached and turn on did not occur. Ramping down all to 0 V')
            raise Exception

        # To allow transients to dissipate
        print("Let equipement rest for 5 seconds")
        time.sleep(5)

        ## Increase RF amplitude until we see pumped current, and adjust from there
        # Configure value for the VGA voltage
        # This DC source is connected to the VGA, which adjusts the gain of the VGA which in turn
        # affects the amplitude of the RF signal comming out of the box
        initial_v_vga = 0 # in V
        final_v_vga = 1.4 # in V
        v_vga_numbers = np.linspace(initial_v_vga, final_v_vga, 57)
        v_vga_vals = [Quantity(i, units="V") for i in v_vga_numbers]

        # Turns on oscillator and let it sleep
        print("Turning on oscillator")
        Oscillator.frequency = frequency
        time.sleep(1)

        # Go through possible voltages on the VGA
        prev_value = v_vga_vals[0]
        for value in v_vga_vals:
            print("Setting vga voltage to " + str(value))
            V_vga.voltage = value

            # When we are getting nearer the turn on point, sleep for longer times to allow transients to dissipate
            if value.value > 1.1:
                time.sleep(7)
            if value.value > 0.5:
                time.sleep(5)
            else:
                time.sleep(0.3)

            # Measure current to see if turn on has occured, breaking out of the for loop if it has
            current = _get_current(CurrentReader, gain)
            if current.value < RF_target.value:
                print("Success! RF pulsed current found")
                V_vga.voltage = prev_value
                break

            # Set VGA voltage to previous value as a 
            prev_value = value

        else:
            print("VGA voltage range reached and no pulsed current was observed")
            raise Exception

        ## Now tune to the 1 charge per cycle regime
        # Set values of VGA voltage around where they were set at the end of the previous step
        initial_v_vga = prev_value.value # in V
        final_v_vga = prev_value.value + 0.050 # in V
        v_vga_numbers = np.linspace(initial_v_vga, final_v_vga, 51)
        v_vga_vals = [Quantity(i, units="V") for i in v_vga_numbers]

        # Turn on the oscillator
        print("Turning on oscillator")
        Oscillator.frequency = frequency # Turns on oscillator
        time.sleep(1)

        all_ons = []

        # Then, go through each VGA voltage value and record the current at that value
        for value in v_vga_vals:
            print("Turning off oscillator")
            Oscillator.power_on = "false"
            time.sleep(5)
            print("Turning on oscillator")
            Oscillator.frequency = frequency
            print("Setting vga voltage to " + str(value))
            V_vga.voltage = value
            time.sleep(5)

            # Record current with oscillator on
            osc_on = []
            for i in range(40):
                osc_on.append(_get_current(CurrentReader, gain).value)
                time.sleep(0.2)

            # Take the average of the collected data
            average_on = Quantity(sum(osc_on)/len(osc_on) * 1e9, units='nA')

            # If the average pulsed current is greater than the turn on, we have more than 
            # enough RF amplitude to cross the gap, so stop the sweep here and break out of the for loop
            all_ons.append(average_on)
            if average_on.value < RF_turn_on.value:
                break

        # Calculate the difference between target current and measured current for each value of VGA voltage
        # and set the voltage of the VGA to the value that gives us the closest amount
        all_ons_values = [current.value for current in all_ons]
        all_ons_diffs = [abs(current - RF_target.value) for current in all_ons_values]
        min_index = all_ons_diffs.index(min(all_ons_diffs))
        best_vga_voltage = v_vga_vals[min_index]

        print("most accurate pumping found with a VGA voltage of " + str(best_vga_voltage))
        print("targeted current was " + str(RF_target) + " and average current at that VGA voltage was " + str(all_ons_values[min_index]) )

        # Go over a few vlaues near the optimized paramters to show that it is indeed the best value
        V_vga.voltage = best_vga_voltage
        for i in [-0.003, -0.002, -0.001, 0, 0.001, 0.002, 0.003]:
            V_vga.voltage = Quantity(best_vga_voltage.value + i, units='V')
            Oscillator.power_on = 'false'
            time.sleep(10)
            Oscillator.frequency = frequency
            time.sleep(15)

        ## Set all voltages down to their set values
        print("Success! Beginning ramping of all voltages")
        _set_all_down()

    # Catch KeyboardInterrupt, which occurs when a user kills the script prematurely
    except KeyboardInterrupt:
        print()
        print("Tuning interupted by user! Setting all voltages to default values")
        _set_all_down()

    # Catch all other Exceptions, set all voltages to default values and then raise error for traceback
    except Exception as e:
        print("")
        print("Exception encountered during auto-tuning! Setting all voltages to 0")
        _set_all_down()
        raise e
