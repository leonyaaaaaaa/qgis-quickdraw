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
from qgis.PyQt.QtWidgets import (QWidget, QPushButton, QSlider, QLabel, QColorDialog,
                                 QVBoxLayout, QFormLayout, QCheckBox, QLineEdit,
                                 QComboBox, QApplication)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSettings
from .utils import tr
from .quickdrawtags import load_tag_groups, save_tag_groups, TagGroupsDialog

class PluginConfigWindow(QWidget):
    settingsChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr('quickdraw - Settings'))
        self.setMinimumWidth(380)
        self._center_on_screen()
        self.settings = QSettings()

        self.fill_color = QColor(self.settings.value("quickdraw/fill_color", "#643c97ff"))
        self.stroke_color = QColor(self.settings.value("quickdraw/stroke_color", "#ff3c97ff"))
        self.stroke_width = int(self.settings.value("quickdraw/stroke_width", 3))
        self.remember_layer = self.settings.value("quickdraw/remember_layer", "true") == "true"
        self.attr_name = self.settings.value("quickdraw/attr_name", "Note")
        self.layer_format = self.settings.value("quickdraw/layer_format", "memory")
        self.shapefile_dir = self.settings.value("quickdraw/shapefile_dir", "")
        self.tag_groups = load_tag_groups(self.settings)

        self.btn_fill_color = QPushButton(tr('Fill Color'))
        self.btn_fill_color.setStyleSheet(f"background-color: {self.fill_color.name()}")
        self.btn_fill_color.clicked.connect(self._pick_fill_color)
        
        self.slider_fill_alpha = QSlider(Qt.Orientation.Horizontal)
        self.slider_fill_alpha.setRange(0, 255)
        self.slider_fill_alpha.setValue(self.fill_color.alpha())
        self.slider_fill_alpha.valueChanged.connect(self._change_fill_alpha)

        self.btn_stroke_color = QPushButton(tr('Stroke Color'))
        self.btn_stroke_color.setStyleSheet(f"background-color: {self.stroke_color.name()}")
        self.btn_stroke_color.clicked.connect(self._pick_stroke_color)
        
        self.slider_stroke_alpha = QSlider(Qt.Orientation.Horizontal)
        self.slider_stroke_alpha.setRange(0, 255)
        self.slider_stroke_alpha.setValue(self.stroke_color.alpha())
        self.slider_stroke_alpha.valueChanged.connect(self._change_stroke_alpha)

        self.slider_width = QSlider(Qt.Orientation.Horizontal)
        self.slider_width.setRange(1, 15)
        self.slider_width.setValue(self.stroke_width)
        self.slider_width.valueChanged.connect(self._change_width)
        self.lbl_width = QLabel(f"{tr('Stroke Width')}: {self.stroke_width}")

        self.chk_remember = QCheckBox(tr('Remember last layer for each shape type'))
        self.chk_remember.setChecked(self.remember_layer)
        self.chk_remember.toggled.connect(self._change_remember)

        self.combo_layer_format = QComboBox()
        self.combo_layer_format.addItems([tr('Memory layer (temporary)'), tr('Shapefile (on disk)')])
        self.combo_layer_format.setCurrentIndex(0 if self.layer_format == 'memory' else 1)
        self.combo_layer_format.currentIndexChanged.connect(self._change_layer_format)

        self.input_attr = QLineEdit()
        self.input_attr.setText(self.attr_name)
        self.input_attr.textChanged.connect(self._change_attr)

        self.btn_reset = QPushButton(tr('Reset Settings'))
        self.btn_reset.clicked.connect(self._reset_defaults)

        self.btn_tag_groups = QPushButton(tr('Configure Tag Groups...'))
        self.btn_tag_groups.clicked.connect(self._open_tag_groups_dialog)

        layout = QVBoxLayout(self)
        f_layout = QFormLayout()
        f_layout.addRow(self.btn_fill_color, self.slider_fill_alpha)
        f_layout.addRow(self.btn_stroke_color, self.slider_stroke_alpha)
        f_layout.addRow(self.lbl_width, self.slider_width)
        
        layout.addLayout(f_layout)
        layout.addWidget(self.chk_remember)
        layout.addWidget(QLabel(tr('New layers are saved as:')))
        layout.addWidget(self.combo_layer_format)
        layout.addWidget(QLabel(tr('Attribute field name:')))
        layout.addWidget(self.input_attr)
        lbl_hint = QLabel(tr('Note: Shapefile field names are limited to 10 characters.'))
        lbl_hint.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(lbl_hint)
        layout.addWidget(self.btn_tag_groups)
        layout.addWidget(self.btn_reset)

    def _pick_fill_color(self):
        c = QColorDialog.getColor(self.fill_color, self, tr("Select Fill Color"), QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self.fill_color = c
            self.slider_fill_alpha.setValue(c.alpha())
            self.btn_fill_color.setStyleSheet(f"background-color: {c.name()}")
            self._save()

    def _change_fill_alpha(self, v):
        self.fill_color.setAlpha(v)
        self._save()

    def _pick_stroke_color(self):
        c = QColorDialog.getColor(self.stroke_color, self, tr("Select Stroke Color"), QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self.stroke_color = c
            self.slider_stroke_alpha.setValue(c.alpha())
            self.btn_stroke_color.setStyleSheet(f"background-color: {c.name()}")
            self._save()

    def _change_stroke_alpha(self, v):
        self.stroke_color.setAlpha(v)
        self._save()

    def _change_width(self, v):
        self.stroke_width = v
        self.lbl_width.setText(f"{tr('Stroke Width')}: {v}")
        self._save()

    def _change_remember(self, v):
        self.remember_layer = v
        self._save()

    def _change_attr(self, v):
        if v.strip():
            self.attr_name = v.strip()
            self._save()

    def _change_layer_format(self, idx):
        self.layer_format = 'memory' if idx == 0 else 'shapefile'
        self._save()

    def _open_tag_groups_dialog(self):
        dlg = TagGroupsDialog(self.tag_groups, self)
        if dlg.exec():
            self.tag_groups = dlg.get_tag_groups()
            self._save()

    def set_shapefile_dir(self, path):
        self.shapefile_dir = path
        self._save()

    def _save(self):
        self.settings.setValue("quickdraw/fill_color", self.fill_color.name(QColor.NameFormat.HexArgb))
        self.settings.setValue("quickdraw/stroke_color", self.stroke_color.name(QColor.NameFormat.HexArgb))
        self.settings.setValue("quickdraw/stroke_width", self.stroke_width)
        self.settings.setValue("quickdraw/remember_layer", "true" if self.remember_layer else "false")
        self.settings.setValue("quickdraw/attr_name", self.attr_name)
        self.settings.setValue("quickdraw/layer_format", self.layer_format)
        self.settings.setValue("quickdraw/shapefile_dir", self.shapefile_dir)
        save_tag_groups(self.settings, self.tag_groups)
        self.settingsChanged.emit()

    def _reset_defaults(self):
        self.fill_color = QColor(60, 151, 255, 100)
        self.stroke_color = QColor(60, 151, 255, 255)
        self.stroke_width = 3
        self.remember_layer = True
        self.attr_name = "Note"
        self.layer_format = "memory"
        
        self.slider_fill_alpha.setValue(100)
        self.slider_stroke_alpha.setValue(255)
        self.slider_width.setValue(3)
        self.chk_remember.setChecked(True)
        self.input_attr.setText("Note")
        self.combo_layer_format.setCurrentIndex(0)
        self.btn_fill_color.setStyleSheet(f"background-color: {self.fill_color.name()}")
        self.btn_stroke_color.setStyleSheet(f"background-color: {self.stroke_color.name()}")
        self._save()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else self.geometry()
        widget_geom = self.geometry()
        self.move(
            int((screen_geom.width() - widget_geom.width()) / 2),
            int((screen_geom.height() - widget_geom.height()) / 2)
        )

    def closeEvent(self, event):
        event.accept()