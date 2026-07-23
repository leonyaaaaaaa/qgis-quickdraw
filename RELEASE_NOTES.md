# quickdraw Tools — v2.1.0

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

# quickdraw Tools — v2.0.0

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

