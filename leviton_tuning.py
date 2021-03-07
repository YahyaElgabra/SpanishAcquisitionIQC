
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

def _AC_drive(fixed_tpg, floating_tpg, bias_offset):
    pass
    

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
            _ramp_to_voltage(Quantity(0, units='V'), V_bias_T, resolution=51, wait_time=0.1)
        # If NameError occured, V_bias_T was never defined, so skip to the next instrument
        except NameError:
            pass

        try:
            _ramp_to_voltage(Quantity(0, units='V'), V_vga, resolution=51, wait_time=0.1)
        # If NameError occured, V_vga was never defined, so skip to the next instrument
        except NameError:
            pass

        try:
            _ramp_to_voltage(Quantity(0, units='V'), V_floating_tpg, resolution=51, wait_time=0.1)
        # If NameError occured, V_tpg was never defined, so skip to the next instrument
        except NameError:
            pass

        try:
            _ramp_to_voltage(Quantity(0, units='V'), V_fixed_tpg, resolution=51, wait_time=0.1)
        # If NameError occured, V_tpg was never defined, so skip to the next instrument
        except NameError:
            pass

    # Put auto-tuning script try-except block to catch any errors and 
    # set all voltages to default values if they occur
    try:
    ## Define variables used in sweep
        gain = 1e9
        turn_on_threshold = Quantity(-0.001 ,units="nA")
        frequency = Quantity(50e6, 'Hz')
        RF_target = Quantity(-(e * frequency.value * 1e9), units='nA')
        RF_turn_on = Quantity(-1.1 * (e * frequency.value * 1e9), units='nA')

        ## Initialize FPGA board
        from spacq.devices.pynq.fpga import fpga
        kwargs = {'request_address':'192.168.2.99'}
        FpgaBoard = fpga(**kwargs)

        ## Configure instruments controlled by FPGA board
        # Configure ADC
        CurrentReader = FpgaBoard.subdevices['ADCport0']

        # Configure Oscillator and VGA
        Oscillator = FpgaBoard.subdevices['OSCport0']
        Oscillator.frequency = frequency
        Oscillator.power = '2'
        Oscillator.power_on = "false"
        V_vga = FpgaBoard.subdevices['DACport0']

        # Configure DAC outputs used for DC output
        V_floating_tpg = FpgaBoard.subdevices['DACport10']
        V_fixed_tpg = FpgaBoard.subdevices['DACport7']
        V_bias_T = FpgaBoard.subdevices['DACport4']

        # For transients that arise during equipement initialization
        print("Let equipement rest for 1 seconds")
        time.sleep(1)

        initial_v_fixed = 0 # in V
        final_v_fixed = -5 # in V
        v_fixed_numbers = np.linspace(initial_v_fixed, final_v_fixed, 51)
        v_fixed_vals = [Quantity(i, units='V') for i in v_fixed_numbers]

        initial_v_floating = 0 # in V
        final_v_floating = 5 # in V
        v_floating_numbers = np.linspace(initial_v_floating, final_v_floating, 51)
        v_floating_vals = [Quantity(i, units='V') for i in v_floating_numbers]

        for i in range(len(v_fixed_vals)):
            print("Setting fixed top gate voltage to " + str(v_fixed_vals[i]))
            V_fixed_tpg.voltage = v_fixed_vals[i]
            print("Setting floating top gate voltage to " + str(v_floating_vals[i]))
            V_floating_tpg.voltage = v_floating_vals[i]
            time.sleep(0.1)

        print("Let equipement rest for 5 seconds")
        time.sleep(5)

        ## Find bias induced turn on
        initial_v_bias = 0 # in V
        final_v_bias = -1.2 # in V
        v_bias_numbers = np.linspace(initial_v_bias, final_v_bias, 201)
        v_bias_vals = [Quantity(i, units='V') for i in v_bias_numbers]

        initial_v_floating = 5 # in V
        final_v_floating = 5 - 1.2 # in V
        v_floating_numbers = np.linspace(initial_v_floating, final_v_floating, 201)
        v_floating_vals = [Quantity(i, units='V') for i in v_floating_numbers]

        prev_value = v_floating_vals[0]
        prev_float_tgp = v_floating_vals[0]
        for i in range(len(v_bias_vals)):
            print("Setting bias voltage to " + str(v_bias_vals[i]))
            V_bias_T.voltage = v_bias_vals[i]
            print("Setting floating top gate voltage to " + str(v_floating_vals[i]))
            V_floating_tpg.voltage = v_floating_vals[i]
            if i > 100:
                time.sleep(3)
            else:
                time.sleep(1)
            current = _get_current(CurrentReader, gain)

            if current.value < turn_on_threshold.value: # negative since current is negative
                print('Channel opening at a bias value of {0} V'.format(V_bias_T.voltage.value))
                V_bias_T.voltage = prev_value
                V_floating_tpg.voltage = prev_float_tgp
                break
            
            try:
                prev_value = v_bias_vals[i-1]
                prev_float_tgp = v_floating_vals[i-1]
            except IndexError:
                pass
        
        else:
            print('End of voltage range reached and turn on did not occur. Ramping down all to 0 V')
            raise Exception

        print("Let equipement rest for 5 seconds")
        time.sleep(5)

        ## Increase RF amplitude until we see pumped current, and adjust from there
        initial_v_vga = 0 # in V
        final_v_vga = 1.4 # in V
        v_vga_numbers = np.linspace(initial_v_vga, final_v_vga, 57)
        v_vga_vals = [Quantity(i, units="V") for i in v_vga_numbers]
        
        osc_off = []
        for i in range(20):
            osc_off.append(_get_current(CurrentReader, gain).value)
            time.sleep(0.1)

        average_off = sum(osc_off)/len(osc_off)

        print("Turning on oscillator")
        Oscillator.frequency = frequency # Turns on oscillator
        time.sleep(1)

        prev_value = v_vga_vals[0]
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

            if diff.value < RF_target.value:
                print("Success! RF pulsed current found")
                V_vga.voltage = prev_value
                break

            prev_value = value
        else:
            print("VGA voltage range reached and no pulsed current was observed")
            raise Exception

        ## Now tune to the 1 charge per cycle regime
        initial_v_vga = prev_value.value # in V
        final_v_vga = prev_value.value - 0.025 # in V
        v_vga_numbers = np.linspace(initial_v_vga, final_v_vga, 26)
        v_vga_vals = [Quantity(i, units="V") for i in v_vga_numbers]
        
        osc_off = []
        for i in range(50):
            osc_off.append(_get_current(CurrentReader, gain).value)
            time.sleep(0.2)

        average_off = sum(osc_off)/len(osc_off)

        print("Turning on oscillator")
        Oscillator.frequency = frequency # Turns on oscillator
        time.sleep(1)

        all_ons = []

        for value in v_vga_vals:
            print("Setting vga voltage to " + str(value))
            V_vga.voltage = value
            time.sleep(1)

            osc_on = []
            for i in range(50):
                osc_on.append(_get_current(CurrentReader, gain).value)
                time.sleep(0.2)

            average_on = sum(osc_on)/len(osc_on)

            all_ons.append(Quantity(average_on, units='A'))

        all_ons_values = [current.value for current in all_ons]
        all_ons_diffs = [current - RF_target.value for current in all_ons_values]
        min_index = all_ons_diffs.index(min(all_ons_diffs))
        best_vga_voltage = v_vga_vals[min_index]

        print("most accurate pumping found with a VGA voltage of " + str(best_vga_voltage))
        print("targeted current was " + str(RF_target) + " and average current at that VGA voltage was " + str(all_ons_values[min_index]) )

        V_vga.voltage = best_vga_voltage
        for i in range(3):
            Oscillator.power_on = 'false'
            time.sleep(15)
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
        print()
        print("Tuning interupted! Setting all voltages to 0")
        _set_all_down()
        raise e
