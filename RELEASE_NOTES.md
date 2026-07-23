# quickdraw tools — v2.3.1

## Bugfix: letters/arrows not registering with a Russian (non-Latin) layout

This turned out to likely be a focus problem, not (only) a layout problem:
the quick tag popup could open without actually grabbing real keyboard
focus, which would make *every* key silently do nothing — letters, digits,
and the arrow keys alike. That matches what you saw. Fixed by forcing
`activateWindow()` / `setFocus()` on the popup as soon as it's shown.

On top of that, letter/digit matching now also checks the OS-native virtual
key code first (falling back to Qt's own key() if that's not available),
since on Windows that native code stays pinned to the same physical key no
matter which keyboard layout/language is active - a more reliable source
than relying on Qt's translation alone.

Also added: every group's page now shows **all** tags picked so far across
every group, not just the current one, so you can see your running total as
you go.

Please test again on your Russian-layout Windows setup — I still can't run
this in a live QGIS session myself, so this is my best fix based on how the
symptoms lined up, not a confirmed reproduction on my end.



## What's new since 2.2.1

- **Backspace to undo a vertex** — while placing multiple clicks for a Line
  or Polygon, pressing **Backspace** now removes the last placed point, same
  as the existing Ctrl+Z shortcut. Both work side by side.

- **metadata.txt cleanup** — filled in the missing version number, fixed a
  typo in the description ("memory& shape" → "memory or shapefile"),
  lowercased the "quickdraw tools" branding in the `about` field, and
  restored the `changelog` entries and feature tags (`shapefile`, `tags`,
  `svg`) that had dropped out of the version you pasted.



## What's new since 2.1.0

- **Layout/language-independent tag keys** — the picker now matches the
  *physical* key you pressed rather than the character your keyboard layout
  produced. Previously, on a non-Latin layout (e.g. Cyrillic), pressing the
  key in the position of "A" could produce a Cyrillic letter instead of "A",
  so it would never match your configured letter tags. Now it's driven by
  key code, so it's consistent no matter what layout is active. Case
  sensitivity (when enabled for a group) is worked out from Shift state /
  the typed character together, so `A` vs `a` still behaves as configured.

- **Append to any matching layer** — the "add to an existing layer" list now
  shows *any* vector layer with the right geometry type and edit support,
  including layers you made yourself (e.g. QGIS's own "New Temporary Scratch
  Layer") or ordinary Shapefiles/GeoPackages already in the project — not
  only layers this plugin created. If the target layer is missing the note
  or Tags field, it's added automatically the first time you append to it.

- **Multi-tag toggle per group** — a new "Multi-tag" checkbox in *Configure
  Tag Groups...*. Checked (default): pick as many tags as you like from that
  group. Unchecked: picking a single tag immediately confirms it and moves
  to the next group — handy for groups where only one value makes sense
  (e.g. a single lithology code).

- **Arrow-key navigation** — Left/Right (or Up/Down) move freely between
  groups without needing to finish one first. Enter now finishes the whole
  picker and applies everything selected so far, from wherever you are;
  Esc still cancels the whole thing.

- Fixed the plugin's own branding to read "quickdraw tools" (lowercase t)
  consistently everywhere.



## What's new since 2.0.0

- **Quick tag flow reworked** — pressing Tab now steps through your
  configured groups **one at a time, in order**. In each group you can:
  - press a tag's key to add it (press more keys to add more tags from the
    *same* group — e.g. `Au, As, Ag` together in one field)
  - press **Enter** to confirm the group and move to the next one
  - press **Tab** to skip the group entirely (no tag added) and move on
  - press **Esc** to cancel the whole picker

  It finishes automatically after the last group (Enter/Tab on the last
  group also finishes it). All tags picked across all groups land in the
  same **Tags** column, comma-separated.

- **Per-group case sensitivity** — each letter-keyed group now has a
  "Case sensitive" checkbox in *Configure Tag Groups...*. Leave it checked
  if `g` and `G` should be different keys (e.g. `g:Ag` vs `G:` something
  else); uncheck it if you want them treated the same.

# quickdraw tools — v2.0.0

## Highlights

- **Icons → SVG**
  Toolbar icons are now loaded directly from `resources/*.svg` on disk
  instead of a compiled Qt resource file. Crisper icons, and no dependency
  on a resource compiler that no longer exists for PyQt6.

- **Qt6 fixes**
  Removed `QDesktopWidget` (deleted in Qt6) in favor of
  `QApplication.primaryScreen()`, and dropped the compiled `resources.py` /
  `resources.qrc` (pyrcc5 output — PyQt6 has no equivalent compiler, so this
  file could never be regenerated going forward). Also cleaned out a couple
  of harmless-but-dead PyQt4-era checks.

- **The shapefile toggle**
  Settings now let you choose whether new layers are created as **Memory
  layer (temporary)** or **Shapefile (on disk)**. Shapefile mode prompts for
  a save location the first time and remembers the folder afterward. Note:
  Shapefile (DBF) field names are capped at 10 characters, so long attribute
  names will be truncated — a warning is shown when this applies.

- **Quick filter (quick tags)**
  Configure up to 10 tag groups in Settings → *Configure Tag Groups...*:
  - **Numeric groups** — list your tags comma-separated (e.g.
    `Rockchip, Soil anomaly, Outcrop`) and they're auto-numbered 1–9, with
    **0** for the 10th.
  - **Letter groups** — define your own key:label pairs (e.g.
    `A:Au, C:Cu, S:As, g:Ag`).

  See the 2.1.0 notes above for the current (reworked) picker flow.

## Compatibility

- `qgisMinimumVersion=3.0`
- `qgisMaximumVersion=4.9.9`

I haven't been able to test this inside actual QGIS 3.x/4.x builds, so please
sanity-check the tag picker and shapefile export on your target QGIS version
before relying on it in the field.

## Notes / caveats

- Layers created with pre-2.0 versions of the plugin won't show up as
  "append to existing layer" targets after upgrading (the matching logic
  moved from sniffing the memory-layer URI to tagging layers with custom
  properties at creation time — which older layers don't have).
- "Reset Settings" resets colors/width/layer format, but intentionally does
  **not** wipe your configured tag groups.

