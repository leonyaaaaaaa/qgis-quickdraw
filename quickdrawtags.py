"""
quickdraw Tools - Quick Tags
Configurable tag groups + the keyboard-driven quick tag picker.

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
import json

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QLabel, QTableWidget,
                                 QTableWidgetItem, QComboBox, QCheckBox, QWidget,
                                 QHBoxLayout, QDialogButtonBox)
from .utils import tr

MAX_GROUPS = 10


def load_tag_groups(qsettings):
    raw = qsettings.value("quickdraw/tag_groups", "")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return []


def save_tag_groups(qsettings, tag_groups):
    qsettings.setValue("quickdraw/tag_groups", json.dumps(tag_groups))


class TagGroupsDialog(QDialog):
    """Lets the user define up to 10 tag groups (numeric or letter-keyed)."""

    def __init__(self, tag_groups, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Configure Tag Groups'))
        self.setMinimumSize(580, 420)

        groups = [dict(g) for g in tag_groups][:MAX_GROUPS]
        while len(groups) < MAX_GROUPS:
            groups.append({'name': '', 'mode': 'numeric', 'tags': []})

        layout = QVBoxLayout(self)
        info = QLabel(tr(
            "Set up to 10 tag groups. Pressing Tab in the note field will step through your "
            "groups in this order, one at a time (Tab again skips a group, Enter confirms and "
            "moves on). Numeric groups auto-number tags 1-9, 0 (10th) in the order typed "
            "below (comma-separated labels), e.g. \"Rockchip, Soil anomaly, Outcrop\". Letter "
            "groups use keys you choose yourself, comma-separated key:Label pairs, e.g. "
            "\"A:Au, C:Cu, S:As, g:Ag\". Uncheck \"Case sensitive\" for a letter group if you "
            "want 'g' and 'G' to mean the same key."
        ))
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(MAX_GROUPS, 4)
        self.table.setHorizontalHeaderLabels([tr('Group name'), tr('Mode'), tr('Case sensitive'), tr('Tags')])
        self.mode_boxes = []
        self.case_boxes = []
        for row, grp in enumerate(groups):
            self.table.setItem(row, 0, QTableWidgetItem(grp.get('name', '')))

            combo = QComboBox()
            combo.addItems([tr('Numeric (1-9, 0)'), tr('Letter (custom keys)')])
            combo.setCurrentIndex(0 if grp.get('mode', 'numeric') == 'numeric' else 1)
            self.table.setCellWidget(row, 1, combo)
            self.mode_boxes.append(combo)

            case_wrap = QWidget()
            case_layout = QHBoxLayout(case_wrap)
            case_layout.setContentsMargins(0, 0, 0, 0)
            case_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_case = QCheckBox()
            chk_case.setChecked(grp.get('case_sensitive', True))
            case_layout.addWidget(chk_case)
            self.table.setCellWidget(row, 2, case_wrap)
            self.case_boxes.append(chk_case)

            self.table.setItem(row, 3, QTableWidgetItem(self._tags_to_text(grp)))

        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                                    Qt.Orientation.Horizontal, self)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    @staticmethod
    def _tags_to_text(grp):
        if grp.get('mode', 'numeric') == 'letter':
            return ', '.join(f"{t['key']}:{t['label']}" for t in grp.get('tags', []))
        return ', '.join(t['label'] for t in grp.get('tags', []))

    def get_tag_groups(self):
        result = []
        for row in range(MAX_GROUPS):
            name_item = self.table.item(row, 0)
            tags_item = self.table.item(row, 3)
            name = name_item.text().strip() if name_item else ''
            raw_tags = tags_item.text().strip() if tags_item else ''
            mode = 'numeric' if self.mode_boxes[row].currentIndex() == 0 else 'letter'
            case_sensitive = self.case_boxes[row].isChecked()

            if not name or not raw_tags:
                continue

            tags = []
            if mode == 'numeric':
                labels = [s.strip() for s in raw_tags.split(',') if s.strip()][:MAX_GROUPS]
                for i, label in enumerate(labels):
                    key = str(i + 1) if i < 9 else '0'
                    tags.append({'key': key, 'label': label})
            else:
                for part in raw_tags.split(','):
                    part = part.strip()
                    if ':' not in part:
                        continue
                    key, label = part.split(':', 1)
                    key, label = key.strip(), label.strip()
                    if key and label:
                        tags.append({'key': key, 'label': label})

            if tags:
                result.append({'name': name, 'mode': mode, 'case_sensitive': case_sensitive, 'tags': tags})
        return result


class QuickTagPicker(QDialog):
    """Keyboard-only popup: steps through configured tag groups one at a
    time. In each group, press a tag's key to add it (repeat for more than
    one tag from the same group - handy for e.g. Au, As, Ag together),
    Enter to confirm and move to the next group, Tab to skip the group
    entirely. Finishes automatically after the last group (or on Enter
    there). Esc cancels the whole picker."""

    def __init__(self, tag_groups, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Quick Tags'))
        self.setMinimumWidth(320)
        self.tag_groups = tag_groups
        self.idx = 0
        self.selections = [[] for _ in tag_groups]

        self.lbl_display = QLabel()
        self.lbl_display.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.lbl_display)

        self._render_current()

    def _matches(self, tag, text, grp):
        if grp.get('mode') == 'letter' and not grp.get('case_sensitive', True):
            return text.lower() == tag['key'].lower()
        return text == tag['key']

    def _render_current(self):
        grp = self.tag_groups[self.idx]
        lines = [tr('Group {0}/{1}: {2}').format(self.idx + 1, len(self.tag_groups), grp['name'])]
        for t in grp['tags']:
            lines.append(f"  {t['key']}: {t['label']}")
        lines.append('')
        chosen = self.selections[self.idx]
        lines.append(tr('Selected in this group: {0}').format(', '.join(chosen) if chosen else tr('(none)')))
        lines.append('')
        lines.append(tr('(Enter = confirm & next, Tab = skip group, Esc = cancel)'))
        self.lbl_display.setText('\n'.join(lines))

    def _advance(self):
        if self.idx >= len(self.tag_groups) - 1:
            self.accept()
        else:
            self.idx += 1
            self._render_current()

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
            self._advance()
            return
        if key == Qt.Key.Key_Escape:
            self.reject()
            return

        grp = self.tag_groups[self.idx]
        for t in grp['tags']:
            if self._matches(t, text, grp):
                if t['label'] not in self.selections[self.idx]:
                    self.selections[self.idx].append(t['label'])
                self._render_current()
                return

    def get_selected_tags(self):
        flat = []
        for group_tags in self.selections:
            flat.extend(group_tags)
        return flat
