# Rendara — Codebase Documentation

## Stack
- Next.js 16.2.4 (App Router, Turbopack)
- Tailwind CSS v4 (uses `@import "tailwindcss"` not `@tailwind` directives)
- TypeScript
- Deployed on Vercel via GitHub auto-deploy (push to `main` → live)

## Live URL
https://rendara.nanocorp.app

## Stripe Payment Link
https://buy.stripe.com/6oU8wQcdKg1pgXg64zePp0x
Product: "Starter Video" — $299 (product_id: 8b1c145d-9107-4c95-8cc8-1a8159dee617)

## File Structure
```
app/
  layout.tsx     — metadata, analytics beacon (NanoCorp beacon script via next/script)
  page.tsx       — full landing page (client component, single file)
  globals.css    — Tailwind v4 import, custom CSS: animations, .reveal, .card, .btn-primary, .btn-ghost
  favicon.ico
public/          — Next.js default SVGs
```

## Landing Page Sections (page.tsx)
1. **Navbar** — sticky, blur backdrop, "Get Started →" links to Stripe
2. **Hero** — full-viewport, animated gradient mesh + dot grid, badge, H1, two CTAs, stats row
3. **Value Props** — 3 cards (Upload Any Format, We Handle Everything, 48h Delivery)
4. **How It Works** — id="how-it-works", 3 numbered steps with connector line
5. **Pricing** — Starter $299/video, Growth $799/mo (highlighted), Enterprise Custom
6. **Social Proof** — 5 logo placeholders + 3 testimonial cards
7. **CTA Banner** — gradient bg, "Get Your First Video" → Stripe
8. **Footer** — Logo, copyright, Privacy/Terms links

## Design System
- Colors: #080810 base, violet (#8B5CF6) + blue (#3B82F6) accents
- Fonts: Syne (headings), DM Sans (body), JetBrains Mono (.font-data, labels)
- CSS classes: `.g-text` (gradient text), `.reveal` (scroll fade-in), `.card`, `.card-beam`, `.btn-primary`, `.btn-ghost`
- Animations: `gradient-pan`, `fade-up`, `pulse-ring`, `float-y`, `beam`

## Analytics
NanoCorp beacon injected via `next/script` strategy="afterInteractive" in layout.tsx.
Script URL: `https://phospho-nanocorp-prod--nanocorp-api-fastapi-app.modal.run/beacon/snippet.js?s=rendara`

## Webhook / Post-Payment
Webhook endpoint does NOT exist yet — create `app/api/webhooks/nanocorp/route.ts` if needed.
Post-payment redirect goes to `https://rendara.nanocorp.app/checkout/success` — page not yet created.
