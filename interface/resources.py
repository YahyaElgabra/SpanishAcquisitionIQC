"""
Tools for working with generic resources.
"""


class NotReadable(Exception):
	"""
	Resource cannot be read from.
	"""

	pass


class NotWritable(Exception):
	"""
	Resource cannot be written to.
	"""

	pass


class Resource(object):
	"""
	A generic resource which can potentially be read from or written to.
	"""

	def __init__(self, obj=None, getter=None, setter=None, converter=None, allowed_values=None):
		"""
		obj: The device to which the resource belongs.
		getter: The method used to get the value.
		setter: The method used to set the value.
		converter: A function which returns a valid value for the resource, given a string.
		allowed_values: A set of all values which are valid for the resource.

		The getter and setter can be actual methods, or just attribute/property name strings.
		"""

		if getter is not None and not callable(getter) and obj is None:
			raise ValueError('Cannot call getter with no object.')

		if setter is not None and not callable(setter) and obj is None:
			raise ValueError('Cannot call setter with no object.')

		self.obj = obj
		self.getter = getter
		self.setter = setter
		self.converter = converter
		if allowed_values is not None:
			self.allowed_values = set(allowed_values)
		else:
			self.allowed_values = None

	@property
	def value(self):
		"""
		The value of the resource.
		"""

		if self.getter is None:
			raise NotReadable()

		if callable(self.getter):
			return self.getter()
		elif self.obj is not None:
			return getattr(self.obj, self.getter)
		else:
			raise NotReadable()

	@value.setter
	def value(self, v):
		if self.setter is None:
			raise NotWritable()

		if callable(self.setter):
			self.setter(v)
		elif self.obj is not None:
			setattr(self.obj, self.setter, v)
		else:
			raise NotWritable()

	def convert(self, value):
		if self.converter is not None:
			return self.converter(value)
		else:
			return value


if __name__ == '__main__':
	import unittest

	from tests import test_resources as my_tests

	unittest.main(module=my_tests)
