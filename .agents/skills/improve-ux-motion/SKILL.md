---
name: improve-ux-motion
description: Motion taste for UI animation with opacity and transform; overrides curves, durations and timing from other animation skills. Use when writing, reviewing or tuning UI animations for enter and exit transitions, dropdowns, panels, menus and modals, crossfades, icon or state swaps, staggered lists, layout morphs, press and hover feedback.
---

Every UI animation has two **phases**, each with its own start, duration and curve:

- The **move**: any transform (translate, scale, size, clip). It carries the motion.
- The **fade**: opacity or color. It assists the move by hiding frames the eye should not track. It never carries the motion alone.

The **climax** of a move is the moment it starts slowing down after its fastest part. Fades are timed against the climax.

Two axes set timing:

- **Mass** is how heavy a surface reads: its size and its contrast. Heavier surfaces move slower so the eye can follow them.
- **Frequency** is how often the user triggers the animation. The more often it plays, the faster and lighter it gets, while it still shows where the new state comes from.

When mass and frequency disagree, frequency wins. Swaps and morphs ignore frequency: mass picks their fast or slow speed (see Swap and Morph layout).

## Precedence

This skill owns motion taste: phase timing, curves, durations, scales, travel and staging. Other animation skills (`animate`, `animate-expo`, their recipes, `animation-performance`) supply tooling, code structure, gestures, springs and performance diagnosis. When their values differ from the ones here, apply the values here. For example: one shared duration for opacity and transform, their own cubic-beziers, a blanket 300ms cap, or a "no animation" gate for frequent actions. Translate their recipes into these rules rather than copying their timing.

## Workflow

1. **Classify** each animated element as one of: enter, exit, crossfade, swap, morph or feedback.
2. **Gauge** its frequency tier (see Frequency).
3. **Split** it into a move and a fade. Time each one from the section for its class.
4. **Weigh** it. Take durations from its frequency tier, and from mass where the tier defers to mass.
5. **Anchor** it. Set where it comes from and where it goes (see Origin).
6. **Stage** it. The main subject appears first and lasts longest. Secondary elements get simpler motion.
7. **Spam-test** it against Interruption. Trigger it repeatedly, reverse it mid-flight, and look for eaten states, missing elements, visible jumps, and entrances that lost their motion.

The work is done when every animated element has a class, a frequency tier, an origin, a separately timed move and fade, and passes the spam test.

## Principles

- **Anticipation**: a major action starts with a smaller preparatory movement. Momentum builds from a source: a user interaction, or the end of another animation.
- **Weight and inertia**: mass gives a surface inertia. Use that inertia to set other elements in motion.
- **Staging**: motion pulls attention to the most important part of the layout.
- **Arcs**: living and moving objects follow curved paths on medium to long distances. Keep short distances linear. Try to avoid making objets go out of bounds.
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
- **Very large**: backdrops and overlays covering the whole page. Their contrast sets the fade duration (see Fade timing).

Contrast shifts the class: an element with high contrast against its background reads one class heavier.

## Fade timing

The curve is always the native CSS `ease` (`cubic-bezier(0.25, 0.1, 0.25, 1)`). The move uses the curves in Move timing.

- **0.2s**: Small changes: button hover text and background, label state changes
- **0.3s**: Closing small and medium surfaces; closing everything else.
- **0.4s**: Opening panels, modals, very large surfaces, low-contrast backdrops, overlapping backdrops; color change on medium and large surfaces.
- **0.7-1s**: High-contrast backdrops; full page layout entrance

Low-contrast color changes take the shorter end of the range, because slow low-contrast fades produce color banding.

## Move timing

- **`ease`**: native CSS `ease`. Very fast moves, such as a press.
- **ease-out**: `cubic-bezier(0.2, 0.4, 0.1, 0.98)`. Enters: the element arrives fast and settles into place.
- **ease-in-out**: `cubic-bezier(0.4, 0.05, 0.2, 1)`. Moves between two on-screen states (resizes, repositioning) and exits, which start slowly and accelerate away.

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
- **Cause**: content brought in by an action carries that action's momentum (see Anticipation, Weight and inertia). The new content travels toward the trigger, pulled in by it: a trigger to the left of the content brings the new content in from the right. When the trigger has a counterpart in the new layout (a button that becomes a close button), morph it into that counterpart (see Morph layout).
- Entering scales start between 0.9 and 0.98, depending on mass and frequency. Swaps keep their own scales (see Swap).

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

A swap only times the exchange: when the old content leaves and when the new content arrives. How the new content enters (move, stagger) follows Enter, and its direction follows Origin.

- Run it in sequence: one thing changes at a time. A crossfade here changes everything at once and misleads the eye.
- Two speeds, picked by the mass of the swapped content:
    - **Fast** (small and medium): old content fades out over 0.15s with no delay; new content starts entering after 0.075s.
    - **Slow** (large and above): old content fades out over 0.35s with no delay; new content starts entering after 0.25s.
- The new content's fade takes its duration from Fade timing, by its mass.
- The overlap is deliberate: the new content starts once the old one is mostly hidden, not fully gone. Starting later leaves an empty beat that stalls the exchange; starting sooner overlaps them into a crossfade.
- Optionally pair it with a light scale-down so both exchange in one motion: 0.65 for small elements, 0.85 for medium, 0.92 for large.

## Morph layout

A morph animates between two layouts of the same place, like smart animate: elements present in both layouts travel to their new place, the container resizes to fit, and the rest swaps. This reads better than replacing a container with an identical-looking one. For each morph:

1. **Match** the elements present in both layouts by role, even when their look changes: a title, an image, the trigger that becomes the new layout's close button. Each one moves and resizes from its old box to its new one. When its look changes, crossfade its visuals inside it during the move.
2. **Homogenize** near-equal sizes: when the two layouts differ by only a few pixels, either give them the same size (shared minimum height, aligned spacing) or set min-height or min-width to the container (stretch to fill, align baseline). A resize of a few pixels reflows and shifts the surrounding page for no visible gain. Use invisible "stable-size" elements in the layout to stabilize two contents of slightly different sizes (text weight, labels).
3. **Resize** the container from its current on-screen size, starting immediately.
4. **Swap** the unmatched content (see Swap). The new content can enter with a move and a stagger.
5. **Clip** the content at the container's edge only when the container has a visible boundary (background, border, outline, shadow). Without one, a clip cuts the content off in mid-air: let the content fade unclipped, while the resize only moves the surrounding layout.

- **Container and matched elements** move together on `cubic-bezier(0.35, 0.05, 0, 0.95)`, at a speed picked by the container's mass: 0.4s for small and medium containers, 0.7s for large ones and above.
- **Content** follows the Swap speed of its own mass.
- **Empty state**: collapsing to nothing keeps the morph's timing, with only the fade-out.
- **Nested morphs** resize their parent along with them, with the same timing.

## Feedback

- **Press**: `75ms ease`, so the action feels immediate.
- **Release**: 0.35-0.5s back to rest. The slower release conveys weight and the result of the action.
- **Dismiss on select**: when a dialog closes right after a click, select and blink the chosen option over 0.3s total: selected → unselected → selected. Run the action immediately on on select, never wait for the blink animation.
- **User select**: Prevent user-select in interactive elements: buttons, links (outside paragraphs), menus, pagers. Images should never be selected anywhere (only the alt text).
- **Native buttons feel**: Listen for `pointerdown`, `mouseleave` and `pointerup`. After a `pointerdown`, if no `mouseleave` was triggered until the `pointerup`, run the action. `mouseleave` is a way to cancel the action. This only applies to action buttons (JS): they should behave as immovable objects and maintain the active state during this behaviour, `mouseleave` remove the active state. Links remain draggable and cancellable on drag.
- **Pointerdown buttons**: The action should run on `pointerdown` for small non-destructive actions that slow down the user : list and graph filters, segmented controls, adding a tab, opening a menu. The click might still be pressed, avoid double fire.
- **Hover**: put hover styles inside `@media (hover: hover)` so touch devices skip them.

### Hit layer

A hover or press that transforms (translate, scale) animates a **visual layer**, while a separate **hit layer** that never moves receives the pointer. This prevents hover jitter: the element sliding out from under the cursor and looping between states.

- The hit layer is the static container around the visual layer, or an invisible element positioned over it (`position: absolute`, `inset`, a higher `z-index`).
- Make the hit layer at least 44×44px on touch devices, even when the visual is smaller.
- Make the hit layer the first sibling of the visual layer, so CSS selectors drive every effect from its states: `.hit:hover ~ .visual`, `.hit:active ~ .visual`, `.hit:focus-visible ~ .visual`.
- The hit layer is the interactive element (`<a>`, `<button>`): it carries the accessible name (`aria-label` when it has no text). Draw the focus ring on the visual layer, through `.hit:focus-visible ~ .visual`.

```html
<div class="control">
    <button
        class="hit"
        aria-label="Close"
    ></button>
    <span class="visual">…</span>
</div>
```

## Interruption

An interruption keeps the animation's **intent**: an entrance always reads as that entrance, and the eye never sees a cut. Whether the element is still visible decides how. Spam-testing (Workflow) checks both cases.

- **Visible**: continue from the current on-screen value toward the new target. Retarget it; restarting from its first frame makes the element jump.
    - Reversing mid-flight (closing a dropdown while it opens) runs the exit from where the element is, at the exit's timing.
- **Hidden** (faded out, clipped out, or off-screen): snap it instantly to the enter's start value and replay the full enter. The snap happens while hidden, so it never shows as a cut.
    - A slider image that zooms out as it enters always starts from its full zoom, even if its last zoom-out had not finished.
    - Staggered items sliding in from the side of a reopened menu always slide the full distance.

## Reduced motion

Under `prefers-reduced-motion: reduce`, keep the fades and color changes that explain a state change, and drop moves: translation, scale, travel and stagger. Fade timing stays the same.

## Implementation

- Animate with the Web Animations API (`element.animate`).
- Animate `opacity` and `transform` by default. `clip-path` is allowed for reveals. Container size is allowed for morphs only.
- Name each animated property explicitly (avoid `transition: all`), so only the intended properties animate.
- Put the background (ground, tint, blur) on its own layer, separate from the content:
    - The background resizes and fades on its own.
    - The content keeps its own clip and its own fade.
    - This reduces repaints.
- Put slow transform layers on the GPU with `will-change: transform`.
- Smooth moving or scaling layers with a rotation too small to see: `rotate(0.02deg)`.
