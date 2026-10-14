---
name: improve-ux-motion
description: Motion rules for UI animation with opacity and transform. Use when writing, reviewing or tuning UI animations: enter and exit transitions, panels, menus and modals, crossfades, icon or state swaps, staggered lists, layout morphs, press and hover feedback.
---

Every UI animation has two **phases**, each with its own start, duration and curve:

- The **move**: any transform (translate, scale, size, clip). It carries the motion.
- The **fade**: opacity or color. It assists the move by hiding frames the eye should not track. It never carries the motion alone.

The **climax** of a move is the moment it starts slowing down after its fastest part. Fades are timed against the climax.

**Mass** is how heavy a surface reads: its size and its contrast against what is behind it. Mass sets duration. Heavier surfaces move slower so the eye can follow them.

## Workflow

1. **Classify** each animated element as one of: enter, exit, crossfade, swap, morph or feedback.
2. **Split** it into a move and a fade. Time each one from the section for its class.
3. **Weigh** it. Set durations from its mass, and use the fade table below.
4. **Stage** it. The main subject appears first and lasts longest. Secondary elements get simpler motion.
5. **Spam-test** it. Trigger the animation repeatedly and quickly, and look for eaten states, missing elements and cuts.

The work is done when every animated element has a class, a separately timed move and fade, scoped tokens if needed, and passes the spam test.

## Principles

- **Anticipation**: a major action starts with a smaller preparatory movement. Momentum builds from a source: a user interaction, or the end of another animation.
- **Weight and inertia**: mass gives a surface inertia. Use that inertia to set other elements in motion.
- **Staging**: motion pulls attention to the most important part of the layout.
- **Arcs**: living and moving objects follow curved paths.

## Fade timing

The curve is always the native CSS `ease`. The move uses the curves in Move timing.

- **0.2s**: Small changes: button hover text and background, label state changes
- **0.3s**: Crossfades between small elements (icon swaps); closing small and medium surfaces
- **0.4s**: Opening panels, menus and modals; color change on medium and large surfaces; closing large surfaces
- **0.5s**: Opening and closing very large surfaces (low-contrast backdrops); slow-motion elements
- **0.7-1s**: High-contrast backdrops

Low-contrast color changes take the shorter end of the range, because slow low-contrast fades produce color banding.

## Move timing

- **`ease`**: native CSS `ease`. Fades only (see Fade timing).
- **ease-out**: `cubic-bezier(0.2, 0.4, 0.1, 0.98)`. Enters: the element arrives fast and settles into place.
- **ease-in-out**: `cubic-bezier(0.4, 0.05, 0.2, 1)`. Moves between two on-screen states (morphs, resizes, repositioning) and exits, which start slowly and accelerate away.

The move is always longer than its fade, and its duration grows with mass.

### Readable content

Content the user must read right away settles fast: short travel, short duration, so it is at rest when the eye starts reading. Text in motion is hard to read. A long, slow slide keeps it moving after the reader has started. This applies to labels, messages, toasts, notifications, and any text that appears in response to an action.

Readability outranks mass: a large surface that carries text to read now still settles fast. Its weight can come through the fade and the background layer instead of a long move.

## Enter

- The fade starts with the move, softly, and ends at the climax. This hides the first frames of the move.
- The fade is shorter than the move, so the element is fully opaque before the move slows down.
- After the climax, the move continues alone at full opacity. Its slow end stays visible and clean.

### Stagger

Stagger siblings or nested items only in predictable grid or list layouts with several rows or columns. In unpredictable layouts, staggering adds noise that misleads the eye.

- Each item gets its own delay: `delay + n × step`.
- For a fixed item count, space the delays along the CSS `ease` curve instead of evenly. This gives the sequence weight.
- For feeds that change or run off screen, keep the delays linear.
- Each item's fade ends at the climax of its own move.

## Exit

Exits are quicker and subtler than enters, but they are always animated. A fade-out is at most as long as the fade-in of the same element.

- **Default** (the element leaves and nothing takes its place):
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
- **Dismiss on select**: when a dialog closes right after a click, blink the chosen option over 0.4s total: unselected → selected → unselected → selected.
- **Hover**: put hover styles inside `@media (hover: hover)` so touch devices skip them.

## Implementation

- Animate with the Web Animations API (`element.animate`) or use libraries that use them (Framer Motion, Anime.js).
- Animate `opacity` and `transform`. They run on the GPU.
- Put the background (ground, tint, blur) on its own layer, separate from the content:
    - The background resizes and fades on its own.
    - The content keeps its own clip and its own fade.
    - This reduces repaints.
- Put slow transform layers on the GPU with `will-change: transform`.
- Smooth moving or scaling layers with a rotation too small to see: `rotate(0.02deg)`.
