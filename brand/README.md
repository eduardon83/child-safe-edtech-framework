# CSEF brand kit

The CSEF mark is a house built from four blocks, with a child safe inside.
Each block is one group that builds it: developers, designers, educators and companies.
The house does not lock the child in. It is a safe place built together.

Every file comes in two versions:

- `on-light`: for white or light backgrounds
- `on-dark`: for navy, black or dark-mode backgrounds

All SVGs have the text converted to outlines, so they need no fonts installed.

## What is in here

| Folder | Files | Use |
|---|---|---|
| `svg/` | `csef-mark-*`, `csef-mark-small-*` | Mark only. Use `small` below 32 px. |
| `svg/` | `csef-lockup-*`, `csef-lockup-compact-*` | Mark plus name, with or without "Child-Safe EdTech Framework". |
| `svg/` | `csef-icon-*` | Square app icon with background. |
| `png/` | marks at 64 to 1024 px, lockups, icons | For tools that do not take SVG. |
| `github/` | `csef-banner-*.png` | README header (transparent background). |
| `github/` | `csef-social-preview-*.png` | Repository social preview, 1280 × 640. |
| `web/` | `favicon.ico`, `favicon.svg`, `apple-touch-icon.png`, `icon-192/512.png`, `site.webmanifest` | Website icons. `favicon.svg` switches to dark mode by itself. |
| `tokens/` | `csef-colors.css`, `csef-colors.json` | Colours and fonts as variables. |

## GitHub repository

1. Copy `github/` into the repo, for example as `.github/brand/`.
2. Put this at the top of `README.md`. GitHub shows the right banner for light or dark mode:

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/brand/csef-banner-on-dark.png">
    <img alt="CSEF, Child-Safe EdTech Framework. Build safe things for kids. Together." src=".github/brand/csef-banner-on-light.png" width="640">
  </picture>
</p>
```

3. Social preview: Settings › General › Social preview › upload `csef-social-preview-on-light.png` (or the dark one).
4. Organisation avatar: `png/csef-icon-on-light-512.png`.

## Website

Copy the files in `web/` to the site root, then add to `<head>`:

```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="stylesheet" href="/csef-colors.css">
```

Logo that follows the visitor's light or dark mode:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/brand/csef-lockup-on-dark.svg">
  <img src="/brand/csef-lockup-on-light.svg" alt="CSEF, Child-Safe EdTech Framework" height="48">
</picture>
```

## Colours

| Name | Light mode | Dark mode | Role |
|---|---|---|---|
| Paper | `#F6F3EC` | text | Background |
| Ink | `#17233F` | background | Text and roof |
| Ink secondary | `#4A5468` | `#B8C0D0` | Secondary text |
| Teal | `#1F8A7A` | `#3FBFA8` | Developers |
| Indigo | `#4A5FC1` | `#8A9BEA` | Designers |
| Sky | `#5DA9DD` | `#5DA9DD` | Educators |
| Lilac | `#9A7AD0` | `#B59BE6` | Companies |
| Coral | `#E2674A` | `#E2674A` | Child (head) |
| Sun | `#F2B441` | `#F2B441` | Child (body) |

Use the role colours for shapes, tags and charts. For body text use Ink or Paper only.

## Fonts

- Display: Space Grotesk, 700 (500 for taglines)
- Body: Inter, 400 and 500

Both are free under the SIL Open Font License, on Google Fonts.

## Rules

- Keep clear space around the mark of at least the height of one block.
- Do not recolour the child, rotate the mark or put it on a busy photo.
- Below 32 px, use `csef-mark-small` (two columns instead of four blocks).

## Licence

The CSEF logo is part of the Child-Safe EdTech Framework, maintained by Kendir Studios.
