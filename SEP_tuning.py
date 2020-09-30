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