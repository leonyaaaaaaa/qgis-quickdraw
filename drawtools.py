"""
quickdraw Tools - beta 1
Quick drawing tools for QGIS: point, line, rectangle, circle, polygon
and buffer, saved straight into memory layers.

Copyright (C) 2026 leonya (lyonya ivanchikov)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
from math import sqrt, pi, cos, sin
from qgis.gui import QgsMapTool, QgsRubberBand, QgsMapToolEmitPoint, QgsProjectionSelectionDialog
from qgis.core import QgsWkbTypes, QgsPointXY, QgsCoordinateReferenceSystem
from qgis.PyQt.QtCore import Qt, pyqtSignal, QPoint, QLocale
from qgis.PyQt.QtWidgets import (QDialog, QLineEdit, QDialogButtonBox, QGridLayout, 
                                 QLabel, QGroupBox, QVBoxLayout, QComboBox, 
                                 QPushButton, QInputDialog, QCheckBox)
from qgis.PyQt.QtGui import QDoubleValidator, QIntValidator, QKeySequence
from .utils import tr

class ToolRectangle(QgsMapToolEmitPoint):
    selectionDone = pyqtSignal()
    move = pyqtSignal()

    def __init__(self, iface, fill_color, stroke_color, stroke_width):
        self.map_canvas = iface.mapCanvas()
        super().__init__(self.map_canvas)
        self.iface = iface
        self.rb = QgsRubberBand(self.map_canvas, QgsWkbTypes.PolygonGeometry)
        self.rb.setFillColor(fill_color)
        self.rb.setStrokeColor(stroke_color)
        self.rb.setWidth(stroke_width)
        self.reset()

    def reset(self):
        self.pt_origin = self.pt_current = None
        self.is_tracking = False
        self.rb.reset(QgsWkbTypes.PolygonGeometry)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pt_origin = self.toMapCoordinates(event.pos())
            self.pt_current = self.pt_origin
            self.is_tracking = True

    def canvasReleaseEvent(self, event):
        self.is_tracking = False
        if event.button() != Qt.LeftButton: return
        
        if self.rb.numberOfVertices() > 3:
            self.selectionDone.emit()
        else:
            w, h, is_ok = DimensionDialog().prompt_dimensions()
            if w > 0 and h > 0 and is_ok:
                calculated_pt = QgsPointXY(self.pt_origin.x() + w, self.pt_origin.y() - h)
                self.rb.addPoint(calculated_pt)
                self.render_box(self.pt_origin, calculated_pt)
                self.selectionDone.emit()

    def canvasMoveEvent(self, event):
        if self.is_tracking:
            self.move.emit()
            self.pt_current = self.toMapCoordinates(event.pos())
            self.render_box(self.pt_origin, self.pt_current)

    def render_box(self, p_start, p_end):
        self.rb.reset(QgsWkbTypes.PolygonGeometry)
        if p_start.x() == p_end.x() or p_start.y() == p_end.y(): return
        self.rb.addPoint(QgsPointXY(p_start.x(), p_start.y()), False)
        self.rb.addPoint(QgsPointXY(p_start.x(), p_end.y()), False)
        self.rb.addPoint(QgsPointXY(p_end.x(), p_end.y()), False)
        self.rb.addPoint(QgsPointXY(p_end.x(), p_start.y()), True)
        self.rb.show()

    def deactivate(self):
        self.rb.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

class DimensionDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr('Rectangle size'))
        self.val_w = QLineEdit()
        self.val_h = QLineEdit()
        self.val_w.setValidator(QDoubleValidator())
        self.val_h.setValidator(QDoubleValidator())

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        layout = QGridLayout()
        layout.addWidget(QLabel(tr('Give a size in m:')), 0, 0)
        layout.addWidget(QLabel(tr('Width:')), 1, 0)
        layout.addWidget(QLabel(tr('Height:')), 1, 1)
        layout.addWidget(self.val_w, 2, 0)
        layout.addWidget(self.val_h, 2, 1)
        layout.addWidget(btn_box, 3, 0, 1, 2)
        self.setLayout(layout)

    def prompt_dimensions(self):
        result = self.exec_()
        w, h = 0.0, 0.0
        if self.val_w.text().strip() and self.val_h.text().strip():
            w = float(self.val_w.text())
            h = float(self.val_h.text())
        return w, h, result == QDialog.Accepted

class ToolPolygon(QgsMapTool):
    selectionDone = pyqtSignal()
    move = pyqtSignal()

    def __init__(self, iface, fill_color, stroke_color, stroke_width):
        self.map_canvas = iface.mapCanvas()
        super().__init__(self.map_canvas)
        self.iface = iface
        self.draw_state = 0
        self.rb = QgsRubberBand(self.map_canvas, QgsWkbTypes.PolygonGeometry)
        self.rb.setFillColor(fill_color)
        self.rb.setStrokeColor(stroke_color)
        self.rb.setWidth(stroke_width)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Undo) and self.rb.numberOfVertices() > 1:
            self.rb.removeLastPoint()

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.draw_state == 0:
                self.rb.reset(QgsWkbTypes.PolygonGeometry)
                self.draw_state = 1
            self.rb.addPoint(self.toMapCoordinates(event.pos()))
        else:
            if self.rb.numberOfVertices() > 2:
                self.draw_state = 0
                self.selectionDone.emit()
            else:
                self.reset()

    def canvasMoveEvent(self, event):
        if self.rb.numberOfVertices() > 0 and self.draw_state == 1:
            self.rb.removeLastPoint(0)
            self.rb.addPoint(self.toMapCoordinates(event.pos()))
        self.move.emit()

    def reset(self):
        self.draw_state = 0
        self.rb.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        self.rb.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

class ToolCircle(QgsMapTool):
    selectionDone = pyqtSignal()
    move = pyqtSignal()

    def __init__(self, iface, fill_color, stroke_color, stroke_width, N_segments=40):
        self.map_canvas = iface.mapCanvas()
        super().__init__(self.map_canvas)
        self.iface = iface
        self.draw_state = 0
        self.N_segments = N_segments
        self.rb = QgsRubberBand(self.map_canvas, QgsWkbTypes.PolygonGeometry)
        self.rb.setFillColor(fill_color)
        self.rb.setStrokeColor(stroke_color)
        self.rb.setWidth(stroke_width)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.draw_state = 1
            self.center_pt = self.toMapCoordinates(event.pos())
            self._build_circle(self.center_pt)

    def canvasMoveEvent(self, event):
        if self.draw_state == 1:
            self._build_circle(self.toMapCoordinates(event.pos()))
            self.rb.show()
            self.move.emit()

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton: return
        self.draw_state = 0
        if self.rb.numberOfVertices() > 3:
            self.selectionDone.emit()
        else:
            rad, is_ok = QInputDialog.getDouble(self.iface.mainWindow(), tr('Radius'), tr('Give a radius in m:'), min=0)
            if rad > 0 and is_ok:
                edge_pt = self.toMapCoordinates(event.pos())
                edge_pt.setX(edge_pt.x() + rad)
                self._build_circle(edge_pt)
                self.rb.show()
                self.selectionDone.emit()

    def _build_circle(self, edge_pt):
        radius = sqrt(self.center_pt.sqrDist(edge_pt))
        self.rb.reset(QgsWkbTypes.PolygonGeometry)
        for step in range(self.N_segments + 1):
            angle = step * (2.0 * pi / self.N_segments)
            self.rb.addPoint(QgsPointXY(self.center_pt.x() + radius * cos(angle),
                                        self.center_pt.y() + radius * sin(angle)))

    def reset(self):
        self.draw_state = 0
        self.rb.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        self.rb.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

class ToolLine(QgsMapTool):
    selectionDone = pyqtSignal()
    move = pyqtSignal()

    def __init__(self, iface, fill_color, stroke_color, stroke_width):
        self.map_canvas = iface.mapCanvas()
        super().__init__(self.map_canvas)
        self.iface = iface
        self.draw_state = 0
        self.rb = QgsRubberBand(self.map_canvas, QgsWkbTypes.LineGeometry)
        self.rb.setColor(stroke_color)
        self.rb.setWidth(stroke_width)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Undo) and self.rb.numberOfVertices() > 1:
            self.rb.removeLastPoint()

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.draw_state == 0:
                self.rb.reset(QgsWkbTypes.LineGeometry)
                self.draw_state = 1
            self.rb.addPoint(self.toMapCoordinates(event.pos()))
        else:
            if self.rb.numberOfVertices() > 2:
                self.draw_state = 0
                self.selectionDone.emit()
            else:
                self.reset()

    def canvasMoveEvent(self, event):
        if self.rb.numberOfVertices() > 0 and self.draw_state == 1:
            self.rb.removeLastPoint(0)
            self.rb.addPoint(self.toMapCoordinates(event.pos()))
        self.move.emit()

    def reset(self):
        self.draw_state = 0
        self.rb.reset(QgsWkbTypes.LineGeometry)

    def deactivate(self):
        self.rb.reset(QgsWkbTypes.LineGeometry)
        super().deactivate()

class ToolPoint(QgsMapTool):
    selectionDone = pyqtSignal()

    def __init__(self, iface, fill_color, stroke_color, stroke_width):
        self.map_canvas = iface.mapCanvas()
        super().__init__(self.map_canvas)
        self.iface = iface
        self.rb = QgsRubberBand(self.map_canvas, QgsWkbTypes.PointGeometry)
        self.rb.setColor(fill_color)
        self.rb.setWidth(stroke_width)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.rb.addPoint(self.toMapCoordinates(event.pos()))
            self.selectionDone.emit()

    def reset(self):
        self.rb.reset(QgsWkbTypes.PointGeometry)

    def deactivate(self):
        self.rb.reset(QgsWkbTypes.PointGeometry)
        super().deactivate()

class ToolBufferSelect(QgsMapTool):
    select = pyqtSignal()
    selectionDone = pyqtSignal()

    def __init__(self, iface, fill_color, stroke_color, stroke_width):
        self.map_canvas = iface.mapCanvas()
        super().__init__(self.map_canvas)
        self.iface = iface
        self.rb = QgsRubberBand(self.map_canvas, QgsWkbTypes.PolygonGeometry)
        self.rb.setFillColor(fill_color)
        self.rb.setStrokeColor(stroke_color)
        self.rb.setWidth(stroke_width)
        self.rbSelect = QgsRubberBand(self.map_canvas, QgsWkbTypes.PolygonGeometry)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.rbSelect.reset(QgsWkbTypes.PolygonGeometry)
            px, py = event.pos().x(), event.pos().y()
            offsets = [(-5, -5), (5, -5), (5, 5), (-5, 5)]
            for dx, dy in offsets:
                self.rbSelect.addPoint(self.toMapCoordinates(QPoint(px + dx, py + dy)))
            self.select.emit()
        else:
            self.selectionDone.emit()

    def reset(self):
        self.rb.reset(QgsWkbTypes.PolygonGeometry)
        self.rbSelect.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        self.rb.reset(QgsWkbTypes.PolygonGeometry)
        self.rbSelect.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

class CoordinateInputDialog(QDialog):
    def __init__(self, default_crs):
        super().__init__()
        self.setWindowTitle(tr('Coordinate Point Tool'))
        self.current_crs = default_crs
        
        self.layout_main = QVBoxLayout(self)
        
        self.chk_dms_mode = QCheckBox(tr("Use DMS mode (Degrees, Minutes, Seconds) instead of X/Y"), self)
        self.chk_dms_mode.toggled.connect(self._toggle_modes)
        self.layout_main.addWidget(self.chk_dms_mode)

        self.grp_xy = QGroupBox(tr("XY Coordinates"))
        grid_xy = QGridLayout(self.grp_xy)
        
        self.input_x = QLineEdit()
        self.input_y = QLineEdit()
        self.input_x.setValidator(QDoubleValidator())
        self.input_y.setValidator(QDoubleValidator())
        
        self.btn_crs = QPushButton(tr("Projection"))
        self.btn_crs.clicked.connect(self._change_crs)
        self.lbl_crs = QLabel(self.current_crs.authid())
        
        grid_xy.addWidget(QLabel("X"), 0, 0)
        grid_xy.addWidget(QLabel("Y"), 0, 1)
        grid_xy.addWidget(self.input_x, 1, 0)
        grid_xy.addWidget(self.input_y, 1, 1)
        grid_xy.addWidget(self.btn_crs, 2, 0)
        grid_xy.addWidget(self.lbl_crs, 2, 1)
        
        self.layout_main.addWidget(self.grp_xy)

        self.grp_dms = QGroupBox(tr("DMS Coordinates (WGS 84)"))
        self.grp_dms.setVisible(False) 
        grid_dms = QGridLayout(self.grp_dms)
        
        self.dms_fields = {}
        for axis in ['lat', 'lon']:
            self.dms_fields[f'{axis}_d'] = QLineEdit()
            self.dms_fields[f'{axis}_m'] = QLineEdit()
            self.dms_fields[f'{axis}_s'] = QLineEdit()
            
            self.dms_fields[f'{axis}_d'].setValidator(QIntValidator(0, 180))
            self.dms_fields[f'{axis}_m'].setValidator(QIntValidator(0, 59))
            self.dms_fields[f'{axis}_s'].setValidator(QDoubleValidator(0.0, 59.9999, 4))
        
        self.cb_lat_dir = QComboBox()
        self.cb_lat_dir.addItems(["N", "S"])
        
        self.cb_lon_dir = QComboBox()
        self.cb_lon_dir.addItems(["E", "W"])

        grid_dms.addWidget(QLabel(tr("Latitude")), 0, 0)
        grid_dms.addWidget(self.dms_fields['lat_d'], 0, 1)
        grid_dms.addWidget(self.dms_fields['lat_m'], 0, 2)
        grid_dms.addWidget(self.dms_fields['lat_s'], 0, 3)
        grid_dms.addWidget(self.cb_lat_dir, 0, 4)

        grid_dms.addWidget(QLabel(tr("Longitude")), 1, 0)
        grid_dms.addWidget(self.dms_fields['lon_d'], 1, 1)
        grid_dms.addWidget(self.dms_fields['lon_m'], 1, 2)
        grid_dms.addWidget(self.dms_fields['lon_s'], 1, 3)
        grid_dms.addWidget(self.cb_lon_dir, 1, 4)
        
        self.layout_main.addWidget(self.grp_dms)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        self.layout_main.addWidget(btn_box)

    def _toggle_modes(self, is_dms):
        self.grp_xy.setVisible(not is_dms)
        self.grp_dms.setVisible(is_dms)
        self.adjustSize()

    def _change_crs(self):
        selector = QgsProjectionSelectionDialog(self)
        if selector.exec_():
            self.current_crs = selector.crs()
            self.lbl_crs.setText(self.current_crs.authid())

    def get_coordinate_data(self):
        result = self.exec_()
        is_ok = result == QDialog.Accepted
        
        pt_x, pt_y = 0.0, 0.0
        output_crs = self.current_crs

        if self.chk_dms_mode.isChecked():
            output_crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
            try:
                lat = int(self.dms_fields['lat_d'].text() or 0) + \
                      float(self.dms_fields['lat_m'].text() or 0) / 60.0 + \
                      float(self.dms_fields['lat_s'].text() or 0) / 3600.0
                if self.cb_lat_dir.currentText() == "S": lat *= -1

                lon = int(self.dms_fields['lon_d'].text() or 0) + \
                      float(self.dms_fields['lon_m'].text() or 0) / 60.0 + \
                      float(self.dms_fields['lon_s'].text() or 0) / 3600.0
                if self.cb_lon_dir.currentText() == "W": lon *= -1
                
                pt_x, pt_y = lon, lat
            except ValueError:
                pass
        else:
            if self.input_x.text().strip() and self.input_y.text().strip():
                pt_x = QLocale().toDouble(self.input_x.text())[0]
                pt_y = QLocale().toDouble(self.input_y.text())[0]

        return QgsPointXY(pt_x, pt_y), output_crs, is_ok