from functools import wraps
from itertools import chain
from numpy import linspace, meshgrid, sort, unique
from scipy.interpolate import griddata

"""
Generic tools.
"""


def flatten(iterable):
	"""
	Flatten an iterable by one level.
	"""

	return chain.from_iterable(iterable)


def sift(items, cls):
	"""
	Filter out items which are not instances of cls.
	"""

	return [item for item in items if isinstance(item, cls)]


def triples_to_mesh(x, y, z, max_mesh=[-1,-1]):
	"""
	Convert 3 equal-sized lists of co-ordinates into an interpolated 2D mesh of z-values.

	Returns a tuple of:
		the mesh
		the x bounds
		the y bounds
		the z bounds
	"""

	x_values, y_values = sort(unique(x)), sort(unique(y))
	
	if (all (item > 0 for item in max_mesh)):
		display_len_x = min (len(x_values), max_mesh[0])
		display_len_y = min (len(y_values), max_mesh[1])
	else:
		display_len_x = len(x_values)
		display_len_y = len(y_values)

	x_space = linspace(x_values[0], x_values[-1], display_len_x)
	y_space = linspace(y_values[0], y_values[-1], display_len_y)

	target_x, target_y = meshgrid(x_space, y_space)
	
	target_z = griddata((x, y), z, (target_x, target_y), method='cubic')
	
	return (target_z, (x_values[0], x_values[-1]), (y_values[0], y_values[-1]),
			(min(z), max(z)))


class Enum(set):
	"""
	An enumerated type.

	>>> e = Enum(['a', 'b', 'c'])
	>>> e.a
	'a'
	>>> e.d
	...
	AttributeError: 'Enum' object has no attribute 'd'
	"""

	def __getattribute__(self, name):
		if name in self:
			return name
		else:
			return set.__getattribute__(self, name)


class PubDict(dict):
	"""
	A locking, publishing dictionary.
	"""

	def __init__(self, lock, send, topic, *args, **kwargs):
		"""
		lock: A re-entrant lock which supports context management.
		send: Message-sending method of a PubSub publisher.
		topic: The topic on which to send messages.
		"""

		dict.__init__(self, *args, **kwargs)

		self.lock = lock
		self.send = send
		self.topic = topic

	def __setitem__(self, k, v):
		"""
		Note: Values cannot be overwritten, to ensure that removal is always handled explicitly.
		"""

		with self.lock:
			if k in self:
				raise KeyError(k)

			if v is None:
				raise ValueError('No value given.')

			dict.__setitem__(self, k, v)

			self.send('{0}.added'.format(self.topic), name=k, value=v)

	def __delitem__(self, k):
		with self.lock:
			dict.__delitem__(self, k)

			self.send('{0}.removed'.format(self.topic), name=k)


class Synchronized(object):
	"""
	A decorator for methods which must be synchronized within an object instance.
	"""

	@staticmethod
	def __call__(f):
		@wraps(f)
		def decorated(self, *args, **kwargs):
			with self.lock:
				return f(self, *args, **kwargs)

		return decorated


class Without(object):
	"""
	A no-op object for use with "with".
	"""

	def __enter__(self, *args, **kwargs):
		return None

	def __exit__(self, *args, **kwargs):
		return False
