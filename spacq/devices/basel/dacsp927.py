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
Physics Basel Low Noise/High Resolution DAC SP 927
Control the output voltages on all the ports.
"""

class Port(AbstractSubdevice):
	"""
	An output port on the voltage source.
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
		output = self.device.ask('{0} ON\n'.format(self.num))
		if output != 0:
			Warning("Device not connected!") 

		# Gets current voltage in hex, convert it to volts and save the result
		result_hex = self.device.ask('{0} V?\n'.format(self.num))
		result = self.hex_to_voltage(result_hex)
		self.currentVoltage = result

	# Converts from hex to voltage (see user manual for more info)
	def hex_to_voltage(self, number):
		return int(number,16)/838848 - 10

	# Converts from hex to voltage (see user manual for more info)
	def voltage_to_hex(self, voltage):
		return hex(int(round(((voltage+10)*838848), 0)))

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
		value_hex = self.voltage_to_hex(value)
		output = self.device.ask('{0} {1}\n'.format(self.num, value_hex))
		if output != 0:
			Warning("Voltage not properly set!") 

		result_hex = self.device.ask('{0} V?\n'.format(self.num))
		result = self.hex_to_voltage(result_hex)
		self.currentVoltage = result
		
class Dacsp927(AbstractDevice):
	"""
	Interface for the Physics Basel DAC SP 927 voltage source
	"""
	
	def _setup(self):
		AbstractDevice._setup(self)

		self.ports = []
		for num in range(8):
			port = Port(self, num+1, **self.port_settings) # Naming convention for DAC SP 927 goes 1 to 8
			self.ports.append(port)
			self.subdevices['port{0}'.format(num+1)] = port

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


name = 'dacsp927 Voltage Source'
implementation = Dacsp927
