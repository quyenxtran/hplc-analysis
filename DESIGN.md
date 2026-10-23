---
version: alpha
name: HPLC workbench
colors:
  primary: "#146a61"
  on-primary: "#ffffff"
  text: "#172b3a"
  muted: "#526675"
  background: "#f4f7f8"
  surface: "#ffffff"
  border: "#b5c5cc"
  warning: "#a33117"
typography:
  body-md:
    fontFamily: system-ui
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: 6px
spacing:
  sm: 8px
  md: 16px
---

## Overview

A local scientific workbench: the chromatogram occupies most of the screen,
with explicit units, reviewed edits, and a separate model-fitting section.

## Colors

Primary teal identifies actions and selected peaks. Dark text sits on white
surfaces. Warning rust identifies errors and fit concerns using text as well as
color. Components use distinct colors plus labels. Signal stays dark; baseline
is dashed. Palette values above are the normative CSS variables.

## Typography

Use installed system fonts. Label every numeric input with its unit. Tables
use tabular numerals. Keep diagnostic messages readable and selectable.

## Layout

Header: dataset, detector, undo/redo/export. Main: graph and residual plot on
the left; Manual edits/Fit components controls on the right. Area tables appear below. Controls
stack below the graph on smaller windows. Keep graph height at least 350px.

## Components

Buttons and form controls use 6px corners, 8px spacing, and visible focus.
Keyboard inputs duplicate draggable handles. Status uses an aria-live region.
Long calculations disable actions and show a busy message. Manual and fitted
areas use distinct tables with window/full-model area labels. Editing clears
stale fits. Browser refresh retains the server session. Closing the server ends
it; exported audits can be restored against their original trace.
