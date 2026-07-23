"""
quickdraw tools - beta 1
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
from __future__ import print_function, absolute_import
import os
from builtins import str

from qgis.PyQt.QtCore import QTranslator, QSettings, QCoreApplication, QLocale, QVariant
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QInputDialog, QFileDialog
from qgis.PyQt.QtGui import QIcon

from qgis.core import (QgsFeature, QgsProject, QgsGeometry, QgsCoordinateTransform, 
                       QgsMapLayer, QgsFeatureRequest, QgsVectorLayer, 
                       QgsLayerTreeGroup, QgsRenderContext, QgsCoordinateReferenceSystem, 
                       QgsWkbTypes, QgsVectorFileWriter, QgsField)
from qgis.gui import QgsRubberBand

from .drawtools import (ToolPoint, ToolRectangle, ToolLine, ToolCircle, ToolPolygon,
                        ToolBufferSelect, CoordinateInputDialog)
from .quickdrawsettings import PluginConfigWindow
from .quickdrawlayerdialog import LayerPromptDialog
from .utils import tr

class QuickDraw(object):
    def __init__(self, iface):
        self.iface = iface
        self.status_bar = self.iface.statusBarIface()
        self.active_tool = None
        self.active_tool_name = None
        self.buffer_geometry = None
        self.recent_layers = {}
        
        self.plugin_actions = []
        self.menu_title = '&quickdraw'
        self.main_toolbar = self.iface.addToolBar('quickdraw')
        self.main_toolbar.setObjectName('quickdraw')
        self.config_window = PluginConfigWindow()

        self._setup_localization()

    def _setup_localization(self):
        override_flag = QSettings().value("locale/overrideFlag", False, type=bool)
        loc_name = QSettings().value("locale/userLocale", "") if override_flag else QLocale.system().name()
        if not loc_name:
            loc_name = 'en'
            
        locale_prefix = loc_name[0:2]
        translation_path = os.path.join(os.path.dirname(__file__), 'i18n', f'quickdraw_{locale_prefix}.qm')

        self.plugin_translator = None
        if os.path.exists(translation_path):
            self.plugin_translator = QTranslator()
            self.plugin_translator.load(translation_path)
            QCoreApplication.installTranslator(self.plugin_translator)

    def unload(self):
        for act in self.plugin_actions:
            self.iface.removePluginVectorMenu('&quickdraw', act)
            self.iface.removeToolBarIcon(act)
        del self.main_toolbar

    def create_action(self, icon_name, tooltip, callback, is_checkable=False, menu_obj=None, obj_name=None):
        full_icon_path = os.path.join(os.path.dirname(__file__), 'resources', icon_name)
        act = QAction(QIcon(full_icon_path), tooltip, self.iface.mainWindow())
        act.triggered.connect(callback)
        act.setCheckable(is_checkable)
        
        if menu_obj:
            act.setMenu(menu_obj)
            
        if obj_name:
            act.setObjectName(obj_name)

        self.main_toolbar.addAction(act)
        self.iface.addPluginToVectorMenu(self.menu_title, act)
        self.plugin_actions.append(act)
        return act

    def initGui(self):
        self.create_action('CircleDraw.svg', tr('Draw Circle'), self.activate_circle_tool, True, obj_name='mCircleDrawingTool')
        self.create_action('RectangleDraw.svg', tr('Draw Rectangle'), self.activate_rect_tool, True, obj_name='mRectangleDrawingTool')
        self.create_action('LineDraw.svg', tr('Draw Line'), self.activate_line_tool, True, obj_name='mLineDrawingTool')
        self.create_action('PolygonDraw.svg', tr('Draw Polygon'), self.activate_polygon_tool, True, obj_name='mPolygonDrawingTool')
        self.create_action('PointDraw.svg', tr('Draw Point'), self.activate_point_tool, True)
        self.create_action('PointDrawXY.svg', tr('Draw Point (XY)'), self.activate_coord_point_tool, False)
        self.create_action('BufferDraw.svg', tr('Draw Buffer'), self.activate_buffer_tool, True, obj_name='mBufferDrawingTool')
        self.create_action('Settings.svg', tr('Settings'), self.open_settings, obj_name='mSettings')

    def _reset_current_tool(self, tool_class, action_idx, shape_type, tool_id):
        if self.active_tool:
            self.active_tool.reset()
        self.active_tool = tool_class(
            self.iface, 
            self.config_window.fill_color,
            self.config_window.stroke_color,
            self.config_window.stroke_width
        )
        self.active_tool.setAction(self.plugin_actions[action_idx])
        self.active_tool.selectionDone.connect(self.process_geometry)
        if hasattr(self.active_tool, 'move'):
            self.active_tool.move.connect(self.update_status_metrics)
            
        self.iface.mapCanvas().setMapTool(self.active_tool)
        self.current_shape = shape_type
        self.active_tool_name = tool_id
        self.refresh_status_bar()

    def activate_point_tool(self):
        self._reset_current_tool(ToolPoint, 4, 'point', 'drawPoint')

    def activate_coord_point_tool(self):
        canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        dialog = CoordinateInputDialog(canvas_crs)
        pt, crs_obj, is_accepted = dialog.get_coordinate_data()
        
        self.target_crs = crs_obj
        if is_accepted:
            if pt.x() == 0 and pt.y() == 0:
                QMessageBox.critical(self.iface.mainWindow(), tr('Error'), tr('Invalid input !'))
            else:
                self.activate_point_tool()
                rb = QgsRubberBand(self.iface.mapCanvas(), QgsWkbTypes.GeometryType.PointGeometry)
                rb.setColor(self.config_window.fill_color)
                rb.setWidth(self.config_window.stroke_width)
                rb.addPoint(pt)
                self.active_tool.rb = rb
                self.current_shape = 'XYpoint'
                self.process_geometry()

    def activate_line_tool(self):
        self._reset_current_tool(ToolLine, 2, 'line', 'drawLine')

    def activate_rect_tool(self):
        self._reset_current_tool(ToolRectangle, 1, 'polygon', 'drawRect')

    def activate_circle_tool(self):
        if self.active_tool:
            self.active_tool.reset()
        self.active_tool = ToolCircle(
            self.iface, 
            self.config_window.fill_color,
            self.config_window.stroke_color,
            self.config_window.stroke_width
        )
        self.active_tool.setAction(self.plugin_actions[0])
        self.active_tool.selectionDone.connect(self.process_geometry)
        self.active_tool.move.connect(self.update_status_metrics)
        self.iface.mapCanvas().setMapTool(self.active_tool)
        self.current_shape = 'polygon'
        self.active_tool_name = 'drawCircle'
        self.refresh_status_bar()

    def activate_polygon_tool(self):
        self._reset_current_tool(ToolPolygon, 3, 'polygon', 'drawPolygon')

    def activate_buffer_tool(self):
        self.buffer_geometry = None
        self._reset_current_tool(ToolBufferSelect, 6, 'polygon', 'drawBuffer')
        self.active_tool.select.connect(self.calculate_buffer_intersection)

    def open_settings(self):
        self.config_window.settingsChanged.connect(self.apply_new_settings)
        self.config_window.show()

    def apply_new_settings(self):
        if self.active_tool and hasattr(self.active_tool, 'rb'):
            self.active_tool.rb.setFillColor(self.config_window.fill_color)
            self.active_tool.rb.setStrokeColor(self.config_window.stroke_color)
            self.active_tool.rb.setWidth(self.config_window.stroke_width)

    def refresh_status_bar(self):
        msgs = {
            'drawPoint': tr('Left click to place a point.'),
            'drawLine': tr('Left click to place points. Right click to confirm.'),
            'drawRect': tr('Maintain the left click to draw a rectangle.'),
            'drawCircle': tr('Maintain the left click to draw a circle. Simple Left click to give a perimeter.'),
            'drawPolygon': tr('Left click to place points. Right click to confirm.'),
            'drawBuffer': tr('Select a vector layer in the Layer Tree, then select an entity on the map.')
        }
        self.status_bar.showMessage(msgs.get(self.active_tool_name, ''))

    def update_status_metrics(self):
        geom = self.transform_geom(self.active_tool.rb.asGeometry(), 
                                   self.iface.mapCanvas().mapSettings().destinationCrs(), 
                                   QgsCoordinateReferenceSystem.fromEpsgId(2154))
        
        if self.active_tool_name == 'drawLine':
            val = geom.length()
            self.status_bar.showMessage(f"{tr('Length')}: {val:.2f} m" if val >= 0 else f"{tr('Length')}: 0 m")
        else:
            val = geom.area()
            self.status_bar.showMessage(f"{tr('Area')}: {val:.2f} m²" if val >= 0 else f"{tr('Area')}: 0 m²")

    def transform_geom(self, geometry, src_crs, dst_crs):
        ctx = QgsProject.instance().transformContext()
        cloned_geom = QgsGeometry(geometry)
        transform = QgsCoordinateTransform(src_crs, dst_crs, ctx)
        cloned_geom.transform(transform)
        return cloned_geom

    def calculate_buffer_intersection(self):
        rb_main = self.active_tool.rb
        rb_sel = self.active_tool.rb if isinstance(self.active_tool, ToolPolygon) else self.active_tool.rbSelect
        
        active_layer = self.iface.layerTreeView().currentLayer()
        if active_layer and active_layer.type() == QgsMapLayer.LayerType.VectorLayer and self.iface.layerTreeView().currentNode().isVisible():
            transformed_geom = self.transform_geom(rb_sel.asGeometry(), self.iface.mapCanvas().mapSettings().destinationCrs(), active_layer.crs())
            feats = active_layer.getFeatures(QgsFeatureRequest(transformed_geom.boundingBox()))
            
            intersected_geoms = []
            for f in feats:
                try:
                    if transformed_geom.intersects(f.geometry()):
                        intersected_geoms.append(f.geometry())
                except Exception:
                    intersected_geoms.append(f.geometry())
                    
            if intersected_geoms:
                for g in intersected_geoms:
                    if intersected_geoms[0].combine(g):
                        self.buffer_geometry = g if not self.buffer_geometry else self.buffer_geometry.combine(g)
                rb_main.setToGeometry(self.buffer_geometry, active_layer)
                
        if isinstance(self.active_tool, ToolPolygon):
            self.process_geometry()

    def _export_to_shapefile(self, mem_layer, lname):
        """Write the freshly built scratch layer to a Shapefile on disk and
        return a layer opened from that file. Falls back to the in-memory
        layer if the user cancels or the write fails."""
        attr_name = self.config_window.attr_name
        if len(attr_name) > 10:
            self.iface.messageBar().pushWarning(
                tr('Warning'),
                tr("Attribute field '{0}' will be truncated to 10 characters in the Shapefile.").format(attr_name)
            )

        start_dir = self.config_window.shapefile_dir or QgsProject.instance().homePath() or ''
        suggested_name = f"{(lname or 'quickdraw_layer').strip()}.shp"
        suggested_path = os.path.join(start_dir, suggested_name) if start_dir else suggested_name

        path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), tr('Save shapefile'), suggested_path, 'ESRI Shapefile (*.shp)'
        )
        if not path:
            return mem_layer

        if not path.lower().endswith('.shp'):
            path += '.shp'

        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = 'ESRI Shapefile'
        save_options.fileEncoding = 'UTF-8'

        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            mem_layer, path, QgsProject.instance().transformContext(), save_options
        )
        write_error = result[0] if isinstance(result, tuple) else result
        if write_error != QgsVectorFileWriter.WriterError.NoError:
            self.iface.messageBar().pushWarning(
                tr('Warning'), tr("Couldn't write the Shapefile, keeping a memory layer instead.")
            )
            return mem_layer

        self.config_window.set_shapefile_dir(os.path.dirname(path))
        return QgsVectorLayer(path, lname or os.path.splitext(os.path.basename(path))[0], 'ogr')

    def process_geometry(self):
        target_geom = self.active_tool.rb.asGeometry()
        is_valid = True
        has_warning = False
        err_no_attr = False
        err_zero_val = False
        
        current_layer = self.iface.layerTreeView().currentLayer()

        if self.active_tool_name == 'drawBuffer':
            if not self.buffer_geometry:
                has_warning, err_no_attr = True, True
            else:
                dist, ok_pressed = QInputDialog.getDouble(self.iface.mainWindow(), tr('Perimeter'), tr('Give a perimeter in m:') + '\n' + tr('(works only with metric crs)'), min=0)
                target_geom = self.buffer_geometry.buffer(dist, 40)
                self.active_tool.rb.setToGeometry(target_geom, QgsVectorLayer(f"Polygon?crs={current_layer.crs().authid()}", "", "memory"))
                if target_geom.length() == 0 and ok_pressed:
                    has_warning, err_zero_val = True, True

        if is_valid and not has_warning:
            lname, attr_val, tags_val, is_append, lst_idx, avail_layers = '', '', '', False, 0, []
            loop_ok, prompt_accepted = False, True
            
            def_layer_id = None
            if self.config_window.remember_layer:
                def_layer_id = self.recent_layers.get(self.current_shape)
            
            while not loop_ok and prompt_accepted:
                dialog = LayerPromptDialog(self.current_shape, self.config_window.attr_name, def_layer_id, self.config_window.tag_groups)
                lname, attr_val, tags_val, is_append, lst_idx, avail_layers, prompt_accepted = dialog.request_layer_info()
                
                if prompt_accepted:
                    loop_ok = (is_append and len(avail_layers) > 0) or (not is_append and lname.strip() != '')
                else:
                    loop_ok = True 

        if prompt_accepted and not has_warning:
            dest_layer = None
            try:
                if is_append:
                    dest_layer = avail_layers[lst_idx]
                    if self.current_shape in ['point', 'XYpoint']:
                        target_geom = target_geom.centroid()
                    existing_fields = [f.name() for f in dest_layer.fields()]
                    missing_fields = []
                    if self.config_window.attr_name not in existing_fields:
                        missing_fields.append(QgsField(self.config_window.attr_name, QVariant.String, len=255))
                    if 'Tags' not in existing_fields:
                        missing_fields.append(QgsField('Tags', QVariant.String, len=255))
                    if missing_fields:
                        dest_layer.startEditing()
                        for fld in missing_fields:
                            dest_layer.addAttribute(fld)
                        dest_layer.commitChanges()
                else:
                    crs_auth = self.iface.mapCanvas().mapSettings().destinationCrs().authid()
                    fields_def = f"field={self.config_window.attr_name}:string(255)&field=Tags:string(255)"
                    
                    if self.current_shape == 'point':
                        dest_layer = QgsVectorLayer(f"Point?crs={crs_auth}&{fields_def}", lname, "memory")
                        target_geom = target_geom.centroid()
                    elif self.current_shape == 'XYpoint':
                        dest_layer = QgsVectorLayer(f"Point?crs={self.target_crs.authid()}&{fields_def}", lname, "memory")
                        target_geom = target_geom.centroid()
                    elif self.current_shape == 'line':
                        dest_layer = QgsVectorLayer(f"LineString?crs={crs_auth}&{fields_def}", lname, "memory")
                    else:
                        dest_layer = QgsVectorLayer(f"Polygon?crs={crs_auth}&{fields_def}", lname, "memory")

                    if self.config_window.layer_format == 'shapefile':
                        dest_layer = self._export_to_shapefile(dest_layer, lname)
                
                dest_layer.startEditing()
                if not is_append:
                    sym = dest_layer.renderer().symbol()
                    sym.setColor(self.config_window.fill_color)
                    
                    if dest_layer.geometryType() == QgsWkbTypes.GeometryType.PolygonGeometry:
                        sym.symbolLayer(0).setStrokeColor(self.config_window.stroke_color)
                        sym.symbolLayer(0).setStrokeWidth(self.config_window.stroke_width * 0.26)
                    elif dest_layer.geometryType() == QgsWkbTypes.GeometryType.LineGeometry:
                        sym.setColor(self.config_window.stroke_color)
                        sym.setWidth(self.config_window.stroke_width * 0.26)
                    elif dest_layer.geometryType() == QgsWkbTypes.GeometryType.PointGeometry:
                        sym.symbolLayer(0).setStrokeColor(self.config_window.stroke_color)
                        sym.setSize(self.config_window.stroke_width * 2)
                    
                new_feat = QgsFeature(dest_layer.fields())
                new_feat.setGeometry(target_geom)
                new_feat.setAttribute(self.config_window.attr_name, attr_val)
                if 'Tags' in [f.name() for f in dest_layer.fields()]:
                    new_feat.setAttribute('Tags', tags_val)
                dest_layer.dataProvider().addFeatures([new_feat])
                dest_layer.commitChanges()
                
                if self.config_window.remember_layer:
                    self.recent_layers[self.current_shape] = dest_layer.id()
                
                if not is_append:
                    proj = QgsProject.instance()
                    proj.addMapLayer(dest_layer, False)
                    root = proj.layerTreeRoot()
                    if not root.findGroup(self.config_window.attr_name):
                        root.insertChildNode(0, QgsLayerTreeGroup(self.config_window.attr_name))
                    grp = root.findGroup(self.config_window.attr_name)
                    grp.insertLayer(0, dest_layer)
                    
                self.iface.layerTreeView().refreshLayerSymbology(dest_layer.id())
                self.iface.mapCanvas().refresh()
            except Exception as exc:
                if dest_layer is not None and dest_layer.isEditable():
                    dest_layer.rollBack()
                self.iface.messageBar().pushCritical(
                    tr('Error'), tr("Couldn't add the shape: {0}").format(exc)
                )
        else:
            if has_warning:
                if err_no_attr:
                    self.iface.messageBar().pushWarning(tr('Warning'), tr('You didn\'t click on a layer\'s attribute !'))
                elif err_zero_val:
                    self.iface.messageBar().pushWarning(tr('Warning'), tr('You must give a non-null value for a point\'s or line\'s perimeter !'))
                else:
                    self.iface.messageBar().pushWarning(tr('Warning'), tr('There is no selected layer, or it is not vector nor visible !'))
                    
        self.active_tool.reset()
        self.refresh_status_bar()
        self.buffer_geometry = None