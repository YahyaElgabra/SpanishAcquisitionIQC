from functools import wraps
from itertools import chain
from numpy import linspace, meshgrid, sort, unique, where, nan, zeros, ones, arange, fliplr
from numpy import min as npmin
from scipy.interpolate import griddata, interp1d

"""
Generic tools.
"""


def flatten(iterable):
	"""
	Flatten an iterable by one level.

	Parameters
	----------
	iterable : iterable

	Example
	-------
	>>> list(flatten([[1, 2], [3, 4]]))
	[1, 2, 3, 4]
	"""

	return chain.from_iterable(iterable)


def sift(items, cls):
	"""
	Filter out items which are not instances of cls.

	Parameters
	----------
	items : iterable
	cls : type
		The class to filter by.

	Example
	-------
	>>> list(sift([1, 2, 'a', 'b'], str))
	['a', 'b']
	"""

	return [item for item in items if isinstance(item, cls)]


def get_mask(x,y, tx, ty):
	"""
	The function calculates a mask based on the distance between two sets of coordinates and returns it.

	Parameters
	----------
	x : array
		The x-coordinates of the data points.
	y : array
		The y-coordinates of the data points.
	tx : array
		The x-coordinates of the grid.
	ty : array	
		The y-coordinates of the grid.

	Returns
	-------
	A 2D array representing a mask for the given set of x and y coordinates and a set of tx and ty coordinates.

	Example
	-------
	>>> x = linspace(0, 10, 11)
	>>> y = linspace(0, 10, 11)
	>>> tx = linspace(0, 10, 21)
	>>> ty = linspace(0, 10, 21)
	>>> mask = get_mask(x, y, tx, ty)
	>>> mask.shape
	(21, 21)
	"""
	dx = (tx[-1] - tx[0]) / (tx.size - 1)
	dy = (ty[-1] - ty[0]) / (ty.size - 1)

	d2 = dx ** 2 + dy ** 2

	xgrid = meshgrid(x, tx)
	ygrid = meshgrid(y, ty)
	
	xdist = (xgrid[0] - xgrid[1]) ** 2
	ydist = (ygrid[0] - ygrid[1]) ** 2

	mask = ones((tx.shape[0], ty.shape[0]))
	
	for i in range (mask.shape[0]):
		for j in range (mask.shape[1]):
			mask[i,j] = npmin(xdist[i] + ydist[j])

	mask = mask < d2
	mask = where(mask, mask, nan)

	return mask.T
	


def triples_to_mesh(x, y, z, max_mesh=[-1,-1], has_mask=False):
	"""
	Convert 3 equal-sized lists of co-ordinates into an interpolated 2D mesh of z-values.

	Parameters
	----------
	x : array
		The x-coordinates of the data points.
	y : array
		The y-coordinates of the data points.
	z : array
		The z-coordinates of the data points.
	max_mesh : array
		The maximum size of the mesh to be returned. If the value is negative, the mesh will be
		returned with the same size as the data points.
	has_mask : bool
		Whether or not to apply a mask to the data.

	Returns
	-------
	the mesh
	the x bounds
	the y bounds
	the z bounds

	Example
	-------
	>>> x = linspace(0, 10, 11)
	>>> y = linspace(0, 10, 11)
	>>> z = linspace(0, 10, 11)
	>>> mesh, x_bounds, y_bounds, z_bounds = triples_to_mesh(x, y, z)
	>>> mesh.shape
	(11, 11)
	>>> x_bounds
	(0.0, 10.0)
	>>> y_bounds
	(0.0, 10.0)
	>>> z_bounds
	(0.0, 10.0)
	"""

	x_values, y_values = sort(unique(x)), sort(unique(y))
	
	if all(item > 0 for item in max_mesh):
		display_len_x = min(len(x_values), max_mesh[0])
		display_len_y = min(len(y_values), max_mesh[1])
	else:
		display_len_x = len(x_values)
		display_len_y = len(y_values)

	x_space = linspace(x_values[0], x_values[-1], display_len_x)
	y_space = linspace(y_values[0], y_values[-1], display_len_y)

	target_x, target_y = meshgrid(x_space, y_space)

	target_z = griddata((x, y), z, (target_x, target_y), method='cubic')

	if has_mask:	
		mask =	get_mask(x, y, x_space, y_space)
		target_z = target_z * mask

	return (target_z, (x_values[0], x_values[-1]), (y_values[0], y_values[-1]),
			(min(z), max(z)))


def triples_to_mesh_y(x, y, z, max_mesh=[-1,-1]):
	"""
	Convert 3 equal-sized lists of co-ordinates into an interpolated mesh of z-values; with 
	interpolation along the y-axis only. The x-data must be of the form
	[x0, x0, x0, ..., x1, x1, x1, ..., xn, xn, xn, ..., xn] with each value xi repeated the same number of times.
	Otherwise unexpected behavior follows.

	Parameters
	----------
	x : array
		The x-coordinates of the data points.
	y : array
		The y-coordinates of the data points.
	z : array
		The z-coordinates of the data points.
	max_mesh : array
		The maximum size of the mesh to be returned. If the value is negative, the mesh will be
		returned with the same size as the data points.

	Returns
	-------
	the mesh
	the x bounds
	the y bounds
	the z bounds

	Example
	-------
	>>> x = linspace(0, 10, 11)
	>>> y = linspace(0, 10, 11)
	>>> z = x * y
	>>> mesh, x_bounds, y_bounds, z_bounds = triples_to_mesh_y(x, y, z)
	>>> mesh.shape
	(11, 11)
	>>> x_bounds
	(0.0, 10.0)
	>>> y_bounds
	(0.0, 10.0)
	>>> z_bounds
	(0.0, 100.0)
	"""
	x_values, y_values = sort(unique(x)), sort(unique(y))

	display_len_x = len(x_values)
	if (max_mesh[1] > 0):
		display_len_y = min (len(y_values), max_mesh[1])
	else:
		display_len_y = len(y_values)

	x_space = x_values
	y_space = linspace(y_values[0], y_values[-1], display_len_y)
	x_period = float(len(x)) / len(x_values)

	target_z = zeros([display_len_x, display_len_y])

	for i, xi in enumerate(x_space):
		y_range = arange(i * x_period, (i + 1) * x_period - 1).tolist()
		fy = interp1d (y[y_range], z[y_range], kind='cubic', bounds_error=False)
		tempy = fy(y_space)
		target_z[i] = tempy

	target_z = target_z.T
	if(x[0] - x[-1])>0:
		target_z = fliplr(target_z)	

	return (target_z, (x_values[0], x_values[-1]), (y_values[0], y_values[-1]),
			(min(z), max(z)))


class Enum(set):
	"""
	An enumerated type.

	Example
	-------
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

	Parameters
	----------
	lock: A re-entrant lock which supports context management.
	send: Message-sending method of a PubSub publisher.
	topic: The topic on which to send messages.
	"""

	def __init__(self, lock, send, topic, *args, **kwargs):
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
