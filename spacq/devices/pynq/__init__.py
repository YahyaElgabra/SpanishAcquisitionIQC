import logging
log = logging.getLogger(__name__)

name = 'Pynq'

from . import fpga
models = [fpga]
log.debug('Found models for "{0}": {1}'.format(name, ''.join(str(x) for x in models)))

from .mock import mock_fpga
mock_models = [mock_fpga]
log.debug('Found mock models for "{0}": {1}'.format(name, ''.join(str(x) for x in mock_models)))
