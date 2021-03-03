'''
File which implement automated tuning of an etched wire
'''

# Import relevant modules
import time
import numpy as np
from scipy.constants import e

from spacq.interface.units import Quantity

def _ramp_to_voltage(value, Instrument, resolution=101, wait_time=None):
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
        if wait_time is not None:
            time.sleep(wait_time)

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

#Implementation of auto-tuning
if __name__ == "__main__":

    ## Define variables used in sweep
    gain = 1e9
    turn_on_threshold = Quantity(-0.5 ,units="nA")
    pinchoff_threshold = Quantity(-0.01 ,units="nA")
    frequency = Quantity(150e6, 'Hz')

    ## Initialize FPGA board
    from spacq.devices.pynq.fpga import fpga
    kwargs2 = {'request_address':'192.168.2.99'}
    FpgaBoard = fpga(**kwargs2)

    ## Configure instruments controlled by FPGA board
    # Configure ADC
    CurrentReader = FpgaBoard.subdevices['ADCport0']

    # Configure Oscillator and VGA
    Oscillator = FpgaBoard.subdevices['OSCport0']
    Oscillator.frequency = frequency
    Oscillator.power_on = "false"
    V_vga = FpgaBoard.subdevices['DACport0']

    # Configure DAC outputs
    V_tpg = FpgaBoard.subdevices['DACport10']
    V_bias_T = FpgaBoard.subdevices['DACport4']

    ## Find zero-bias turn on
    initial_v_tgp = 0 # in V
    final_v_tpg = -5 # in V
    v_tpg_numbers = np.linspace(initial_v_tgp, final_v_tpg, 51)
    v_tpg_vals = [Quantity(i, units='V') for i in v_tpg_numbers]

    for value in v_tpg_vals:
        V_tpg.voltage = value
        time.sleep(1)
        current = _get_current(CurrentReader, gain)

        if current.value < turn_on_threshold.value: # negative since current is negative
            print('Channel opening at a top gate value of {0} V'.format(V_tpg.voltage.value))
            break

    ## Find a region in pinch off where a DC bias opens the channel with a positive bias but not a negative bias
    initial_v_tgp = V_tpg.voltage.value
    final_v_tpg = V_tpg.voltage.value + 0.1
    v_tpg_numbers = np.linspace(initial_v_tgp, final_v_tpg, 51)
    v_tpg_vals = [Quantity(i, units='V') for i in v_tpg_numbers]

    open_v_bias_T = 0.025 # in V
    closed_v_bias_T = 0.02 # in V
    

    for value in v_tpg_vals:
        V_tpg.voltage = value
        time.sleep(1)

        _ramp_to_voltage(Quantity(open_v_bias_T, units='V'), V_bias_T, wait_time=0.1)
        time.sleep(1)
        current_open = _get_current(CurrentReader, gain)

        _ramp_to_voltage(Quantity(closed_v_bias_T, units='V'), V_bias_T, wait_time=0.1)
        time.sleep(1)
        current_closed = _get_current(CurrentReader, gain)

        if current_closed.value > pinchoff_threshold.value and current_open.value < pinchoff_threshold:
            
            _ramp_to_voltage(Quantity(-open_v_bias_T, units='V'), V_bias_T, wait_time=0.1)
            time.sleep(1)
            current_negative = _get_current(CurrentReader, gain)

            if current_negative < pinchoff_threshold: # back to positive current
                break

    ## Increase RF amplitude until we see pumped current, and adjust from there
    initial_v_vga = 0 # in V
    final_v_vga = 1.1 # in V
    v_vga_numbers = np.linspace(initial_v_vga, final_v_vga, 111)
    v_vga_vals = [Quantity(i, units="V") for i in v_vga_numbers]
    
    for value in v_vga_vals:
        V_vga.voltage = value
        time.sleep(1)

        Oscillator.frequency = frequency # Turns on oscillator
        time.sleep(1)
        osc_on = []
        for i in range(30):
            osc_on.append(_get_current(CurrentReader, gain).value)
            time.sleep(0.1)

        average_on = sum(osc_on)/len(osc_on)

        Oscillator.power_on = 'false' # Turns off Oscillator
        time.sleep(1)
        osc_off = []
        for i in range(30):
            osc_off.append(_get_current(CurrentReader, gain).value)
            time.sleep(0.1)

        average_off = sum(osc_off)/len(osc_off)

        diff = Quantity((average_on - average_off), units='nA')

        if diff.value > pinchoff_threshold.value:
            break

    # # Testing that we can talk to instruments using script
    # for value in v_vga_vals:
    #     V_vga.voltage = value
    #     time.sleep(0.1)

    # for i in range(5):
    #     time.sleep(1)
    #     Oscillator.power_on = 'false'
    #     time.sleep(1)
    #     Oscillator.frequency = Quantity(150e6, 'Hz')

    # _ramp_to_voltage(Quantity(0, 'V'), V_vga)
    # time.sleep(1)
    # Oscillator.power_on = 'false'


    



    
