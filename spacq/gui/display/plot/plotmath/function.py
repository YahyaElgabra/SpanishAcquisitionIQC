import wx

from ....tool.box import MessageDialog
from .common.math_setup import MathSetupDialog_Function
from numpy import concatenate

class FunctionMathSetupDialog(MathSetupDialog_Function):

	dheading = []
	ddata = []
	
	def __init__(self, parent, headings, data, *args, **kwargs):
		MathSetupDialog_Function.__init__(self, parent, headings, ['x'], *args, **kwargs)

		self.parent = parent
		self.headings = headings
		self.data = data


    	def calculate(self):
        	try:
            		y_data = [self.data[:,x].astype(float) for x in self.axes]
       		except ValueError as e:
            		MessageDialog(self, str(e), 'Invalid value').Show()
            		return

		title = 'y = {0}'.format(self.function_input.Value)
		y_data = y_data[0]
		d_data = eval(self.function_input.Value.replace('x','y_data'))
		d_data = d_data.reshape(d_data.size,1)
		return(title,d_data)


