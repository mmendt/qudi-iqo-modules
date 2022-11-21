# -*- coding: utf-8 -*-
"""
FIXME

Copyright (c) 2022, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

from enum import IntEnum
from pyqtgraph import ScatterPlotItem
from PySide2 import QtWidgets, QtCore, QtGui

from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.core.module import GuiBase
from qudi.core.configoption import ConfigOption

from qudi.util.widgets.plotting.plot_widget import DataSelectionPlotWidget


class FollowMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('qudi: Follower Test')
        ranges = (-0.0005, 0.0005)
        self.plot_widget = DataSelectionPlotWidget(selection_bounds=[ranges, ranges],
                                                   allow_tracking_outside_data=True,
                                                   xy_region_selection_crosshair=True,
                                                   xy_region_selection_handles=False)
        self.plot_data = ScatterPlotItem()
        self.plot_widget.addItem(self.plot_data)
        self.plot_widget.add_region_selection(span=((0, 0), (0, 0)),
                                              mode=DataSelectionPlotWidget.SelectionMode.XY)
        self.plot_widget.setRange(xRange=ranges, yRange=ranges)
        self.setCentralWidget(self.plot_widget)


class FollowGui(GuiBase):
    """ FIXME
    """

    # declare connectors
    _follower = Connector(name='follow_logic', interface='FollowLogic')

    # declare signals
    sigTargetPositionUpdated = QtCore.Signal(tuple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = None

    def on_activate(self):
        """ Create all UI objects and show the window.
        """
        self._mw = FollowMainWindow()
        self._mw.plot_widget.sigRegionSelectionChanged.connect(self._crosshair_moved)
        self._restore_window_geometry(self._mw)
        follower = self._follower()
        follower.sigPositionChanged.connect(self._position_updated, QtCore.Qt.QueuedConnection)
        self.sigTargetPositionUpdated.connect(follower.set_target_pos, QtCore.Qt.QueuedConnection)
        curr_pos = follower.current_pos
        self._position_updated(curr_pos)
        crosshair_span = ((curr_pos[0]-0.00001, curr_pos[0]+0.00001),
                          (curr_pos[1]-0.00001, curr_pos[1]+0.00001))
        self._mw.plot_widget.move_region_selection(crosshair_span, 0)
        self.show()

    def on_deactivate(self):
        """ Hide window empty the GUI and disconnect signals
        """
        self._mw.plot_widget.sigRegionSelectionChanged.disconnect()
        self.sigTargetPositionUpdated.disconnect()
        self._follower().sigPositionChanged.disconnect(self._position_updated)
        self._save_window_geometry(self._mw)
        self._mw.close()

    def show(self):
        """ Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def _crosshair_moved(self, selection_dict):
        selection = selection_dict[DataSelectionPlotWidget.SelectionMode.XY]
        if selection:
            self.sigTargetPositionUpdated.emit(selection[0][0])

    def _position_updated(self, pos):
        x, y = pos
        self._mw.plot_data.addPoints(x=[x], y=[y])
