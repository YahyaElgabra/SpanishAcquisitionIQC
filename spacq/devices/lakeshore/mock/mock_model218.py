import random

from ...mock.mock_abstract_device import MockAbstractDevice
from ..model218 import model218

"""
Mock Lakeshore 335 Temperature Controller
"""

class MockModel218(MockAbstractDevice, model218):
	"""
	Mock interface for Lakeshore 335 Temperature Controller.
	"""

	def __init__(self, *args, **kwargs):
		self.mocking = model218

		MockAbstractDevice.__init__(self, *args, **kwargs)
		
		self.mock_state = {}
		self.mock_state['readingstatus'] = 0
		self.mock_state['read_only'] = ['temperature']

	def _reset(self):
		pass
		
	def write(self, message, result=None, done=False):
		"""
		Write a message to the device.

		Parameters
		----------
		message : str
		result : str, optional
			What to return when the message is a query.
		done : bool, optional
			Whether the message is complete.
		"""
		if not done:
			cmd, args, query = self._split_message(message)
					
			if cmd[0] == 'krdg' and query:
				result = random.randint(5,100)
				done = True

		MockAbstractDevice.write(self, message, result, done)


name = 'Model 218 Temperature Monitor'
implementation = MockModel218
