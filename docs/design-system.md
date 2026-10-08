# EquiClaim — Neo-Brutalist Acid

## Product
Forensic audit engine for hospital bills. Reads an itemized bill + EOB, benchmarks CPT/HCPCS lines against the hospital’s CMS price file, checks 45 CFR § 149 and NCCI, then pauses for a human to certify a dispute docket.

## Visual system (authoritative)
High-contrast Neo-Brutalism. Paper #F8F4E8, ink #09090B, acid yellow-green #D2E823. No blur on shadows — only offset solid blocks. 2px–4px ink borders on every interactive element. Radius never exceeds 32px (buttons 12px).

**Type:** Dela Gothic One for all display/uppercase headings (tracking-tighter). Space Grotesk 400–700 for body. IBM Plex Mono remains for claim IDs, citations, and money.

**CTA:** Hard-shadow button — ink fill, acid text, 16px 32px padding, 12px radius, 2px ink border, shadow 4px 4px 0 #09090B. Hover/click: translate(2px, 2px) and drop the shadow. Active: translateY(4px).

**Motion:** Display words rise in on load. The sample statement scan tracks scroll across three beats. The audit trail draws a vertical rule. Glitch on hover for display text (±2px, 0.3s, infinite). Custom 32px mix-blend-difference cursor that scales 2.5× over links/buttons. SVG noise overlay at 3% opacity. `prefers-reduced-motion` skips the pin and the reveals.

**Layout:** Sticky floating nav (16px inset, 90% paper + blur 24px, 2px border, 12px radius). Hero 7/5 grid. Bento with one 2×2 dark card and two 1×1 hard-shadow cards. Horizontal 320px product-style cards for citations. Ink footer with 3 columns + acid submit.

Night theme inverts the paper/ink grounds; acid stays the only accent. Use ONLY these fonts and colors.
