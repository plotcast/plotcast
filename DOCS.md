# Rendara — Codebase Documentation

## Stack
- Next.js 16.2.4 (App Router, Turbopack)
- Tailwind CSS v4 (uses `@import "tailwindcss"` not `@tailwind` directives)
- TypeScript
- Deployed on Vercel via GitHub auto-deploy (push to `main` → live)

## Live URL
https://rendara.nanocorp.app

## Stripe Products & Payment Link

**Active payment link (all products):** https://buy.stripe.com/cNibJ2b9G3eDfTcdx1ePp0K

| Product | Price | ID |
|---|---|---|
| Starter Video (legacy) | $299 one-time | 8b1c145d-9107-4c95-8cc8-1a8159dee617 |
| Rendara Starter — 1 Data Video | $299 one-time | d8f07be1-3fa6-442e-9f2f-cb81bb37800c |
| Rendara Growth — 3 Data Videos/Month | $799/mo | 92d681ed-eaf4-4772-9fbb-11aa2a59b77f |

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

## Plotcast Repo Export Notes
- Date: 2026-04-29
- Task: publish the existing local codebase to a new public GitHub repository under the `plotcast` account.
- Filesystem search results: no separate `/nanocorp-hq/plotcast` or other `plotcast` source directory exists in this environment.
- Source used for export: `/home/worker/repo` (the only local git working tree present).
- Starting commit for export: `9928a34` (`docs: update Stripe products table with Starter and Growth plans`).
- GitHub target repo: `https://github.com/plotcast/plotcast`

## VM Context Import Notes
- Date: 2026-04-29
- Task: commit all relevant VM markdown and context files into `plotcast/plotcast`.
- Global discovery commands executed:
  - `find / -name "*.md" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null`
  - `find / \( -iname 'AGENTS.md' -o -iname 'agents.md' -o -iname 'context*' -o -iname 'README*' \) -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null`
  - `ls -la /`
  - `ls -la /home/worker/`
- Raw outputs were saved under `vm-context/manifests/`.
- Relevant copied sources were:
  - `/.nanocorp/`
  - `/home/worker/.codex/skills/.system/`
  - `/opt/nanocorp/skills/`
- No standalone `AGENTS.md`, `agents.md`, or `context.md` files were present outside system/package content.
- `.agents/skills` and `.claude/skills` exist in the repo as symlinks to `/opt/nanocorp/skills`.
- `vm-context/vm-root/.nanocorp/codex_prompt.txt` was reduced to a stub because the original task prompt contained live GitHub authentication material and GitHub push protection continued to reject fuller sanitized copies.
- Intentional exclusion: OS and package-manager docs under locations such as `/usr`, `/opt/yarn-v1.22.22`, and `/__modal` were preserved in manifests but not copied into the repo tree.
- Export directory added: `vm-context/`
