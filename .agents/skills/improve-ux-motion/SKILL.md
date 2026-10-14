---
name: improve-ux-motion
description: Motion taste for UI animation with opacity and transform; overrides curves, durations and timing from other animation skills. Use when writing, reviewing or tuning UI animations: enter and exit transitions, dropdowns, panels, menus and modals, crossfades, icon or state swaps, staggered lists, layout morphs, press and hover feedback.
---

Every UI animation has two **phases**, each with its own start, duration and curve:

- The **move**: any transform (translate, scale, size, clip). It carries the motion.
- The **fade**: opacity or color. It assists the move by hiding frames the eye should not track. It never carries the motion alone.

The **climax** of a move is the moment it starts slowing down after its fastest part. Fades are timed against the climax.

Two axes set timing:

- **Mass** is how heavy a surface reads: its size and its contrast. Heavier surfaces move slower so the eye can follow them.
- **Frequency** is how often the user triggers the animation. The more often it plays, the faster and lighter it gets, while it still shows where the new state comes from.

When mass and frequency disagree, frequency wins.

## Precedence

This skill owns motion taste: phase timing, curves, durations, scales, travel and staging. Other animation skills (`animate`, `animate-expo`, their recipes, `animation-performance`) supply tooling, code structure, gestures, springs and performance diagnosis. When their values differ from the ones here, apply the values here. For example: one shared duration for opacity and transform, their own cubic-beziers, a blanket 300ms cap, or a "no animation" gate for frequent actions. Translate their recipes into these rules rather than copying their timing.

## Workflow

1. **Classify** each animated element as one of: enter, exit, crossfade, swap, morph or feedback.
2. **Gauge** its frequency tier (see Frequency).
3. **Split** it into a move and a fade. Time each one from the section for its class.
4. **Weigh** it. Take durations from its frequency tier, and from mass where the tier defers to mass.
5. **Anchor** it. Set where it comes from and where it goes (see Origin).
6. **Stage** it. The main subject appears first and lasts longest. Secondary elements get simpler motion.
7. **Spam-test** it. Trigger it repeatedly, reverse it mid-flight, and look for eaten states, missing elements, and motion that restarts from zero.

The work is done when every animated element has a class, scoped tokens if needed, a frequency tier, an origin, a separately timed move and fade, and passes the spam test.

## Principles

- **Anticipation**: a major action starts with a smaller preparatory movement. Momentum builds from a source: a user interaction, or the end of another animation.
- **Weight and inertia**: mass gives a surface inertia. Use that inertia to set other elements in motion.
- **Staging**: motion pulls attention to the most important part of the layout.
- **Arcs**: living and moving objects follow curved paths.
- **Continuity**: every new state visibly comes from its cause, so the user never wonders where it came from.

## Frequency

- **Constant**: keyboard-driven actions, a command palette opened by shortcut, arrow-key navigation through a list.
    - Fade only, 0.1s `ease`. No move.
    - The change is effectively instant; the fade only softens the cut.
- **Frequent**: dropdowns, selects, context menus, tooltips, popovers, tabs, accordions, toggles, inline validation.
    - Enter: fade 0.15s, move 0.25s ease-out, short travel (scale from 0.97, or 8px at most), starting from the origin.
    - Exit: fade 0.18s with no delay and no move.
    - Mass only decides the travel distance, not the duration.
- **Occasional**: modals, drawers, side panels, sheets, toasts, page-level menus.
    - Timing follows mass and the Fade timing table.
- **Rare**: onboarding, first-run, success states, empty states, marketing pages.
    - Full mass timing. Staging, stagger and anticipation have room here, and motion may run slower.

**Warm state**: when the user moves between siblings of an open frequent element (tooltips along a toolbar, menus in a menu bar), swap the content in place, instantly. Run the full enter only on the first open.

**Input never waits for motion.** An entering element accepts clicks and keys from its first frame. Stagger and staging never block interaction.

## Mass

- **Small**: icons, buttons, checkboxes, radios, toggles, chips and tags, badges, tooltips, single labels.
- **Medium**: cards, dropdown menus, popovers, toasts, inputs and field groups, list rows, small dialogs.
- **Large**: modals, side panels and drawers, bottom sheets, full-width navigation menus, page sections, images and slides that fill the screen.
- **Very large**: backdrops and overlays covering the whole page. Their duration depends on contrast: 0.5s when low, 0.7–1s when high (see Fade timing).

Contrast decides between two steps: an element with high contrast against its background reads one step heavier.

## Fade timing

The curve is always the native CSS `ease`. The move uses the curves in Move timing.

- **0.2s**: Small changes: button hover text and background, label state changes
- **0.3s**: Crossfades between small elements (icon swaps); closing small and medium surfaces
- **0.4s**: Opening panels and modals; color change on medium and large surfaces; closing large surfaces
- **0.5s**: Opening and closing very large surfaces (low-contrast backdrops); slow-motion elements
- **0.7-1s**: High-contrast backdrops

Low-contrast color changes take the shorter end of the range, because slow low-contrast fades produce color banding.

## Move timing

- **`ease`**: native CSS `ease`. Use for very fast moves (press, repositionning).
- **ease-out**: `cubic-bezier(0.2, 0.4, 0.1, 0.98)`. Enters: the element arrives fast and settles into place.
- **ease-in-out**: `cubic-bezier(0.4, 0.05, 0.2, 1)`. Moves between two on-screen states (morphs, resizes, repositioning) and exits, which start slowly and accelerate away.

The move is always longer than its fade, and its duration grows with mass.

Gestures where a finger drives the value use springs from the other skills.

### Readable content

Content the user must read right away settles fast: short travel, short duration, so it is at rest when the eye starts reading. Text in motion is hard to read. A long, slow slide keeps it moving after the reader has started. This applies to labels, messages, toasts, notifications, and any text that appears in response to an action.

Readability outranks mass: a large surface that carries text to read now still settles fast. Its weight can come through the fade and the background layer instead of a long move.

## Origin

- Anchored elements (dropdowns, popovers, menus, tooltips, context menus) grow out of their trigger: set `transform-origin` at the trigger, on the side facing it.
- Modals and other unanchored surfaces stay centered.
- Elements that enter from an edge (drawers, sheets, toasts) travel from that edge.
- Exits retrace the entry path in reverse. An element that came from the trigger shrinks back toward it.
- Entering scales start between 0.9 and 0.98, depending on mass and frequency. Swaps keep their own scales (see Swap).

## Enter

- The fade starts with the move, softly, and ends at the climax. This hides the first frames of the move.
- The fade is shorter than the move, so the element is fully opaque before the move slows down.
- After the climax, the move continues alone at full opacity. Its slow end stays visible and clean.

### Stagger

Stagger siblings or nested items only in predictable grid or list layouts with several rows or columns, and only at occasional and rare frequency. In unpredictable layouts, staggering adds noise that misleads the eye.

- Each item gets its own delay: `delay + n × step`.
- For a fixed item count, space the delays along the CSS `ease` curve instead of evenly. This gives the sequence weight.
- For feeds that change or run off screen, keep the delays linear.
- Each item's fade ends at the climax of its own move.

## Exit

Exits are quicker and subtler than enters, but they are always animated. A fade-out is at most as long as the fade-in of the same element.

- **Default** (the element leaves and nothing takes its place):
    - The move starts at full opacity.
    - The fade starts as the move accelerates, with a delay of 0-0.1s.
    - The fade ends just before the move does. The slow tail of an exit leaves ghost frames that catch the eye, and the fade hides them.
- **Returning focus** (a panel, menu or overlay closing over the page): the fade starts with no delay, so the eye goes straight back to the main content.
- **Staggered children** inside a closing container fade out together, in place, with no transform.

## Crossfade

Use for slides, images and surfaces that fill the screen or container.

- The leaving item stays in place, with no transform.
- The leaving item fades out after a short delay, once the entering item is almost opaque. This keeps the frame covered and avoids a dark frame between two half-transparent images.
- Coverage check: `entering + (1 − entering) × leaving` stays near 1 for the whole change.

## Swap

Use for icons, labels, design system atoms and molecules, field groups that change with a mode, and page transitions. A swap signals a state change and guides the eye to the new state.

- Run it in sequence: fade out the old element, then animate in the new one. One thing changes at a time. A crossfade here changes everything at once and misleads the eye.
- Optionally pair it with a light scale-down so both elements exchange in one motion: 0.65 for small elements, 0.85 for medium, 0.92 for large.

## Morph

Keep the container and swap the content inside it, animating the container's size to fit. This reads better than replacing a container with an identical-looking one.

## Feedback

- **Press**: `75ms ease`, so the action feels immediate.
- **Release**: 0.35-0.5s back to rest. The slower release conveys weight and the result of the action.
- **Dismiss on select**: when a dialog closes right after a click, blink the chosen option over 0.3s total: unselected → selected → unselected → selected.
- **Hover**: put hover styles inside `@media (hover: hover)` so touch devices skip them.

## Interruption

- An interrupted animation continues from its current on-screen value toward the new target. Retarget it; restarting from its first frame makes the element jump.
- Reversing mid-flight (closing a dropdown while it opens) runs the exit from where the element is, at the exit's timing.
- Anything the user can trigger twice in a second retargets this way.

## Reduced motion

Under `prefers-reduced-motion: reduce`, keep the fades and color changes that explain a state change, and drop moves: translation, scale, travel and stagger. Fade timing stays the same.

## Implementation

- Animate with the Web Animations API (`element.animate`).
- Animate `opacity` and `transform` by default. `clip-path` is allowed for reveals. Container size is allowed for morphs only.
- Name each animated property explicitly. Never use `transition: all`.
- Put the background (ground, tint, blur) on its own layer, separate from the content:
    - The background resizes and fades on its own.
    - The content keeps its own clip and its own fade.
    - This reduces repaints.
- Put slow transform layers on the GPU with `will-change: transform`.
- Smooth moving or scaling layers with a rotation too small to see: `rotate(0.02deg)`.
