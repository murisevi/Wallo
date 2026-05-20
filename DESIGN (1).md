# Design System Strategy: The Serene Ledger

## 1. Overview & Creative North Star: "The Digital Sanctuary"
The financial world is often synonymous with anxiety, rigid grids, and cold data. This design system rejects that paradigm. Our Creative North Star is **"The Digital Sanctuary."** 

We are moving away from the "banking app" aesthetic and toward a high-end, editorial experience that feels like a well-organized personal journal. We achieve this through **Organic Asymmetry** and **Tonal Depth**. Instead of a standard 12-column rigid grid, we use generous, intentional white space (the "Breathing Room" principle) to let data breathe. Layouts should feel curated, not automated. Elements should overlap slightly or use staggered alignments to break the "template" look, creating a sense of human touch and intentionality.

---

## 2. Colors: Tonal Atmosphere
The palette is rooted in warmth and soft contrasts to evoke a sense of calm and control.

### Surface Hierarchy & The "No-Line" Rule
**Strict Mandate:** Designers are prohibited from using 1px solid borders to define sections. Traditional lines create visual "noise" and mental stress. 
- **Boundaries:** Define sections solely through background color shifts. Use `surface_container_low` (#f3f4f3) for secondary sections sitting on a `background` (#faf9f8) base.
- **Nesting:** Treat the UI as stacked sheets of fine, heavy-stock paper. To highlight a featured insight or "Total Balance" card, use `surface_container_lowest` (#ffffff) on top of a `surface_container` (#edeeed) background. This creates depth through value, not geometry.

### The "Glass & Signature" Rule
- **Glassmorphism:** For floating action buttons or navigation bars, use `surface_container_low` at 80% opacity with a `20px` backdrop-blur. This integrates the UI with the content behind it, softening the overall experience.
- **Signature Gradients:** For main CTAs and "Success" moments, do not use flat colors. Use a subtle linear gradient from `primary` (#0060ad) to `primary_container` (#68abff) at a 135-degree angle. This adds "soul" and a premium finish.

---

## 3. Typography: Editorial Clarity
We use **Manrope** for its geometric yet warm character. The hierarchy is designed to guide the eye through a narrative of financial health.

*   **Display (Large/Medium):** Used for big "Hero" numbers (e.g., Total Balance). These should be tracked slightly tighter (-2%) to feel like a premium magazine headline.
*   **Headline (Small/Medium):** Used for section starts. These convey the "Calm and Control" personality.
*   **Title (Medium/Small):** For card headers. Use `on_surface` (#303333) for high readability.
*   **Body:** Manrope’s high x-height ensures legibility even at `body-sm` (0.75rem). Always use `on_surface_variant` (#5d605f) for secondary body text to reduce visual weight and stress.

The typography hierarchy isn't just about size; it's about **Authority vs. Assistance**. High-contrast scale shifts (e.g., a `display-lg` balance next to a `label-md` date) create a sophisticated, editorial rhythm.

---

## 4. Elevation & Depth: Tonal Layering
In this system, "Elevation" is a feeling, not a drop-shadow effect.

*   **The Layering Principle:** Depth is achieved by "stacking" the surface-container tiers. 
    *   *Base:* `background` (#faf9f8)
    *   *Content Block:* `surface_container_low` (#f3f4f3)
    *   *Interactive Card:* `surface_container_lowest` (#ffffff)
*   **Ambient Shadows:** For elements that truly need to "float" (like a bottom sheet or a modal), use an ultra-diffused shadow: `box-shadow: 0 20px 40px rgba(48, 51, 51, 0.06)`. Note the use of the `on_surface` color for the shadow tint—never use pure black.
*   **The "Ghost Border" Fallback:** If a container sits on a background of the same color, use a "Ghost Border": `1px solid` of `outline_variant` (#b0b2b1) at **15% opacity**. It should be felt rather than seen.

---

## 5. Components: Soft & Intentional
All components inherit the **Roundedness Scale**, primarily using `lg` (2rem) and `xl` (3rem) to maintain the "Humano & Cercano" vibe.

*   **Buttons (The Pill):** 
    *   *Primary:* Gradient-filled (Primary to Primary-Container), `rounded-full`, no shadow. 
    *   *Secondary:* `surface_container_high` background with `on_primary_container` text.
*   **Cards (The Container):** 
    *   Strictly no dividers. Use `Spacing 6` (2rem) of vertical white space to separate transaction groups. Use `surface_container_low` to group related items.
*   **Input Fields:** 
    *   Background: `surface_container_lowest`. 
    *   Border: None, except the "Ghost Border" at 10% opacity. 
    *   Focus State: A soft 4px outer glow of `surface_tint` (#0060ad) at 20% opacity.
*   **The "Vibe" Chips:** 
    *   Use `secondary_container` (#a7f4b0) for income and `tertiary_container` (#fc8585) for expenses. These should be rounded-md (1.5rem) and use `label-md` typography.
*   **Progress Bars:** 
    *   Thick (8px+), rounded-full tracks. Use the background color of the container to "carve out" the track, creating a tactile, debossed look.

---

## 6. Do's and Don'ts

### Do
*   **Do** use asymmetrical margins (e.g., more padding on the left than the right in a header) to create a custom, high-end feel.
*   **Do** use the `spacing-10` (3.5rem) or `spacing-12` (4rem) values for major section gaps. Generosity is the key to "No Stress."
*   **Do** use "Soft Success": When a goal is met, use a combination of `secondary` (#216c36) and a subtle backdrop-blur—not a jarring, high-vibrancy green.

### Don't
*   **Don't** use 1px solid black or grey lines to separate list items. Use white space or a subtle `surface_variant` background shift.
*   **Don't** use sharp corners (`none` or `sm`). Every corner should feel "smooth to the touch."
*   **Don't** cram information. If a screen feels busy, increase the spacing scale or move content into a "nested" layer.
*   **Don't** use pure black (#000000). Always use `on_surface` (#303333) for text to maintain the warm, human tone.