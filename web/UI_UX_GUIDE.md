# RAFTBOUND A10 — UI/UX Style Guide & Acceptance Checklist

Reference: [Roblox Creator Docs — UI and UX design](https://github.com/Roblox/creator-docs/blob/main/content/en-us/production/game-design/ui-ux-design.md).

This document adapts **principles**, not Roblox-branded graphics or copyrighted interface assets, to RAFTBOUND's desktop-first 3D ocean survival game.

## Player goals and flows

1. **Collect**: see debris in unobstructed viewport → crosshair changes when targetable → SPACE/click throws net → toast confirms salvage or a miss → hotbar quantity updates.
2. **Survive**: inspect health/food/water at top left → use hotbar slot 1/2 or inventory → see stat value and confirmation update. Alerts use red only when below 25%.
3. **Craft**: Q or Craft button → select All/Build/Survival/Farming/Tools → read the purpose and resource affordability → craft or clearly see disabled state → toast confirms → inventory synchronizes.
4. **Inventory**: Tab/Bag button → 4-column resource grid → use food/water directly → ESC, X, or backdrop closes. Raw materials remain non-clickable so the action is never deceptive.
5. **Pause / Settings**: ESC → Continue/Restart, Settings or Controls → change quality, camera or performance overlay → Resume. Save is invoked on pause.

## Design principles mapped to UI

- **Prioritization**: vital bars, current quest, aiming and quick actions are always visible; full inventory and recipes stay hidden until requested. Story/copy is not placed in the targeting zone.
- **Attention**: gold means primary action/affordable item, cyan means water, orange means food, coral means health/warning, green means ready/success. Motion and toasts are brief; avoid constant HUD animation.
- **Visual language**: icon + text + current numeric value always travel together; game-critical status never uses color alone.
- **Conventions**: ESC closes the most recent overlay, X closes a panel, disabled crafting is gray and shows material deficits, 1/2 consume provisions, Tab inventory, Q crafting, Space net, WASD movement.
- **Consistency**: repeated corners/radii, focus rings, semantic colors, font scale, buttons, headers and cost chips across panels.
- **Feedback**: target crosshair change, impact toast, inventory count change, deficit costs, quest progress, percentage in settings.
- **Low-friction UX**: opening crafting requires one action; crafting an affordable recipe requires one additional click; overlay navigation is reversible and never stacks more than one drawer.

## Interaction details

- HUD is pointer-events none except interactive buttons, so it doesn't intercept canvas input.
- Drawers suspend gameplay simulation and reset held movement keys, preventing shark damage or accidental throwing while reading recipes.
- Desktop primary target: 1440×900; additional 1365×768 and narrow 390×844 layout coverage.
- Escape order: active drawer → close drawer; otherwise pause game → resume game. Tab and Q swap/close relevant drawers.
- Menus use labelled dialog sections, focus-visible controls, accessible text in buttons and a polite toast live region.
- Reduced-motion media query removes animations; keep keyboard access and sufficient type size at desktop resolution.

## Acceptance gates

| Criterion | How to validate |
|---|---|
| TypeScript compiles | `npm run build` in `web/` |
| WebGL scene still loads assets | A10 real browser smoke checks `13/13 GLB` and WebGL2 |
| Survival interactions remain usable | A08 Node regression tests |
| Inventory, crafting, filters work | Playwright tests interactions and counts |
| No HUD obstruction on desktop/mobile | Browser screenshots at 1365×768 and 390×844 |
| Settings/buttons not decorative | Browser tests exercise quality, filter, close, pause |
| Art direction / performance production-grade | **Not signed off** until actual playtest and hardware FPS |

## Assets and visual tokens

- Palette: deep ocean slate (`#0b2530`), sea-glass cyan (`#72cce5`), rope gold (`#f0c374`), health coral (`#fc796d`).
- Surfaces: frosted/translucent panels with dark fallback for low-contrast ocean scenes.
- Typeface: native system fonts only; no remote font/CDN dependency.
- Icons: first-party inline SVG symbols and existing game item emoji. Replace item emoji with licensed item icon atlas during visual-polish phase.

A10 does not claim that these design decisions are Roblox-specific APIs; Roblox's article is used as a cross-platform design reference.
