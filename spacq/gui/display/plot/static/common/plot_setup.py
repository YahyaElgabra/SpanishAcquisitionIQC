import wx

from .....tool.box import Dialog

"""
Plot configuration.
"""

class AxisSelectionPanel(wx.Panel):
	"""
	A panel for choosing the headings to be used for the axes.
	"""

	def __init__(self, parent, axes, headings, selection_callback, *args, **kwargs):
		wx.Panel.__init__(self, parent, *args, **kwargs)

		self.selection_callback = selection_callback

		# Panel.
		panel_box = wx.BoxSizer(wx.HORIZONTAL)

		## Axes.
		self.axis_lists = []

		for axis in axes:
			axis_static_box = wx.StaticBox(self, label=axis)
			axis_box = wx.StaticBoxSizer(axis_static_box, wx.VERTICAL)
			panel_box.Add(axis_box, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)

			axis_list = wx.ListBox(self, choices=headings)
			axis_list.SetMinSize((-1, 300))
			self.Bind(wx.EVT_LISTBOX, self.OnAxisSelection, axis_list)
			axis_box.Add(axis_list, proportion=1, flag=wx.EXPAND)

			self.axis_lists.append(axis_list)

		self.SetSizer(panel_box)

	def OnAxisSelection(self, evt=None):
		"""
		Announce the latest selection.
		"""

		result = [None if list.Selection == wx.NOT_FOUND else list.Selection for
				list in self.axis_lists]

		self.selection_callback(result)


class PlotSetupDialog(Dialog):

	bounds_format = '{0:.4e}'
	"""
	Plot configuration dialog.
	"""

	def __init__(self, parent, headings, axis_names, max_mesh = [-1, -1], *args, **kwargs):
		Dialog.__init__(self, parent, *args, **kwargs)

		self.max_mesh = max_mesh #derivative classes can choose to call this constructor with or wihtout the  max_mesh argument;
					 # defaults to [-1, -1] meaning 'skip'
		self.axes = [None for _ in axis_names]

		# Dialog.
		dialog_box = wx.BoxSizer(wx.VERTICAL)

		## Axis setup.
		axis_panel = AxisSelectionPanel(self, axis_names, headings, self.OnAxisSelection)
		dialog_box.Add(axis_panel)

		## Input: Max Grid Points
		if (all (item > 0 for item in max_mesh)):
			self.has_max_mesh_value = True

			grid_box = wx.BoxSizer(wx.HORIZONTAL)
			button_static_box = wx.StaticBox(self, label='Max Grid Points')
			settings_box = wx.StaticBoxSizer(button_static_box, wx.HORIZONTAL)
			grid_box.Add(settings_box, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)

			dialog_box.Add(grid_box, flag=wx.CENTER)

			### Max X mesh size.
			settings_box.Add(wx.StaticText(self, label='x: '),
				flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
			self.mesh_x_value = wx.TextCtrl(self,
				value=str(max_mesh[0]),
				size=(100, -1), style=wx.TE_PROCESS_ENTER)
			self.Bind(wx.EVT_TEXT_ENTER, self.OnXValue, self.mesh_x_value)
			settings_box.Add(self.mesh_x_value, flag=wx.RIGHT, border=20)

			### Max Y mesh size.
			settings_box.Add(wx.StaticText(self, label='y: '),
				flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
			self.mesh_y_value = wx.TextCtrl(self,
				value=str(max_mesh[1]),
				size=(100, -1), style=wx.TE_PROCESS_ENTER)
			self.Bind(wx.EVT_TEXT_ENTER, self.OnYValue, self.mesh_y_value)
			settings_box.Add(self.mesh_y_value, flag=wx.RIGHT, border=20)
		else:
			self.has_max_mesh_value = False			

		## End buttons.
		button_box = wx.BoxSizer(wx.HORIZONTAL)
		dialog_box.Add(button_box, flag=wx.CENTER)

		self.ok_button = wx.Button(self, wx.ID_OK)
		self.ok_button.Disable()
		self.Bind(wx.EVT_BUTTON, self.OnOk, self.ok_button)
		button_box.Add(self.ok_button)

		cancel_button = wx.Button(self, wx.ID_CANCEL)
		button_box.Add(cancel_button)

		self.SetSizerAndFit(dialog_box)

	def OnAxisSelection(self, values):
		self.axes = values

		self.ok_button.Enable(all(axis is not None for axis in self.axes))

	def OnOk(self, evt=None):
		if self.has_max_mesh_value: # update the values typed in (but ENTER not pressed) for max_x, max_y
			self.OnXValue()
			self.OnYValue()
		if self.make_plot():
			self.Destroy()

			return True

	def OnXValue(self, evt=None):
		value = self.mesh_x_value.Value
		try:
			value = int(value)
		except ValueError:
			value = self.max_mesh[0]

		if (value > 0):
			self.max_mesh[0] = value

		# Update the text box.
		self.mesh_x_value.Value = str(self.max_mesh[0])

	def OnYValue(self, evt=None):
		value = self.mesh_y_value.Value
		try:
			value = int(value)
		except ValueError:
			value = self.max_mesh[1]

		if (value > 0):
			self.max_mesh[1] = value

		# Update the text box.
		self.mesh_y_value.Value = str(self.max_mesh[1])
