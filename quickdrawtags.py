"""
quickdraw tools - Quick Tags
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
            "groups in this order (arrow keys \u2190/\u2192 also move between groups; Enter "
            "finishes and applies everything picked so far; Esc cancels). Numeric groups "
            "auto-number tags 1-9, 0 (10th) in the order typed below (comma-separated "
            "labels), e.g. \"Rockchip, Soil anomaly, Outcrop\". Letter groups use keys you "
            "choose yourself, comma-separated key:Label pairs, e.g. \"A:Au, C:Cu, S:As, "
            "g:Ag\". Uncheck \"Case sensitive\" for a letter group if you want 'g' and 'G' to "
            "mean the same key. Uncheck \"Multi-tag\" for a group if only one tag should be "
            "pickable there (picking one then immediately moves to the next group)."
        ))
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(MAX_GROUPS, 5)
        self.table.setHorizontalHeaderLabels(
            [tr('Group name'), tr('Mode'), tr('Case sensitive'), tr('Multi-tag'), tr('Tags')]
        )
        self.mode_boxes = []
        self.case_boxes = []
        self.multi_boxes = []
        for row, grp in enumerate(groups):
            self.table.setItem(row, 0, QTableWidgetItem(grp.get('name', '')))

            combo = QComboBox()
            combo.addItems([tr('Numeric (1-9, 0)'), tr('Letter (custom keys)')])
            combo.setCurrentIndex(0 if grp.get('mode', 'numeric') == 'numeric' else 1)
            self.table.setCellWidget(row, 1, combo)
            self.mode_boxes.append(combo)

            self.table.setCellWidget(row, 2, self._centered_checkbox(grp.get('case_sensitive', True)))
            self.case_boxes.append(self.table.cellWidget(row, 2).findChild(QCheckBox))

            self.table.setCellWidget(row, 3, self._centered_checkbox(grp.get('multi_tag', True)))
            self.multi_boxes.append(self.table.cellWidget(row, 3).findChild(QCheckBox))

            self.table.setItem(row, 4, QTableWidgetItem(self._tags_to_text(grp)))

        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
                                    Qt.Orientation.Horizontal, self)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    @staticmethod
    def _centered_checkbox(checked):
        wrap = QWidget()
        wrap_layout = QHBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chk = QCheckBox()
        chk.setChecked(checked)
        wrap_layout.addWidget(chk)
        return wrap

    @staticmethod
    def _tags_to_text(grp):
        if grp.get('mode', 'numeric') == 'letter':
            return ', '.join(f"{t['key']}:{t['label']}" for t in grp.get('tags', []))
        return ', '.join(t['label'] for t in grp.get('tags', []))

    def get_tag_groups(self):
        result = []
        for row in range(MAX_GROUPS):
            name_item = self.table.item(row, 0)
            tags_item = self.table.item(row, 4)
            name = name_item.text().strip() if name_item else ''
            raw_tags = tags_item.text().strip() if tags_item else ''
            mode = 'numeric' if self.mode_boxes[row].currentIndex() == 0 else 'letter'
            case_sensitive = self.case_boxes[row].isChecked()
            multi_tag = self.multi_boxes[row].isChecked()

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
                result.append({
                    'name': name, 'mode': mode, 'case_sensitive': case_sensitive,
                    'multi_tag': multi_tag, 'tags': tags
                })
        return result


class QuickTagPicker(QDialog):
    """Keyboard-only popup for picking tags across configured groups.

    Navigation: Right/Down/Tab move to the next group (or finish, if
    already on the last one); Left/Up move to the previous group; Enter
    finishes and applies everything picked so far, from any group; Esc
    cancels the whole picker.

    Selecting: press a tag's key to add it. In a "multi-tag" group this can
    be repeated to add more than one tag from that same group (e.g. Au, As,
    Ag together); in a single-tag group, picking one tag immediately moves
    on to the next group.

    Key matching prefers the OS-native virtual key code (nativeVirtualKey())
    where it looks like a Windows VK_A..VK_Z/VK_0..VK_9 code, since Windows
    keeps those assigned to the same physical keys no matter which keyboard
    layout/language is active. Falls back to Qt's own key() elsewhere.
    """

    _LETTER_KEYS = {chr(c): getattr(Qt.Key, f'Key_{chr(c)}') for c in range(ord('A'), ord('Z') + 1)}
    _DIGIT_KEYS = {str(d): getattr(Qt.Key, f'Key_{d}') for d in range(10)}

    def __init__(self, tag_groups, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Quick Tags'))
        self.setMinimumWidth(340)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tag_groups = tag_groups
        self.idx = 0
        self.selections = [[] for _ in tag_groups]

        self.lbl_display = QLabel()
        self.lbl_display.setWordWrap(True)
        self.lbl_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout = QVBoxLayout(self)
        layout.addWidget(self.lbl_display)

        self._render_current()

    def showEvent(self, event):
        super().showEvent(event)
        # Force real keyboard focus onto this dialog. Without this, key
        # presses can end up going to whatever triggered the picker instead
        # of the picker itself, which looks exactly like "keys don't work".
        self.activateWindow()
        self.raise_()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    @staticmethod
    def _typed_is_upper(event):
        text = event.text()
        if text and text.isalpha() and text.isascii():
            return text.isupper()
        return bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

    @staticmethod
    def _physical_char(event):
        """Best-effort layout-independent identification of which A-Z/0-9
        key was physically pressed. Prefers the native virtual key code:
        on Windows, VK_A..VK_Z (0x41-0x5A) and VK_0..VK_9 (0x30-0x39) stay
        pinned to the same physical keys regardless of the active keyboard
        layout/language, which Qt's own key() does not always guarantee.
        Falls back to Qt's key() if the native code isn't in that range
        (e.g. on other platforms)."""
        native = event.nativeVirtualKey()
        if 0x41 <= native <= 0x5A:
            return chr(native)
        if 0x30 <= native <= 0x39:
            return chr(native)

        key = event.key()
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(ord('A') + (key - Qt.Key.Key_A))
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return chr(ord('0') + (key - Qt.Key.Key_0))
        return None

    def _matches(self, tag, event, grp):
        key_char = tag['key']
        physical = self._physical_char(event)
        if physical is None:
            return False

        if grp.get('mode') == 'letter':
            if physical.upper() != key_char.upper():
                return False
            if grp.get('case_sensitive', True):
                return self._typed_is_upper(event) == key_char.isupper()
            return True
        return physical == key_char

    def _render_current(self):
        grp = self.tag_groups[self.idx]
        mode_hint = tr('pick one') if not grp.get('multi_tag', True) else tr('pick any number')
        lines = [tr('Group {0}/{1}: {2} ({3})').format(self.idx + 1, len(self.tag_groups), grp['name'], mode_hint)]
        for t in grp['tags']:
            lines.append(f"  {t['key']}: {t['label']}")
        lines.append('')
        chosen = self.selections[self.idx]
        lines.append(tr('Selected in this group: {0}').format(', '.join(chosen) if chosen else tr('(none)')))
        all_selected = self.get_selected_tags()
        lines.append(tr('All tags selected so far: {0}').format(', '.join(all_selected) if all_selected else tr('(none)')))
        lines.append('')
        lines.append(tr('(\u2190/\u2192 = switch group, Enter = finish, Esc = cancel)'))
        self.lbl_display.setText('\n'.join(lines))

    def _advance(self):
        if self.idx >= len(self.tag_groups) - 1:
            self.accept()
        else:
            self.idx += 1
            self._render_current()

    def _go_back(self):
        if self.idx > 0:
            self.idx -= 1
            self._render_current()

    def keyPressEvent(self, event):
        key = event.key()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
            return
        if key == Qt.Key.Key_Escape:
            self.reject()
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Tab):
            self._advance()
            return
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._go_back()
            return

        grp = self.tag_groups[self.idx]
        for t in grp['tags']:
            if self._matches(t, event, grp):
                if t['label'] not in self.selections[self.idx]:
                    self.selections[self.idx].append(t['label'])
                if grp.get('multi_tag', True):
                    self._render_current()
                else:
                    self._advance()
                return

    def get_selected_tags(self):
        flat = []
        for group_tags in self.selections:
            flat.extend(group_tags)
        return flat
