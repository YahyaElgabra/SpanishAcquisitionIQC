'''
File which implement automated tuning of an etched wire to the single quantum level 
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
    Instrument: Instrument whose voltage should be set

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
        print("Ramping device through " + str(value))
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
            Oscillator.power_on = 'false'
        # If NameError occured, Oscillator was never defined, so skip to the next instrument
        except NameError: 
            pass

        try:
            _ramp_to_voltage(Quantity(0, units='V'), V_bias_T, wait_time=0.1)
        # If NameError occured, V_bias_T was never defined, so skip to the next instrument
        except NameError:
            pass

        try:
            _ramp_to_voltage(Quantity(0, units='V'), V_vga, wait_time=0.1)
        # If NameError occured, V_vga was never defined, so skip to the next instrument
        except NameError:
            pass

        try:
            _ramp_to_voltage(Quantity(-1, units='V'), V_tpg, resolution=30, wait_time=1)
        # If NameError occured, V_tpg was never defined, so skip to the next instrument
        except NameError:
            pass

    # Put auto-tuning script try-except block to catch any errors and 
    # set all voltages to default values if they occur
    try:
    ## Define variables used in sweep
        gain = 1e8
        turn_on_threshold = Quantity(-0.01 ,units="nA")
        frequency = Quantity(150e6, 'Hz')
        RF_turn_on = Quantity((-e * frequency.value) * 10e9, units='nA')
        print(RF_turn_on)

        ## Initialize FPGA board
        from spacq.devices.pynq.fpga import fpga
        kwargs = {'request_address':'192.168.2.99'}
        FpgaBoard = fpga(**kwargs)

        ## Configure instruments controlled by FPGA board
        # Configure ADC
        CurrentReader = FpgaBoard.subdevices['ADCport0']

        # # Configure Oscillator and VGA
        Oscillator = FpgaBoard.subdevices['OSCport0']
        Oscillator.frequency = frequency
        Oscillator.power_on = "false"
        V_vga = FpgaBoard.subdevices['DACport0']

        # Configure DAC outputs used for DC output
        V_tpg = FpgaBoard.subdevices['DACport10']
        V_bias_T = FpgaBoard.subdevices['DACport4']

        # For transients that arise during equipement initialization
        print("Let equipement rest for 5 seconds")
        time.sleep(5)

        ## Find zero-bias turn on
        initial_v_tgp = -0.1 # in V
        final_v_tpg = -5 # in V
        v_tpg_numbers = np.linspace(initial_v_tgp, final_v_tpg, 50)
        v_tpg_vals = [Quantity(i, units='V') for i in v_tpg_numbers]

        for value in v_tpg_vals:
            print("Setting top gate voltage to " + str(value))
            V_tpg.voltage = value
            time.sleep(3)
            current = _get_current(CurrentReader, gain)

            if current.value < turn_on_threshold.value: # negative since current is negative
                print('Channel opening at a top gate value of {0} V'.format(V_tpg.voltage.value))
                break
        
        else:
            print('End of voltage range reached and turn on did not occur. Ramping top gate to -1 V')
            _set_all_down()

        ## Find a region in pinch off where a DC bias opens the channel with a positive bias
        initial_v_tgp = V_tpg.voltage.value + 0.1
        final_v_tpg = V_tpg.voltage.value
        _ramp_to_voltage(Quantity(initial_v_tgp, units='V'), V_tpg, resolution=11, wait_time=0.1)
        v_tpg_numbers = np.linspace(initial_v_tgp, final_v_tpg, 11)
        v_tpg_vals = [Quantity(i, units='V') for i in v_tpg_numbers]

        open_v_bias_T = 0.025
        print("Setting bias voltage to " + str(open_v_bias_T))
        _ramp_to_voltage(Quantity(open_v_bias_T, units='V'), V_bias_T, resolution=26, wait_time=0.1)
        time.sleep(1)

        prev_value = initial_v_tgp

        for value in v_tpg_vals:
            print("Setting top gate voltage to " + str(value))
            V_tpg.voltage = value
            time.sleep(2)
            current = _get_current(CurrentReader, gain)

            if current.value < turn_on_threshold.value:
                print("Bias assisted turn on found!")
                V_tpg.voltage = prev_value
                break

            prev_value = value

        else:
            print("Out of top gate voltages!")
            _set_all_down()

        ## Increase RF amplitude until we see pumped current, and adjust from there
        initial_v_vga = 0 # in V
        final_v_vga = 1.1 # in V
        v_vga_numbers = np.linspace(initial_v_vga, final_v_vga, 23)
        v_vga_vals = [Quantity(i, units="V") for i in v_vga_numbers]
        
        osc_off = []
        for i in range(20):
            osc_off.append(_get_current(CurrentReader, gain).value)
            time.sleep(0.1)

        average_off = sum(osc_off)/len(osc_off)

        print("Turning on oscillator")
        Oscillator.frequency = frequency # Turns on oscillator
        time.sleep(1)

        for value in v_vga_vals:
            print("Setting vga voltage to " + str(value))
            V_vga.voltage = value
            time.sleep(1)

            osc_on = []
            for i in range(20):
                osc_on.append(_get_current(CurrentReader, gain).value)
                time.sleep(0.1)

            average_on = sum(osc_on)/len(osc_on)

            diff = Quantity((average_on - average_off), units='A')

            if diff.value < turn_on_threshold.value:
                print("Success! Setting all voltages to zero")
                break
        else:
            _set_all_down()

        ## Now tune to the 1 charge per cycle regime

        ## Set all voltages down to their set values
        _set_all_down()

    # Catch KeyboardInterrupt, which occurs when a user kills the script prematurely
    except KeyboardInterrupt:
        print()
        print("Tuning interupted by user! Setting all voltages to default values")
        _set_all_down()

    # Catch all other Exceptions, set all voltages to default values and then raise error for traceback
    except Exception as e:
        print()
        print("Tuning interupted! Setting all voltages to 0")
        _set_all_down()
        raise e
