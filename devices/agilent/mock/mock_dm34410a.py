from devices.agilent.dm34410a import DM34410A
from devices.mock.mock_abstract_device import MockAbstractDevice

"""
Mock Agilent 34410A Digital Multimeter

Control a fake multimeter.
"""


class MockDM34410A(MockAbstractDevice, DM34410A):
	"""
	Mock interface for Agilent 34410A Digital Multimeter.
	"""

	def __reset(self):
		"""
		Reset to a known blank state.
		"""

		self.mock_state['mode'] = 'dc'
		self.mock_state['nplc'] = '1'
		self.mock_state['auto_zero'] = 1

	def __init__(self, *args, **kwargs):
		"""
		Pretend to connect to the DM.
		"""

		MockAbstractDevice.__init__(self, *args, **kwargs)

		self.name = 'DM34410A'
		self.__reset()

		DM34410A._setup(self)

	def write(self, message, result=None, done=False):
		if not done:
			cmd, args, query = self._split_message(message)

			if cmd[0] == '*rst':
				self.__reset()
				done = True
			elif cmd[0] == 'configure':
				if cmd[1] == 'voltage' and cmd[2] == 'dc':
					self.mock_state['mode'] = 'dc'
					done = True
			elif cmd[0] == 'measure':
				if cmd[1] == 'voltage' and cmd[2] == 'dc' and query:
					result = '+4.27150000E-03'
					done = True
			elif cmd[0] == 'sense':
				if cmd[1] == 'voltage' and cmd[2] == 'dc':
					if cmd[3] == 'nplc':
						if query:
							result = self.mock_state['nplc']
						else:
							self.mock_state['nplc'] = args
						done = True
					elif cmd[3] == 'zero' and cmd[4] == 'auto':
						if query:
							result = self.mock_state['auto_zero']
						else:
							if args in ['on']:
								value = 1
							elif args in ['once', 'off']:
								value = 0
							self.mock_state['auto_zero'] = value
						done = True
			elif cmd[0] == 'read' and query:
				result = '-1.26360000E-02'
				done = True

		MockAbstractDevice.write(self, message, result, done)


implementation = MockDM34410A


if __name__ == '__main__':
	import unittest

	from tests import test_mock_awg5014b as my_tests

	unittest.main(module=my_tests)
