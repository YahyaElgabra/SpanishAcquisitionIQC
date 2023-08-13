import logging
log = logging.getLogger(__name__)

from spacq.interface.resources import Resource
from spacq.tool.box import Synchronized

from ..abstract_device import AbstractDevice
from ..tools import quantity_wrapped

"""
Lakeshore Model 218 Temperature Monitor

Read temperature of up to 8 channels
"""

class model218(AbstractDevice):
	"""
	Interface for Lakeshore Model 218 Temperature Monitor
	"""
	
	def _setup(self):
		AbstractDevice._setup(self)

		# Resources.
		self.read_only = ['temperature1','temperature2','temperature3','temperature4','temperature5','temperature6','temperature7','temperature8']
		for name in self.read_only:
			self.resources[name] = Resource(self, name)
			self.resources[name].units = 'K'
								
	@Synchronized()
	def _connected(self):
		AbstractDevice._connected(self)

	@Synchronized()
	def reset(self):
		"""
		Reset the device to its default state.
		"""

		log.info('Resetting "{0}".'.format(self.name))
		self.write('*rst')

	@property
	@quantity_wrapped('K')
	@Synchronized()
	def temperature1(self):
		"""
		Return the temperature of channel 1 in Kelvin.

		Returns
		-------
		float
		"""

		return float(self.ask('krdg? 1'))

	@property
	@quantity_wrapped('K')
	@Synchronized()
	def temperature2(self):
		"""
		Return the temperature of channel 2 in Kelvin.

		Returns
		-------
		float
		"""
		return float(self.ask('krdg? 2'))

	@property
	@quantity_wrapped('K')
	@Synchronized()
	def temperature3(self):
		"""
		Return the temperature of channel 3 in Kelvin.

		Returns
		-------
		float
		"""
		return float(self.ask('krdg? 3'))

	@property
	@quantity_wrapped('K')
	@Synchronized()
	def temperature4(self):
		"""
		Return the temperature of channel 4 in Kelvin.

		Returns
		-------
		float
		"""
		return float(self.ask('krdg? 4'))

	@property
	@quantity_wrapped('K')
	@Synchronized()
	def temperature5(self):
		"""
		Return the temperature of channel 5 in Kelvin.

		Returns
		-------
		float
		"""
		return float(self.ask('krdg? 5'))

	@property
	@quantity_wrapped('K')
	@Synchronized()
	def temperature6(self):
		"""
		Return the temperature of channel 6 in Kelvin.

		Returns
		-------
		float
		"""
		return float(self.ask('krdg? 6'))

	@property
	@quantity_wrapped('K')
	@Synchronized()
	def temperature7(self):
		"""
		Return the temperature of channel 7 in Kelvin.

		Returns
		-------
		float		
		"""
		return float(self.ask('krdg? 7'))

	@property
	@quantity_wrapped('K')
	@Synchronized()
	def temperature8(self):
		"""
		Return the temperature of channel 8 in Kelvin.

		Returns
		-------
		float
		"""
		return float(self.ask('krdg? 8'))

name = 'Model 218 Temperature Monitor'
implementation = model218
