# Vendored design system

`tokens.css`, `components.css` and `components.js` come from the Richard Wei Finance design system
(claude.ai artifact `8egmdtDmTuvXWNMPgnDEBV`, version 1793235014-ecb9): `project/tokens.css`,
`project/components/bundle.css` (without its Google Fonts `@import`; render.py loads the bundled
fonts instead) and `project/components/bundle.js`. React 18.3.1 UMD builds are included (MIT).

Local patches in `components.js`, each marked `[market-data patch]`:

- `textWidth` counts CJK and full-width characters as a full em (it assumed Latin letters, so
  Chinese labels and legends overlapped).
- `ColumnChart` without an axis scales to the data instead of a nice-tick floor, and no longer
  draws category labels below the SVG when values are negative (they overlapped the source line).
- `BarChart` leaves room for the value label of a bar at zero.

To update: copy the three files again from the design system, re-apply the patches, and render the
demo issue (`python3 -m pipeline.report build --demo`) to check.

`issue.js` is ours: it lays out an issue spec (see `../issue.py`) with these components.
