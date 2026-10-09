# Vendored Hyprune logo

Copied unchanged from the meta repository `hyprune/hyprune`, folder `brand/`, at
commit **352e777** ("Add the brand folder: approved logo SVGs, exports and usage
rules"). Hashes are the ones listed in that commit's `brand/SHA256SUMS`.

| Vendored file | Source path | SHA-256 |
|---|---|---|
| `monogram-16-mono.svg` | `brand/svg/monogram-16-mono.svg` | `f9363a4ab406bd2badd40368dba7ed4f132848492b3d6ab76064bd63f7006cfd` |
| `monogram-32-mono.svg` | `brand/svg/monogram-32-mono.svg` | `52a43c6a3dc6c604a2f8514c3f993024115ce1c83a3fca63a32c0300dad6fe60` |
| `primary-optical-mono.svg` | `brand/svg/primary-optical-mono.svg` | `b34fa4269ee72b02cb0765d96140ec0daee59dbd461f9360b2a43e0a26d27116` |
| `primary-mono.svg` | `brand/svg/primary-mono.svg` | `b386022a859caee17804d3230c6f9782d3a10f3bc801babb6208500a5b266d88` |

"Hyprune logo by Hyprune contributors, CC-BY-4.0"
(<https://creativecommons.org/licenses/by/4.0/>). No trademark rights are granted.

## How the shell draws it

`BrandMarks.js` is generated from these SVGs by `dev/sync-brand.py`. It copies
each element's geometry verbatim: path `d` strings and stroke widths, and the
ellipse/rect/circle attributes. `../BrandMark.qml` draws that table with
QtQuick.Shapes (CurveRenderer) in a bound theme colour (default `Tokens.accent`),
which stands in for `currentColor`. Don't edit `BrandMarks.js` by hand. After
updating a vendored SVG, rerun the generator and update the table above.
`tests/test_brand.py` checks all of this.

Drawing choice follows the brand size rule, by rendered physical pixels (logical
size × window device-pixel ratio × ancestor `scale`, e.g. the Director's uiScale):

| Physical size | Drawing |
|---|---|
| 16 px (and below) | `monogram-16-mono.svg` |
| 17–47 px | `monogram-32-mono.svg` |
| 48–95 px | `primary-optical-mono.svg` |
| 96 px and up | `primary-mono.svg` |

The Bold one-ink drawings aren't vendored. They are for use beside the
path-lettered `hyprune` wordmark, and the shell shows the product name as text.

Clear space: the room drawings' viewBox already holds at least 37 source units
around the ink (the rule asks for 32). The shell aligns the ink, not the box, to
the content edge, and keeps the full box free of other content.
