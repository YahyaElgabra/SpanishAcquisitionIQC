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
		r = self.device.ask_raw(':5000/dac1?channel={0}&on=true'.format(self.num))
		if r.status_code != 200:
			Warning("Device not connected!")

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
		r = self.device.ask_raw(':5000/dac1?channel={0}&value={1}'.format(self.num, value))
		if r.status_code != 200:
			Warning("Voltage not properly set!") 

		self.currentVoltage = value
		
class ADCPort(AbstractSubdevice):
	'''
	An input port on the ADC for reading voltages connected to the FPGA.
	'''

	def _setup(self):
		AbstractDevice._setup(self)

		# Resources.
		read_only = ['reading']
		for name in read_only:
			self.resources[name] = Resource(self, name)

		self.resources['reading'].units = 'V'

	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)
		# Turn on port
		r = self.device.ask_raw(':5000/adc1?channel={0}&on=true'.format(self.num)) #TODO confirm that :5000 will always be the correct syntax
		if r.status_code != 200:
			Warning("Device not connected!")

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
	@Synchronized()
	def reading(self):
		"""
		The value measured by the device, as a quantity in V.
		"""

		r = self.device.ask_raw(':5000/adc1?channel={0}&reading?'.format(self.num)) #TODO confirm message
		if r.status_code != 200:
			Warning("Voltage not properly read!") 

		result = r.text['reading'] #TODO confirm how to extract voltage correctly
		return result

class OSCPort(AbstractSubdevice):
	'''
	An output port of the oscillator connected to the FPGA
	'''
	def _setup(self):
		AbstractDevice._setup(self)

		# Resources.

		read_write = ['frequency', 'phase', 'amplitude']
		for name in read_write:
			self.resources[name] = Resource(self, name, name)

		self.resources['frequency'].units = 'Hz'
		self.resources['phase'].units = 'deg'
		self.resources['amplitude'].units = 'V'
	
	@Synchronized()
	def _connected(self):
		AbstractSubdevice._connected(self)
		# Turn on port
		r = self.device.ask_raw(':5000/osc1?channel={0}&on=true'.format(self.num)) #TODO confirm that :5000 will always be the correct syntax
		if r.status_code != 200:
			Warning("Device not connected!")

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
		minFreq = 1 # Hz #TODO confirm min/max frequencies
		maxFreq = 2e9 # Hz
		if value < minFreq or value > maxFreq:
			raise ValueError('Value {0} not within the allowed bounds: {1} to {2}'.format(value, minFreq, maxFreq))

		r = self.device.ask_raw(':5000/osc1?channel={0}&frequency={1}'.format(self.num, value)) #TODO confirm message
		if r.status_code != 200:
			Warning("Voltage not properly set!") 

		self.currentFrequency = value

	@property
	def phase(self):
		# The phase of the output, (in degrees but SpanishAcquisition uses no units for this TODO: fix this)
		return self.currentPhase
		
	@phase.setter
	def phase(self,value):
		minPhase = -180
		maxPhase = 180
		if float(value) < minPhase or float(value) > maxPhase:
			raise ValueError('Value {0} not within the allowed bounds: {1} to {2}'.format(value, minPhase, maxPhase))
			
		r = self.device.ask_raw(':5000/osc1?channel={0}&phase={1}'.format(self.num, value)) #TODO confirm message
		if r.status_code != 200:
			Warning("Voltage not properly set!") 

		self.currentPhase = value

	@property
	@quantity_wrapped('V')
	def BNCAmplitude(self):
		# The amplitude of the output on the BNC output line (if enabled)
		# Currently using Vpp value, as Spanish Acquisition doesn't handle dBm currently (TODO: add dBm units)
		return self.currentAmplitude
		
	@BNCAmplitude.setter
	@quantity_unwrapped('V')
	def BNCAmplitude(self,value):
		minAMP = 0.1 # TODO confirm min/max amplitudes
		maxAmp = 1 # Vpp

		if value < minAMP or value > maxAmp:
			raise ValueError('Value {0} not within the allowed bounds: {1} to {2}'.format(value, minAMP, maxAmp))
		
		r = self.device.ask_raw(':5000/osc1?channel={0}&amplitude={1}'.format(self.num, value)) #TODO confirm message
		if r.status_code != 200:
			Warning("Voltage not properly set!") 

		self.currentAmplitude = value

class fpga(AbstractDevice):
	"""
	Interface for the Pynq FPGA board
	"""
	
	def _setup(self):
		AbstractDevice._setup(self)

		self.DACports = []
		for num in range(16):
			port = DACPort(self, num, **self.port_settings) # Naming convention for DAC goes 0 to 15
			self.DACports.append(port)
			self.subdevices['DACport{0}'.format(num)] = port

		self.ADCports = []
		for num in range(16): #TODO confirm that there are 16 ADC ports
			port = ADCPort(self, num, **self.port_settings)
			self.ADCports.append(port)
			self.subdevices['ADCport{0}'.format(num)] = port

		self.OSCports = []
		for num in range(2): #TODO confirm number of oscillator output ports
			port = OSCPort(self, num, **self.port_settings)
			self.OSCports.append(port)
			self.subdevices['OSCport{0}'.format(num)] = port

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
