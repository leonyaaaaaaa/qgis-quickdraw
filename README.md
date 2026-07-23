# quickdraw tools

**License:** [GNU GPL v3](LICENSE)
**Author:** leonya ivanchikov

quickdraw tools is a QGIS plugin that makes on-the-fly digitizing fast.
It adds a toolbar of simple drawing tools — circle, rectangle, line, polygon,
point (with an optional X/Y or DMS coordinate entry) and buffer — and saves
what you draw straight into memory layers, without the usual layer-creation
dialogs getting in the way.

## Features

- **Draw Circle, Rectangle, Line, Polygon, Point** — click on the map, done.
- **Point by coordinates** — enter X/Y directly, or switch to DMS
  (Degrees, Minutes, Seconds) mode.
- **Buffer** — select a feature on the map and buffer it by a given distance.
- **New or existing layer** — add each shape to a brand-new memory layer or
  append it to a matching one you already created.
- **Persistent settings** — fill color, stroke color, stroke width, the
  attribute field name and the "remember last layer" option are saved with
  `QSettings` and survive a QGIS restart.
- **Remember last layer per shape type** — optional, toggle it in Settings.

## Settings

Open **quickdraw → Settings** to configure:

| Setting | Description |
|---|---|
| Fill Color | Color (and alpha) used to fill polygons/points |
| Stroke Color | Color (and alpha) used for outlines/lines |
| Stroke Width | Outline thickness, 1–15 |
| Remember last layer for each shape type | Reuse the last layer you drew into for that shape |
| Attribute field name | Name of the text attribute stored with each shape |
| Reset Settings | Restore all of the above to their defaults |

## Installation

1. Download or clone this repository.
2. Copy the folder into your QGIS plugins directory, or zip it and install
   it via **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Enable **quickdraw tools** in the Plugins panel.

## License

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option)
any later version. See [LICENSE](LICENSE) for the full text.
