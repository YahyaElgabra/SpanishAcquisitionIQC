from __future__ import division

import logging
log = logging.getLogger(__name__)

import numpy
import time

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

		# Resources.
		read_write = ['voltage']
		for name in read_write:
			self.resources[name] = Resource(self, name, name)

		self.resources['voltage'].units = 'V'

	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)
		# Turn on port
		r = self.device.ask_raw(':5000/dac1?channel={0}&value=0&span=pm10V'.format(self.num))
		if r.status_code != 200:
			Warning("Device not connected!")

		self.currentVoltage = 0
		self.span_limits = [-10, 10]

	def __init__(self, device, num, *args, **kwargs):
		"""
		Initialize the output port.
		device: The voltage source to which this Port belongs.
		num: The index of this port.
		"""
		AbstractSubdevice.__init__(self, device, *args, **kwargs)
		self.num = num
		
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
		resulting_voltage = value
		if value < self.span_limits[0] or value > self.span_limits[1]:
			raise ValueError("Voltage {0} is out of the allowed span {1}".format(value, self.span_limits))
		r = self.device.ask_raw(':5000/dac1?channel={0}&value={1}'.format(self.num, resulting_voltage))
		if r.status_code != 200:
			raise Exception("Voltage not properly set!")

		self.currentVoltage = value
		
class ADCPort(AbstractSubdevice):
	'''
	An input port on the ADC for reading voltages connected to the FPGA.
	'''

	def _setup(self):
		AbstractSubdevice._setup(self)

		# Resources.
		read_only = ['reading', 'filter']
		for name in read_only:
			self.resources[name] = Resource(self, name)

		self.resources['reading'].units = 'V'

	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)
		# Turn on port
		r = self.device.ask_raw(':5000/adc2?channel={0}&on=true&inputpair=vin{1}vincom&filter=default'.format(self.num, self.num))
		if r.status_code != 200:
			Warning("Device not connected!")
		self.currentFilter = 'default'

	def __init__(self, device, num, *args, **kwargs):
		"""
		Initialize the output port.
		device: The voltage source to which this Port belongs.
		num: The index of this port.
		"""
		AbstractSubdevice.__init__(self, device, *args, **kwargs)
		self.num = num

	@Synchronized()
	def reset(self):
		"""
		Reset the device to its default state.
		"""
		r = self.device.ask_raw(':5000/adc2?reset=true')
		if r.status_code != 200:
			Warning("Reset did not properly occur")

	@property
	@quantity_wrapped('V')
	@Synchronized()
	def reading(self):
		"""
		The value measured by the device, as a quantity in V.
		"""

		while True:
			r = self.device.ask_raw(':5000/adc2')
			if r.status_code != 200:
				Warning("Voltage not properly read!") 

			else:
				try:
					temp = eval(r.text)
					if temp['channel'] == 'CH{0}'.format(self.num):
						result = temp['voltage']
						break
				except SyntaxError: # Caused by an errant GET request and can be ignored safely
					pass

		return result

	@property
	def filter(self):
		return self.currentFilter
	
	@filter.setter
	def filter(self, value):
		possible_filters = ['default', 'sin3', 'sin5']

		if value not in possible_filters:
			raise ValueError('Filter {0} not part of the allowed powers: {1}'.format(value, possible_filters))

		r = self.device.ask_raw(':5000/adc2?filter={0}'.format(value))
		if r.status_code != 200:
			Warning("Filter not properly set!") 

		self.currentFilter = value

class OSCPort(AbstractSubdevice):
	'''
	An output port of the oscillator connected to the FPGA
	'''
	def _setup(self):
		AbstractSubdevice._setup(self)

		# Resources.

		read_write = ['frequency', 'power', 'power_on'] #'freq_resolution'
		for name in read_write:
			self.resources[name] = Resource(self, name, name)

		self.resources['frequency'].units = 'Hz'
		#self.resources['freq_resolution'].units = 'Hz'
	
	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)
		# Turn on port
		r = self.device.ask_raw(':5000/osc1?channel={0}&on=true&freq=500e6&power=0&freq_resolution=100e3&power_down=true'.format(self.num))
		if r.status_code != 200:
			Warning("Device not connected!")
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
		AbstractSubdevice.__init__(self, device, *args, **kwargs)
		self.num = num

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
		minFreq = 5e7 # Hz (Hardware limit)
		maxFreq = 5e9 # Hz (Hardware limit)
		if value < minFreq or value > maxFreq:
			raise ValueError('Value {0} not within the allowed bounds: {1} to {2}'.format(value, minFreq, maxFreq))

		r = self.device.ask_raw(':5000/osc1?&freq={0}'.format(value))
		if r.status_code != 200:
			Warning("Frequency not properly set!") 

		self.currentFrequency = value

	@property
	def power(self):
		# The power output by the oscillator
		return self.currentPower
		
	@power.setter
	def power(self, value):
		possible_powers = ['0','1','2','3'] # corresponds to -5, -2, 1 or 4 dBm, respectively 

		if value not in possible_powers:
			raise ValueError('Value {0} not part of the allowed powers: {1}'.format(value, possible_powers))
		
		r = self.device.ask_raw(':5000/osc1?power={0}'.format(value))
		if r.status_code != 200:
			Warning("Voltage not properly set!") 

		self.currentPower = value

	@property
	def power_on(self):
		return self.currentPower_on

	@power_on.setter
	def power_on(self, value):
		# Swap to match hardware code
		possible_values = {'true':'false','false':'true'}
		# Make robust to capitalization
		value = value.lower()
		if value not in possible_values:
			raise ValueError('Value {0} not part of the allowed values: {1}'.format(value, possible_values.values()))

		r = self.device.ask_raw(':5000/osc1?power_down={0}'.format(possible_values[value]))
		if r.status_code != 200:
			Exception("Voltage not properly set!")

		self.currentPower_on = value 

class fpga(AbstractDevice):
	"""
	Interface for the Pynq FPGA board
	"""
	
	def _setup(self):
		AbstractDevice._setup(self)

		self.DACports = []
		for num1 in range(16):
			port = DACPort(self, num1, **self.port_settings) # Naming convention for DAC goes 0 to 15
			self.DACports.append(port)
			self.subdevices['DACport{0}'.format(num1)] = port

		self.ADCports = []
		for num2 in range(2):
			port = ADCPort(self, num2, **self.port_settings) # Naming convention for DAC goes 0 to 7, but we are only using ports 0, 1 and 2
			self.ADCports.append(port)
			self.subdevices['ADCport{0}'.format(num2)] = port

		port = OSCPort(self, 0, **self.port_settings)
		self.OSCports = [port]
		self.subdevices['OSCport0'] = port

	def __init__(self, port_settings=None, *args, **kwargs):
		"""
		Initialize the voltage source and all its ports.
		port_settings: A dictionary of values to give to each port upon creation.
		"""

		if port_settings is None:
			self.port_settings = {}
		else:
			self.port_settings = port_settings

		AbstractDevice.__init__(self, *args, **kwargs)

	@Synchronized()
	def _connected(self):
		AbstractDevice._connected(self)
		# Add any initialization here. Careful: if you reconnect it will run this

name = 'Pynq FPGA board'
implementation = fpga
