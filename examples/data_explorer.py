import logging
logging.basicConfig(level=logging.WARNING)

from functools import partial
import wx

from spacq.gui.display.plot.static.delegator import formats, available_formats
from spacq.gui.display.table.generic import TabularDisplayFrame
from spacq.gui.tool.box import load_csv, MessageDialog


class DataExplorerApp(wx.App):
	def OnInit(self):
		# Frames.
		self.csv_frame = TabularDisplayFrame(None, title='Data Explorer')

		# Menu.
		menuBar = wx.MenuBar()

		## File.
		menu = wx.Menu()

		item = menu.Append(wx.ID_ANY, '&Open...')
		self.Bind(wx.EVT_MENU, self.OnMenuFileOpen, item)

		item = menu.Append(wx.ID_ANY, '&Close')
		self.Bind(wx.EVT_MENU, self.OnMenuFileClose, item)

		menu.AppendSeparator()

		item = menu.Append(wx.ID_EXIT, 'E&xit')
		self.Bind(wx.EVT_MENU, self.OnMenuFileExit, item)

		menuBar.Append(menu, '&File')

		## Plot.
		menu = wx.Menu()

		menuBar.Append(menu, '&Plot')

		menu.Append(wx.ID_ANY, ' 2D:').Enable(False)

		self.two_dimensional_menu = menu.Append(wx.ID_ANY, '&Curve...')
		self.Bind(wx.EVT_MENU, partial(self.create_plot, formats.two_dimensional),
				self.two_dimensional_menu)

		menu.AppendSeparator()

		menu.Append(wx.ID_ANY, ' 3D:').Enable(False)

		self.colormapped_menu = menu.Append(wx.ID_ANY, '&Colormapped...')
		self.Bind(wx.EVT_MENU, partial(self.create_plot, formats.colormapped),
				self.colormapped_menu)

		self.surface_menu = menu.Append(wx.ID_ANY, 'S&urface...')
		self.Bind(wx.EVT_MENU, partial(self.create_plot, formats.surface),
				self.surface_menu)

		## Help.
		menu = wx.Menu()

		### About.
		item = menu.Append(wx.ID_ANY, '&About...')
		self.Bind(wx.EVT_MENU, self.OnMenuHelpAbout, item)

		menuBar.Append(menu, '&Help')

		self.csv_frame.SetMenuBar(menuBar)

		self.update_plot_menus(False)

		# Display.
		self.csv_frame.Show()
		self.csv_frame.SetSize((800, 600))

		self.SetTopWindow(self.csv_frame)
		self.csv_frame.Raise()

		return True

	def update_plot_menus(self, status):
		"""
		If status is True, enable the plot menus corresponding to the available formats. Otherwise, disable all.
		"""

		pairs = [
			(formats.two_dimensional, self.two_dimensional_menu),
			(formats.colormapped, self.colormapped_menu),
			(formats.surface, self.surface_menu),
		]

		for format, menu in pairs:
			if not status or format in available_formats:
				menu.Enable(status)

	def create_plot(self, format, evt=None):
		"""
		Open up a dialog to configure the selected plot format.
		"""

		headings, rows = self.csv_frame.display_panel.GetValue()
		available_formats[format](self.csv_frame, headings, rows).Show()

	def OnMenuFileOpen(self, evt=None):
		try:
			result = load_csv(self.csv_frame)
		except IOError as e:
			MessageDialog(self.csv_frame, str(e), 'Could not load data').Show()
			return

		if result is None:
			return

		has_header, values = result
		self.csv_frame.display_panel.from_csv_data(has_header, values)

		self.update_plot_menus(len(self.csv_frame.display_panel) > 0)

	def OnMenuFileClose(self, evt=None):
		self.csv_frame.display_panel.SetValue([], [])

		self.update_plot_menus(False)

	def OnMenuFileExit(self, evt=None):
		if self.csv_frame:
			self.csv_frame.Close()

	def OnMenuHelpAbout(self, evt=None):
		info = wx.AboutDialogInfo()
		info.SetName('Data Explorer')
		info.SetDescription('An application for displaying data in tabular and graphical form.')

		wx.AboutBox(info)


if __name__ == "__main__":
	app = DataExplorerApp()
	app.MainLoop()