'''
File which digital controls of the Pynq FPGA board
'''

## Import relevant modules
# From built-ins
import time
from __future__ import division
import logging
log = logging.getLogger(__name__)

# From home-built package 
from spacq.interface.resources import Resource
from spacq.interface.units import Quantity
from spacq.tool.box import Synchronized
from ..abstract_device import AbstractDevice, AbstractSubdevice
from ..tools import quantity_unwrapped, quantity_wrapped, BinaryEncoder

"""
Pynq FPGA board for the IDEaS project with periphery components
"""

class DACPort(AbstractSubdevice):
	"""
	An output port on the DAC voltage source connected to the FPGA.
	"""
	def _setup(self):
		AbstractSubdevice._setup(self)

		## Resources
		# Defines all resources that are read/write
		read_write = ['voltage']
		for name in read_write:
			self.resources[name] = Resource(self, name, name)

		# Set units on relevant resources
		self.resources['voltage'].units = 'V'

	# Configuration of devices upon initialization
	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)
		# Turn on port and sets the span to +/- 10 V
		r = self.device.ask_raw(':5000/dac1?channel={0}&span=pm10V'.format(self.num))
		# Verify that the command was successfully executed
		if r.status_code != 200:
			raise Exception("Something went wrong while setting the span!")
		
		# Sets voltage output to 0 V (changing the span changes the output voltage, so this step is necessary)
		r = self.device.ask_raw(':5000/dac1?channel={0}&value=0'.format(self.num))
		# Verify that the command was successfully executed
		if r.status_code != 200:
			raise Exception("Something went wrong while setting the voltage!")

		# Define current state of the DAC port
		self.currentVoltage = 0
		self.span_limits = [-10, 10]

	def __init__(self, device, num, *args, **kwargs):
		"""
		Initialize the output port.
		device: The voltage source to which this Port belongs.
		num: The index of this port.
		"""
		# Calls __init__ from the AbstractSubdevice class it inherets from
		AbstractSubdevice.__init__(self, device, *args, **kwargs)
		self.num = num

	# Set property to read and write voltages
	@property
	@quantity_wrapped('V')
	def voltage(self):
		return self.currentVoltage
		
	@voltage.setter
	@quantity_unwrapped('V')
	def voltage(self, value):
		"""
		Set the voltage on this port, as a quantity in V.
		"""
		# Verify that the voltage to be set is within span
		if value < self.span_limits[0] or value > self.span_limits[1]:
			raise ValueError("Voltage {0} is out of the allowed span {1}".format(value, self.span_limits))

		# Verify that the command was successfully executed
		r = self.device.ask_raw(':5000/dac1?channel={0}&value={1}'.format(self.num, value))
		if r.status_code != 200:
			raise Exception("Voltage not properly set!")

		# Set internal voltage value to value that was just set
		self.currentVoltage = value
		
class ADCPort(AbstractSubdevice):
	'''
	An input port on the ADC for reading voltages connected to the FPGA.
	'''

	def _setup(self):
		AbstractSubdevice._setup(self)

		## Resources
		# Defines all resources that are read only
		read_only = ['reading', 'filter']
		for name in read_only:
			self.resources[name] = Resource(self, name)

		# Set units on relevant resources
		self.resources['reading'].units = 'V'

	# Configuration of devices upon initialization
	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)
		# Turn on the ADC port, hardcoding the reference voltage and setting the internal filter
		r = self.device.ask_raw(':5000/adc2?channel={0}&on=true&inputpair=vin{1}vincom&filter=default'.format(self.num, self.num))

		# Verify that the command was successfully executed
		if r.status_code != 200:
			raise Exception("Something went wrong while initializing the ADC!")

		# Specify current filter on ADC
		self.currentFilter = 'default'

	def __init__(self, device, num, *args, **kwargs):
		"""
		Initialize the output port.
		device: The voltage source to which this Port belongs.
		num: The index of this port.
		"""
		# Calls __init__ from the AbstractSubdevice class it inherets from
		AbstractSubdevice.__init__(self, device, *args, **kwargs)
		self.num = num

	@Synchronized()
	def reset(self):
		"""
		Reset the ADC to its default state.
		"""
		r = self.device.ask_raw(':5000/adc2?reset=true')
		if r.status_code != 200:
			raise Exception("Reset did not properly occur")

	@property
	@quantity_wrapped('V')
	@Synchronized()
	def reading(self):
		"""
		The value measured by the device, as a quantity in V.
		"""
		# The ADC can only read from one port at a time (in a hardware sense) so some 
		# logic has to be performed to read the voltage of the intended port

		# Keep repeating until the correct output port is read
		# It will cycle through all ports so eventually the voltage from the appropriate port will be read
		while True:

			r = self.device.ask_raw(':5000/adc2')
			if r.status_code != 200:
				Warning("Voltage not properly read!") 

			else:
				try:
					# Try to evaluate the string returned by the GET request
					temp = eval(r.text)
					# Check to see if we are reading from the right ADC port and
					# save the result if we are.
					if temp['channel'] == 'CH{0}'.format(self.num):
						result = temp['voltage']
						break
				except SyntaxError: # Caused by an errant GET request and can be ignored safely
					pass

		return result

	# Set property to read and write the current filter setting on the ADC
	@property
	def filter(self):
		return self.currentFilter
	
	@filter.setter
	def filter(self, value):
		# Specify possible filter values, and check that a possible filter setting is the one that is being set 
		possible_filters = ['default', 'sin3', 'sin5']
		if value not in possible_filters:
			raise ValueError('Filter {0} not part of the allowed powers: {1}'.format(value, possible_filters))

		# Verify that the command was successfully executed
		r = self.device.ask_raw(':5000/adc2?filter={0}'.format(value))
		if r.status_code != 200:
			Exception("Filter not properly set!") 

		self.currentFilter = value

class OSCPort(AbstractSubdevice):
	'''
	An output port of the oscillator connected to the FPGA
	'''
	def _setup(self):
		AbstractSubdevice._setup(self)

		## Resources
		# Defines all resources that are read/write
		read_write = ['frequency', 'power', 'power_on']
		for name in read_write:
			self.resources[name] = Resource(self, name, name)

		# Set units on relevant resources
		self.resources['frequency'].units = 'Hz'
	
	# Configuration of devices upon initialization
	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)
		# Turn on oscillator and configure frequency but make sure the power is off on initialization
		r = self.device.ask_raw(':5000/osc1?channel={0}&on=true&freq=500e6&power=0&freq_resolution=100e3&power_down=true'.format(self.num))

		# Verify that the command was successfully executed
		if r.status_code != 200:
			Exception("Device not connected!")

		# Define current state of the oscillator
		self.currentFrequency = 500e6
		self.freq_resolution = 100e3
		self.currentPower = 0
		self.currentPower_on = 'false'

	def __init__(self, device, num, *args, **kwargs):
		"""
		Initialize the output port.
		device: The voltage source to which this Port belongs.
		num: The index of this port.
		"""
		# Calls __init__ from the AbstractSubdevice class it inherets from
		AbstractSubdevice.__init__(self, device, *args, **kwargs)
		self.num = num

	# Set property to read and write (i.e. set) the frequency of the oscillator
	@property
	@quantity_wrapped('Hz')
	def frequency(self):
		"""
		The output frequency of the signal generator
		"""
		return self.currentFrequency

	@frequency.setter
	@quantity_unwrapped('Hz')
	def frequency(self, value):
		# Check to see if the frequency is within the possible range for the hardware
		minFreq = 5e7 # Hz (Minimum hardware limit)
		maxFreq = 5e9 # Hz (Maximum hardware limit)
		if value < minFreq or value > maxFreq:
			raise ValueError('Value {0} not within the allowed bounds: {1} to {2}'.format(value, minFreq, maxFreq))

		# Set value of frequency
		r = self.device.ask_raw(':5000/osc1?&freq={0}'.format(value))

		# Verify that the command was successfully executed
		if r.status_code != 200:
			Exception("Frequency not properly set!") 

		self.currentFrequency = value

	# Set property to read and write the current power of oscillator
	@property
	def power(self):
		# The power output by the oscillator
		return self.currentPower
		
	@power.setter
	def power(self, value):
		# The oscillator has only 4 values of power it can set (0, 1, 2 and 3 which correspond to -5, -2, 1 or 4 dBm, respectively).
		# The output of the oscillator is therefore used as the input into a VGA which has much more fine-grained control of it's gain,
		# allowing us higher resolution during usage

		# Specify possible values for power, and check that a possible setting is the one that is being set 
		possible_powers = ['0','1','2','3'] # corresponds to -5, -2, 1 or 4 dBm, respectively 
		if value not in possible_powers:
			raise ValueError('Value {0} not part of the allowed powers: {1}'.format(value, possible_powers))
		
		# Set power of oscillator
		r = self.device.ask_raw(':5000/osc1?power={0}'.format(value))

		# Verify that the command was successfully executed
		if r.status_code != 200:
			Exception("Voltage not properly set!") 

		self.currentPower = value

	# Set property to read and write whether the power of the oscillator is enabled
	@property
	def power_on(self):
		return self.currentPower_on

	@power_on.setter
	def power_on(self, value):
		# The oscillator has a setting which controls whether any power is being output by the device,
		# which is independent of all the other settings. Those other setting do dictacte however what the power 
		# and frequency of that the device will output if we do turn on the power

		# Swap to match hardware code
		possible_values = {'true':'false','false':'true'}
		# Make robust to capitalization
		value = value.lower()

		# Specify possible values for power_on, and check that a possible setting is the one that is being set 
		if value not in possible_values:
			raise ValueError('Value {0} not part of the allowed values: {1}'.format(value, possible_values.values()))

		# Set power_down attribute of oscillator
		r = self.device.ask_raw(':5000/osc1?power_down={0}'.format(possible_values[value]))

		# Verify that the command was successfully executed
		if r.status_code != 200:
			Exception("Voltage not properly set!")

		self.currentPower_on = value 

class fpga(AbstractDevice):
	"""
	Interface for the Pynq FPGA board
	"""
	# Setup run on device initialization
	def _setup(self):
		AbstractDevice._setup(self)

		## Set all 16 DAC outputs as subdevices of ths device and initialize them
		self.DACports = []
		# For each DAC output (naming convention goes from 0 to 15)
		for num1 in range(16):
			# Initialize the DAC output and properly specify it as a subdevice of the Pynq FPGA board
			port = DACPort(self, num1, **self.port_settings)
			self.DACports.append(port)
			self.subdevices['DACport{0}'.format(num1)] = port

		## Initialize ADC ports
		self.ADCports = []
		# For each ADC port (naming convention goes from 0 to 7, but we are only using ports 0, 1 and 2)
		for num2 in range(2):
			# Initialize the ADC port and properly specify it as a subdevice of the Pynq FPGA board
			port = ADCPort(self, num2, **self.port_settings)
			self.ADCports.append(port)
			self.subdevices['ADCport{0}'.format(num2)] = port

		# Initialize the only oscillator
		port = OSCPort(self, 0, **self.port_settings)
		self.OSCports = [port]
		self.subdevices['OSCport0'] = port

	def __init__(self, port_settings=None, *args, **kwargs):
		"""
		Initialize the voltage source and all its ports.
		port_settings: A dictionary of values to give to each port upon creation.
		"""

		# Handles optional port settings 
		if port_settings is None:
			self.port_settings = {}
		else:
			self.port_settings = port_settings

		# Calls __init__ from the AbstractDevice class it inherets from
		AbstractDevice.__init__(self, *args, **kwargs)

	@Synchronized()
	def _connected(self):
		AbstractDevice._connected(self)

name = 'Pynq FPGA board'
implementation = fpga
