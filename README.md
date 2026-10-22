# Free Credits & Offers for Students and Startups

An independent, checked index of free tiers, trial credits, startup programs and student offers across developer services: LLM and AI APIs, cloud, databases, hosting, VPS and servers, dev tools, GPU and ML, observability, auth and analytics, email and messaging, API and CMS platforms, payments, education-only programs, and self-hosted open-source alternatives.

**Live site:** https://studentandstartupdeals.danubelabs.net/
**Source of the site:** `docs/` on the `revamp` branch (GitHub Pages).

Snapshot as of 2026-10-22: 236 providers, 1,474 verified findings across 15 service fronts, and 45 headline offers re-checked against official provider pages.

## What is in the repo

| Path | What it is |
|---|---|
| `docs/` | The published site (GitHub Pages source): home, fronts, provider pages, live checks, changes, 404, sitemap, robots, manifest, social card, plus the full PDF/DOCX report, Markdown index and sections under `docs/downloads/` and `docs/research/`. |
| `docs/CNAME` | Custom domain for GitHub Pages. |
| `data/` | Structured data the site is built from: `registry.json` (all providers and findings), `quickhits.json`, `verification.json`. |
| `data/pipeline/` | Stage outputs from the research pipeline: maps, deep research, gap fill, critics. |
| `tools/build_site.py` | Generates every page, `sitemap.xml`, `robots.txt`, `site.webmanifest` and the assets from `data/`. |
| `tools/og-mock.html` | HTML mock for the social card, screenshotted to `docs/assets/og-image.png`. |

## Rebuild the site

Python 3 with no extra packages:

```
python tools/build_site.py          # regenerate docs/
python tools/build_site.py --check  # fails if committed docs/ is stale
```

The site URL is set once, in `BASE` and `CUSTOM_DOMAIN` at the top of `tools/build_site.py`.

## How the data was made

1. Map: one research agent per service front listed providers and offers, with source URLs.
2. Deep research: one agent per provider checked amounts, eligibility, claim steps, expiry, gotchas and 2025–26 changes.
3. Critique: completeness, accuracy and currency critics flagged gaps and corrections; gaps were filled.
4. Consolidation: providers were merged across fronts and duplicate findings removed.
5. Live verification: 45 headline offers were re-checked by agents that fetched each official page.

Research agents ran on Haiku. Verification agents ran on Opus.

## Caveats

- This is a snapshot. Offers change often. Check the provider's current page before you sign up or claim an offer.
- Live-check verdicts come from agents reading official pages. They are a guide, not a substitute for reading the page yourself.
- Quick-hit rankings are parsed from offer text. Some values are eligibility thresholds or program totals, marked "pool/threshold" in the report.
- A few findings sit under a related product's provider entry. The offer text names the actual program.
- Some provider pages are JavaScript-gated. Those amounts are medium confidence or were marked unverifiable.
- This is independent research, not affiliated with any provider. Not financial, legal or tax advice.

## License

MIT. See [LICENSE](LICENSE).
