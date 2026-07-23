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
from qgis.PyQt.QtCore import Qt, QEvent
from qgis.PyQt.QtWidgets import QDialog, QComboBox, QLineEdit, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel
from qgis.core import QgsProject
from .utils import tr
from .quickdrawtags import QuickTagPicker

class LayerPromptDialog(QDialog):
    def __init__(self, shape_type, attr_field_name, default_layer_id=None, tag_groups=None):
        super().__init__()
        self.setWindowTitle(tr('Drawing'))
        self.tag_groups = tag_groups or []
        self.selected_tags = []

        type_mapper = {'point': 'Point', 'XYpoint': 'Point', 'line': 'LineString'}
        target_uri_type = type_mapper.get(shape_type, 'Polygon')

        self.combo_layers = QComboBox()
        self.available_layers = []
        
        for layer in QgsProject.instance().mapLayers().values():
            if (layer.customProperty('quickdraw/geom_category') == target_uri_type
                    and layer.customProperty('quickdraw/attr_field') == attr_field_name):
                self.available_layers.append(layer)
                self.combo_layers.addItem(layer.name())

        self.chk_append = QCheckBox(tr('Add to an existing layer'))
        self.chk_append.toggled.connect(self._toggle_append_mode)

        self.preselect_idx = -1
        if default_layer_id:
            for idx, lay in enumerate(self.available_layers):
                if lay.id() == default_layer_id:
                    self.preselect_idx = idx
                    break

        self.lbl_new_name = QLabel(tr('New layer name:'))
        self.input_layer_name = QLineEdit()
        self.input_attribute = QLineEdit()

        btn_container = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, Qt.Orientation.Horizontal, self)
        btn_container.accepted.connect(self.accept)
        btn_container.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.lbl_new_name)
        layout.addWidget(self.input_layer_name)
        layout.addWidget(self.chk_append)
        layout.addWidget(self.combo_layers)
        layout.addWidget(QLabel(tr('Note for this object (attribute):')))
        layout.addWidget(self.input_attribute)

        if self.tag_groups:
            tags_hint = tr('Tags (press Tab in the note field above to step through your tag groups):')
            layout.addWidget(QLabel(tags_hint))
            self.lbl_tags_value = QLabel(tr('(none)'))
            layout.addWidget(self.lbl_tags_value)
            self.input_attribute.installEventFilter(self)

        if not self.available_layers:
            self.chk_append.setEnabled(False)
            self.combo_layers.setEnabled(False)
            
        layout.addWidget(btn_container)
        self.combo_layers.setEnabled(False)

        if self.preselect_idx >= 0:
            self.combo_layers.setCurrentIndex(self.preselect_idx)
            self.chk_append.setChecked(True)

        self.input_attribute.setFocus()

    def eventFilter(self, obj, event):
        if obj is self.input_attribute and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab:
                self._open_tag_picker()
                return True
        return super().eventFilter(obj, event)

    def _open_tag_picker(self):
        picker = QuickTagPicker(self.tag_groups, self)
        if picker.exec():
            self.selected_tags = picker.get_selected_tags()
            self.lbl_tags_value.setText(', '.join(self.selected_tags) if self.selected_tags else tr('(none)'))

    def _toggle_append_mode(self):
        is_appending = self.chk_append.isChecked()
        self.combo_layers.setEnabled(is_appending)
        self.lbl_new_name.setEnabled(not is_appending)
        self.input_layer_name.setEnabled(not is_appending)

    def request_layer_info(self):
        exec_result = self.exec()
        return (
            self.input_layer_name.text(),
            self.input_attribute.text(),
            ', '.join(self.selected_tags),
            self.chk_append.isChecked(),
            self.combo_layers.currentIndex(),
            self.available_layers,
            exec_result == QDialog.DialogCode.Accepted
        )