from ...mock.mock_abstract_device import MockAbstractDevice
from ..fpga import fpga

"""
Mock Pynq FPGA
*******This is not complete************
"""


class mockfpga(MockAbstractDevice, fpga):
	"""
	Mock interface for the DAC SP 927 voltage source
	"""

	def __init__(self, *args, **kwargs):
		self.mocking = fpga

		MockAbstractDevice.__init__(self, *args, **kwargs)

	def _reset(self):
		self.mock_state['frequency'] = 1000 # Hz
		self.mock_state['BNCAmplitude'] = 0.5 # V



name = 'Pynq FPGA board'
implementation = mockfpga
