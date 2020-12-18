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
Pynq FPGA board for the IDEaS project
First test to determine if we can connect using Spanish Acquisition
"""

class DACPort(AbstractSubdevice):
	"""
	An output port on the DAC voltage source connected to the FPGA.
	"""
	def _setup(self):
		AbstractSubdevice._setup(self)

		# Resources.
		read_write = ['voltage', 'span']
		for name in read_write:
			self.resources[name] = Resource(self, name, name)

		self.resources['voltage'].units = 'V'
		self.resources['span'].units = 'V'

	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)

		# Turn on port
		output = self.device.ask_raw('{0} ON\r\n'.format(self.num)).strip('\r\n')
		if output != 0:
			Warning("Device not connected!")
		# Gets current voltage in hex, convert it to volts and save the result
		result = self.device.ask_raw('{0} V?\r\n'.format(self.num)).strip('\r\n')
		self.currentVoltage = result

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
		output = self.device.ask_raw('{0} {1}\r\n'.format(self.num, value)).strip('\r\n')
		if output != 0:
			Warning("Voltage not properly set!") 

		result = self.device.ask_raw('{0} V?\r\n'.format(self.num)).strip('\r\n')
		self.currentVoltage = result
		
class fpga(AbstractDevice):
	"""
	Interface for the Pynq FPGA board
	"""
	
	def _setup(self):
		AbstractDevice._setup(self)

		self.ports = []
		for num in range(16):
			port = DACPort(self, num, **self.port_settings) # Naming convention for DAC goes 0 to 15
			self.ports.append(port)
			self.subdevices['port{0}'.format(num)] = port

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
