"""Build the static GitHub Pages site from the research data in data/.

Run from the repo root:  python tools/build_site.py

Writes index.html, fronts/, providers/, verification.html, changes.html, 404.html,
sitemap.xml, robots.txt, site.webmanifest and assets/ (style.css, app.js, favicon.svg, og-image.png).
Every page has a unique title, description, canonical URL, Open Graph and Twitter tags, and
JSON-LD (WebSite, Dataset, FAQPage, BreadcrumbList, CollectionPage, WebPage).
"""
import datetime
import html
import json
import shutil
import tempfile
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs'  # published folder: GitHub Pages serves revamp:/docs
BASE = 'https://studentandstartupdeals.danubelabs.net/'
CUSTOM_DOMAIN = 'studentandstartupdeals.danubelabs.net'
REPO_URL = 'https://github.com/FiredMosquito831/free-credits-for-students-and-startups'
SITE_NAME = 'Free Credits & Offers for Students and Startups'
ASOF = '2026-10-22'
DOWNLOADS = ['downloads/Freebies_Report.pdf', 'downloads/Freebies_Report.docx']
URL_OK = re.compile(r'^https?://\S+$')
LINK_CUT = re.compile(r'[\s()\'";<>]')
VERDICT_LABEL = {'confirmed': 'Confirmed', 'partly_confirmed': 'Partly confirmed', 'incorrect': 'Incorrect',
                 'no_longer_available': 'No longer available', 'unverifiable': 'Unverifiable'}

REG = json.loads((ROOT / 'data/registry.json').read_text(encoding='utf-8'))
QH = json.loads((ROOT / 'data/quickhits.json').read_text(encoding='utf-8'))
VER = json.loads((ROOT / 'data/verification.json').read_text(encoding='utf-8'))
PROVIDERS = REG['providers']
FRONTS = REG['fronts']
STATS = REG['stats']
FRONT_TITLE = {f['id']: f['title'] for f in FRONTS}
WITH_PAGE = [p for p in PROVIDERS if p['findings']]
for p in WITH_PAGE:
    p['slug'] = re.sub(r'[^a-z0-9]+', '-', p['key'].lower()).strip('-')[:80] or 'provider'
assert len({p['slug'] for p in WITH_PAGE}) == len(WITH_PAGE), 'provider slug collision'
VER_BY_NAME = {}
for it in VER['items']:
    VER_BY_NAME.setdefault(it['provider'], []).append(it)
PAGES = []


# ---------- helpers ----------
def esc(s):
    return html.escape('' if s is None else str(s), quote=True)


def clean_link(u):
    u = LINK_CUT.split(str(u or '').strip())[0]
    return u if URL_OK.match(u) else ''


def domain(u):
    return urlparse(u).netloc.replace('www.', '')


def trim(s, n):
    s = ' '.join(str(s or '').split())
    return s if len(s) <= n else s[: n - 1].rsplit(' ', 1)[0] + '…'


def badge(text, cls):
    return f'<span class="badge {cls}">{esc(text)}</span>'


def prov_link(name, prefix):
    page = next((p for p in WITH_PAGE if p['name'] == name), None)
    if page is None:
        return esc(name)
    return f'<a href="{prefix}{page["slug"]}.html">{esc(name)}</a>'


def link_html(url, label=None):
    u = clean_link(url)
    if not u:
        return '—'
    return f'<a href="{esc(u)}" rel="noopener">{esc(label or domain(u))}</a>'


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace('</', '<\\/') + '</script>'


def crumb_ld(items):
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': name, 'item': url} for i, (name, url) in enumerate(items)]}


def crumbs_html(items):
    parts = [f'<a href="{href}">{esc(label)}</a>' if href else esc(label) for label, href in items]
    return '<nav class="crumbs" aria-label="Breadcrumb">' + ' / '.join(parts) + '</nav>'


def write(path, text):
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')
    PAGES.append(path)


def head(path, title, desc, depth, ld_blocks=(), robots='index, follow, max-image-preview:large'):
    canon = BASE if path == 'index.html' else BASE + path
    root = '../' * depth
    out = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f'<title>{esc(title)}</title>',
           f'<meta name="description" content="{esc(desc)}">',
           f'<link rel="canonical" href="{esc(canon)}">',
           f'<meta name="robots" content="{esc(robots)}">',
           '<meta property="og:type" content="website">',
           f'<meta property="og:site_name" content="{esc(SITE_NAME)}">',
           f'<meta property="og:title" content="{esc(title)}">',
           f'<meta property="og:description" content="{esc(desc)}">',
           f'<meta property="og:url" content="{esc(canon)}">',
           f'<meta property="og:image" content="{BASE}assets/og-image.png">',
           '<meta name="twitter:card" content="summary_large_image">',
           f'<meta name="twitter:title" content="{esc(title)}">',
           f'<meta name="twitter:description" content="{esc(desc)}">',
           f'<meta name="twitter:image" content="{BASE}assets/og-image.png">',
           '<meta name="theme-color" content="#0F766E">',
           '<meta name="color-scheme" content="light">',
           '<link rel="preconnect" href="https://fonts.googleapis.com">',
           '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;600;700&display=swap">',
           f'<link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml">',
           f'<link rel="manifest" href="{root}site.webmanifest">',
           f'<link rel="stylesheet" href="{root}assets/style.css">']
    out += [ld(b) for b in ld_blocks]
    out.append('</head>')
    return '\n'.join(out) + '\n'


def shell(path, title, desc, depth, body, ld_blocks=(), robots='index, follow, max-image-preview:large'):
    root = '../' * depth
    header = (
        '<a class="skip" href="#main">Skip to content</a>\n'
        '<header class="site-header"><div class="wrap bar">'
        f'<a class="brand" href="{root}index.html">'
        '<svg class="mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect width="24" height="24" rx="7" fill="#0F766E"/>'
        '<text x="12" y="16.5" font-size="13" font-weight="700" text-anchor="middle" fill="#FFFFFF" font-family="Arial, sans-serif">$</text></svg>'
        '<span>Free Credits &amp; Offers</span></a>'
        '<nav aria-label="Main">'
        f'<a href="{root}index.html#fronts">Fronts</a>'
        f'<a href="{root}index.html#directory">Directory</a>'
        f'<a href="{root}verification.html">Live checks</a>'
        f'<a href="{root}changes.html">Changes</a>'
        f'<a href="{root}index.html#downloads">Downloads</a>'
        '</nav></div></header>\n')
    footer = (
        '<footer class="site-footer"><div class="wrap">'
        '<p class="foot-title">Free Credits &amp; Offers for Students and Startups</p>'
        f'<p>Independent research snapshot as of {ASOF}. Not affiliated with any provider named here. '
        'Terms change often: read the provider\'s current page before you sign up or claim an offer.</p>'
        f'<p class="foot-links"><a href="{root}{DOWNLOADS[0]}">PDF report</a>'
        f'<a href="{root}research/INDEX.md">Index (Markdown)</a>'
        f'<a href="{REPO_URL}" rel="noopener">Source on GitHub</a>'
        f'<a href="{REPO_URL}/issues/new" rel="noopener">Report an outdated offer</a></p>'
        '</div></footer>\n'
        f'<script src="{root}assets/app.js" defer></script>\n')
    return (head(path, title, desc, depth, ld_blocks, robots) + '<body>\n' + header
            + '<main id="main" class="wrap">\n' + body + '\n</main>\n' + footer + '</body>\n</html>\n')


# ---------- pages ----------
def build_fronts():
    for f in FRONTS:
        rows = [p for p in PROVIDERS if f['id'] in p['fronts']]
        if not rows:
            continue
        total = sum(len(p['findings']) for p in rows)
        path = f'fronts/{f["id"]}.html'
        title = trim(f'{f["title"]}: free offers for students and startups', 66)
        desc = trim(f'{len(rows)} providers and {total} verified findings in {f["title"].lower()}, checked {ASOF}. '
                    'Eligibility, claim steps and source links.', 158)
        body = [crumbs_html([('Home', '../index.html'), ('Service fronts', '../index.html#fronts'), (f['title'], None)]),
                f'<h1>{esc(f["title"])}</h1>',
                f'<p class="lead">{len(rows)} providers and {total} verified findings for this front, as of {ASOF}.</p>']
        if f.get('summary'):
            body.append(f'<div class="note"><strong>Mapping summary.</strong> {esc(f["summary"])}</div>')
        body.append('<h2>Comparison table</h2>')
        trs = []
        for p in sorted(rows, key=lambda x: x['name'].lower()):
            name = f'<a href="../providers/{p["slug"]}.html">{esc(p["name"])}</a>' if p['findings'] else esc(p['name'])
            audience = ', '.join(p['audiences']) or 'free-for-all'
            trs.append(f'<tr><th scope="row">{name}</th><td>{esc(trim(p["best_offer"], 150))}</td>'
                       f'<td>{esc(audience)}</td>'
                       f'<td>{p["confidence"]["high"]} / {p["confidence"]["medium"]} / {p["confidence"]["low"]}</td>'
                       f'<td>{link_html(p["link"])}</td></tr>')
        body.append('<div class="tablewrap"><table><caption class="visually-hidden">Providers in '
                    f'{esc(f["title"])}: best offer, audience, confidence counts and source</caption>'
                    '<thead><tr><th scope="col">Provider</th><th scope="col">Best offer</th>'
                    '<th scope="col">Audience</th><th scope="col">Findings H / M / L</th>'
                    '<th scope="col">Source</th></tr></thead><tbody>' + ''.join(trs) + '</tbody></table></div>')
        others = [g for g in FRONTS if g['id'] != f['id'] and any(g['id'] in p['fronts'] for p in PROVIDERS)]
        body.append('<h2>Other service fronts</h2><ul class="list">' + ''.join(
            f'<li><a href="{g["id"]}.html">{esc(g["title"])}</a></li>' for g in others) + '</ul>')
        ldb = [{'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': title, 'description': desc,
                'url': BASE + path, 'dateModified': ASOF,
                'mainEntity': {'@type': 'ItemList', 'itemListElement': [
                    {'@type': 'ListItem', 'position': i + 1, 'name': p['name']} for i, p in enumerate(rows)]}},
               crumb_ld([('Home', BASE), ('Service fronts', BASE + 'index.html#fronts'), (f['title'], BASE + path)])]
        write(path, shell(path, title, desc, 1, '\n'.join(body), ldb))


def build_providers():
    for p in WITH_PAGE:
        path = f'providers/{p["slug"]}.html'
        first = p['fronts'][0]
        title = trim(f'{p["name"]}: free credits and offers for students and startups', 66)
        desc = trim(f'{p["name"]}: {p["best_offer"]}. Eligibility, how to claim, expiry and source links, '
                    f'checked {ASOF}.', 158)
        body = [crumbs_html([('Home', '../index.html'), (FRONT_TITLE[first], f'../fronts/{first}.html'),
                             (p['name'], None)]),
                f'<h1>{esc(p["name"])}: free credits and offers</h1>',
                f'<p class="lead">Best offer on record: {esc(trim(p["best_offer"], 220))}. '
                f'{len(p["findings"])} verified findings, checked {ASOF}.</p>']
        for it in VER_BY_NAME.get(p['name'], []):
            live = (f'<div class="note"><strong>Live check of “{esc(trim(it["offer"], 90))}”:</strong> '
                    f'{badge(VERDICT_LABEL.get(it["verdict"], it["verdict"]), "v-" + it["verdict"])}'
                    f'<p>{esc(it.get("verified_summary", ""))}</p>')
            if clean_link(it.get('official_url')):
                live += f'<p>Official page: {link_html(it["official_url"], "open the provider page")}</p>'
            body.append(live + '</div>')
        body.append('<h2>Offers</h2>')
        for f_ in p['findings']:
            parts = [f'<article class="finding"><h3>{esc(f_["name"])} '
                     f'{badge(f_["confidence"] + " confidence", "conf-" + f_["confidence"])}</h3>']
            if f_['detail']:
                parts.append(f'<p>{esc(f_["detail"])}</p>')
            dl = []
            for label, key in (('Eligibility', 'eligibility'), ('How to claim', 'claim'),
                               ('Expiry', 'expiry'), ('Gotchas', 'gotchas')):
                if f_.get(key):
                    dl.append(f'<dt>{label}</dt><dd>{esc(f_[key])}</dd>')
            if clean_link(f_.get('source_url')):
                dl.append(f'<dt>Source</dt><dd>{link_html(f_["source_url"])}</dd>')
            if dl:
                parts.append('<dl>' + ''.join(dl) + '</dl>')
            if f_['confidence'] == 'low':
                parts.append('<p class="muted">Low confidence: verify before claiming.</p>')
            parts.append('</article>')
            body.append(''.join(parts))
        if p['sunsets']:
            body.append('<h2>2025–26 changes</h2><ul>' + ''.join(f'<li>{esc(s)}</li>' for s in p['sunsets']) + '</ul>')
        notes = [c for c in p['corrections'] if c['item'] or c['text']]
        if notes:
            body.append('<h2>Critic corrections</h2><ul>' + ''.join(
                f'<li><strong>{esc(c["item"])}:</strong> {esc(c["text"])}</li>' for c in notes) + '</ul>')
        body.append('<h2>Listed in</h2><ul class="list">' + ''.join(
            f'<li><a href="../fronts/{fid}.html">{esc(FRONT_TITLE[fid])}</a></li>' for fid in p['fronts']) + '</ul>')
        ldb = [{'@context': 'https://schema.org', '@type': 'WebPage', 'name': title, 'description': desc,
                'url': BASE + path, 'dateModified': ASOF, 'about': {'@type': 'Thing', 'name': p['name']}},
               crumb_ld([('Home', BASE), (FRONT_TITLE[first], BASE + f'fronts/{first}.html'),
                         (p['name'], BASE + path)])]
        write(path, shell(path, title, desc, 1, '\n'.join(body), ldb))


def build_verification():
    items = VER['items']
    tally = VER.get('tally', {})
    summary = ', '.join(f'{tally.get(k, 0)} {VERDICT_LABEL[k].lower()}' for k in VERDICT_LABEL if tally.get(k))
    title = 'Live checks of 45 headline free-credit offers'
    desc = trim(f'{len(items)} headline free-credit and startup offers re-checked against official provider pages '
                f'on {ASOF}: {summary}.', 158)
    trs = []
    for i, it in enumerate(items, 1):
        prov = prov_link(it['provider'], 'providers/')
        trs.append(f'<tr><td>{i}</td><td>{prov}</td><td>{esc(trim(it["offer"], 110))}</td>'
                   f'<td>{badge(VERDICT_LABEL.get(it["verdict"], it["verdict"]), "v-" + it["verdict"])}</td>'
                   f'<td>{esc(it.get("verified_summary", ""))}</td><td>{link_html(it.get("official_url", ""))}</td></tr>')
    body = [crumbs_html([('Home', 'index.html'), ('Live checks', None)]),
            '<h1>Live checks of headline offers</h1>',
            f'<p class="lead">{len(items)} headline offers from the quick-hit tables were re-checked against each '
            f'provider’s official page on {ASOF}. Results: {esc(summary)}.</p>',
            '<p>Verdicts: <strong>Confirmed</strong> means the amount and eligibility match. <strong>Partly confirmed</strong> '
            'means the offer exists but the terms differ; the verified terms are shown. <strong>No longer available</strong> '
            'means it has ended or closed. Agents read the pages; check the live terms before you claim.</p>',
            '<div class="tablewrap"><table><caption class="visually-hidden">Live verdicts for 45 headline offers</caption>'
            '<thead><tr><th scope="col">#</th><th scope="col">Provider</th><th scope="col">Offer</th>'
            '<th scope="col">Verdict</th><th scope="col">Verified terms</th><th scope="col">Official page</th></tr></thead>'
            '<tbody>' + ''.join(trs) + '</tbody></table></div>']
    ldb = [{'@context': 'https://schema.org', '@type': 'WebPage', 'name': title, 'description': desc,
            'url': BASE + 'verification.html', 'dateModified': ASOF},
           crumb_ld([('Home', BASE), ('Live checks', BASE + 'verification.html')])]
    write('verification.html', shell('verification.html', title, desc, 0, '\n'.join(body), ldb))


def build_changes():
    title = '2025–26 changes and critic corrections for free-credit offers'
    desc = trim(f'{STATS["sunset_notes"]} recorded 2025–26 changes and {STATS["corrections"]} critic corrections '
                f'to free tiers, trial credits and startup programs, checked {ASOF}.', 158)
    rows = sorted(PROVIDERS, key=lambda p: p['name'].lower())
    changes = [(p, s) for p in rows for s in p['sunsets']]
    corrs = [(p, c) for p in rows for c in p['corrections'] if c['item'] or c['text']]
    body = [crumbs_html([('Home', 'index.html'), ('Changes', None)]),
            '<h1>2025–26 changes and corrections</h1>',
            f'<p class="lead">Recorded changes to free tiers, trial credits and startup programs, and corrections '
            f'from the critics pass. Checked {ASOF}.</p>',
            '<h2>Changes</h2>',
            '<div class="tablewrap"><table><caption class="visually-hidden">Recorded 2025–26 changes by provider</caption>'
            '<thead><tr><th scope="col">Provider</th><th scope="col">Change</th></tr></thead><tbody>' +
            ''.join(f'<tr><td>{esc(p["name"])}</td><td>{esc(s)}</td></tr>' for p, s in changes) +
            '</tbody></table></div>',
            '<h2>Critic corrections</h2>',
            '<div class="tablewrap"><table><caption class="visually-hidden">Critic corrections by provider</caption>'
            '<thead><tr><th scope="col">Provider</th><th scope="col">Item</th><th scope="col">Correction</th>'
            '<th scope="col">Source</th></tr></thead><tbody>' +
            ''.join(f'<tr><td>{esc(p["name"])}</td><td>{esc(c["item"])}</td><td>{esc(c["text"])}</td>'
                    f'<td>{link_html(c["url"])}</td></tr>' for p, c in corrs) +
            '</tbody></table></div>']
    ldb = [{'@context': 'https://schema.org', '@type': 'WebPage', 'name': title, 'description': desc,
            'url': BASE + 'changes.html', 'dateModified': ASOF},
           crumb_ld([('Home', BASE), ('Changes', BASE + 'changes.html')])]
    write('changes.html', shell('changes.html', title, desc, 0, '\n'.join(body), ldb))


def build_404():
    title = 'Page not found | ' + SITE_NAME
    desc = 'This page does not exist. Go back to the free credits and offers index.'
    body = ('<h1>Page not found</h1><p class="lead">That page does not exist. Start from the index of service '
            'fronts or search for a provider.</p><p><a class="btn primary" href="index.html">Back to the index</a></p>')
    write('404.html', shell('404.html', title, desc, 0, body, robots='noindex, follow'))


FRONT_ICON = {
    'llm-apis': 'M12 3l1.8 4.6L18.4 9.4l-4.6 1.8L12 15.8l-1.8-4.6L5.6 9.4l4.6-1.8z',
    'cloud-credits': 'M7 18h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.2 9.6 3.5 3.5 0 0 0 7 18z',
    'databases': 'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zm0 0v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6',
    'hosting-paas': 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c2.5 2.6 2.5 15.4 0 18M12 3c-2.5 2.6-2.5 15.4 0 18',
    'vps-servers': 'M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01',
    'devtools': 'M4 5h16v14H4zM8 10l3 2-3 2M13 16h4',
    'gpu-ml': 'M9 9h6v6H9zM9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3',
    'observability': 'M3 12h4l3-7 4 14 3-7h4',
    'auth-analytics': 'M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z',
    'email-messaging': 'M4 6h16v12H4zM4 7l8 6 8-6',
    'apis-data': 'M9 3v5M15 3v5M7 8h10v3a5 5 0 0 1-10 0zM12 16v5',
    'payments-fintech': 'M3 6h18v12H3zM3 10h18M7 15h4',
    'student-only': 'M2 9l10-5 10 5-10 5zM6 11v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5',
    'oss-selfhost': 'M8 6l-4 6 4 6M16 6l4 6-4 6M13 4l-2 16',
    'extras': 'M12 5v14M5 12h14',
}


def icon(fid):
    d = FRONT_ICON.get(fid, FRONT_ICON['extras'])
    return f'<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="{d}"/></svg>'


def build_index():
    confirmed = []
    seen = set()
    for it in sorted((i for i in VER['items'] if i['verdict'] == 'confirmed'), key=lambda i: -i['value']):
        if it['provider'] in seen:
            continue
        seen.add(it['provider'])
        confirmed.append(it)
    fronts_cards = []
    for f in FRONTS:
        n = sum(1 for p in PROVIDERS if f['id'] in p['fronts'])
        if n:
            fronts_cards.append(
                f'<a class="card" href="fronts/{f["id"]}.html">{icon(f["id"])}'
                f'<span class="card-body"><strong>{esc(f["title"])}</strong>'
                f'<span class="meta">{n} providers · {f["findings"]} findings</span></span></a>')
    live_rows = ''.join(
        f'<tr><td data-label="Offer">{esc(trim(it["offer"], 100))}</td><td data-label="Provider">{esc(it["provider"])}</td>'
        f'<td data-label="Verified terms">{esc(trim(it.get("verified_summary", ""), 170))}</td>'
        f'<td data-label="Official page">{link_html(it.get("official_url", ""))}</td></tr>' for it in confirmed[:8])
    list_items = []
    for p in sorted(WITH_PAGE, key=lambda x: x['name'].lower()):
        hay = ' '.join([p['name'], p['best_offer'], ' '.join(FRONT_TITLE[f] for f in p['fronts'])]).lower()
        list_items.append(f'<li data-provider="{esc(hay)}"><a href="providers/{p["slug"]}.html">{esc(p["name"])}</a>'
                          f'<br><span class="muted">{esc(trim(p["best_offer"], 110))}</span></li>')
    faq = [
        ('Are these offers free?',
         'Most are free tiers, trial credits, startup programs or student offers. Each has its own limits, duration '
         'and eligibility, listed on the provider page here.'),
        ('Do I need a credit card?',
         'Some offers say no card is required. Read the eligibility line for each one, because some ask for a card '
         'at a later step.'),
        ('Who can use startup programs?',
         'Usually companies that meet criteria such as incorporation, funding stage or an accelerator invitation. '
         'Check each program’s eligibility text.'),
        ('How were the offers checked?',
         'Research agents read provider pages during the sweep and rated each finding high, medium or low confidence. '
         f"{len(VER['items'])} headline offers were re-checked against official pages; the verdicts are on the live checks page."),
        ('How often is this updated?',
         f'This is a snapshot as of {ASOF}. It is not updated automatically, and offers change, so check the provider '
         'before you claim.'),
        ('Is this affiliated with the providers?',
         'No. This is independent research. Provider names are used only to identify the services.'),
    ]
    faq_html = ''.join(f'<details class="faq-item"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>'
                       for q, a in faq)
    title = f'{SITE_NAME} (2026)'
    desc = trim(f'Free tiers, trial credits, startup programs and student offers for LLM APIs, cloud, databases, hosting, '
                f'VPS, dev tools and more: {STATS["providers"]} providers, checked {ASOF}.', 158)
    dataset = {'@type': 'Dataset', 'name': 'Free credits and offers for students and startups (research snapshot, ' + ASOF + ')',
               'description': f'{STATS["providers"]} providers and {STATS["findings"]} verified findings on free tiers, trial '
                              'credits, startup programs and student offers across developer services.',
               'url': BASE, 'dateModified': ASOF, 'isAccessibleForFree': True,
               'keywords': ['free credits', 'startup credits', 'student offers', 'free hosting', 'free API credits',
                            'free VPS', 'developer tools', 'self-hosted open source'],
               'distribution': [
                   {'@type': 'DataDownload', 'encodingFormat': 'application/pdf', 'contentUrl': BASE + DOWNLOADS[0]},
                   {'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/registry.json'},
                   {'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': BASE + 'data/verification.json'}]}
    ldb = [{'@context': 'https://schema.org', '@type': 'WebSite', '@id': BASE + '#website', 'url': BASE,
            'name': SITE_NAME, 'inLanguage': 'en'},
           dataset,
           {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
               {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faq]}]
    stats = ''.join([
        f'<div class="stat"><b>{STATS["providers"]}</b><span>providers</span></div>',
        f'<div class="stat"><b>{STATS["findings"]:,}</b><span>verified findings</span></div>',
        f'<div class="stat"><b>{STATS["fronts"]}</b><span>service fronts</span></div>',
        f'<div class="stat"><b>{len(VER["items"])}</b><span>headline offers re-checked live</span></div>',
    ])
    body = [
        '<section class="hero" aria-labelledby="hero-title">',
        f'<p class="eyebrow">Independent research · snapshot as of {ASOF.replace("-", chr(8209))}</p>',
        '<h1 id="hero-title">Free credits, offers and bonuses for students and startups</h1>',
        '<p class="lead">An independent, checked index of free tiers, trial credits, startup programs and student offers '
        'across LLM and AI APIs, cloud, databases, hosting, VPS and servers, dev tools, GPU and ML, observability, auth, '
        'email, payments and self-hosted open source.</p>',
        '<div class="hero-search" role="search">',
        '<label for="provider-search">Search providers, services or offers</label>',
        '<input id="provider-search" class="search" type="search" placeholder="Try: hosting, GPU, Cloudflare, student" '
        'autocomplete="off">',
        f'<p id="search-status" class="muted" aria-live="polite">{len(WITH_PAGE)} providers</p>',
        '</div>',
        '<div class="cta"><a class="btn primary" href="#fronts">Browse service fronts</a>'
        '<a class="btn" href="downloads/Freebies_Report.pdf">Download the PDF report</a>'
        '<a class="btn ghost" href="verification.html">See the live checks</a></div>',
        '</section>',
        f'<section class="stats" aria-label="Key numbers">{stats}</section>',
        f'<div class="note"><strong>Snapshot as of {ASOF}.</strong> Terms change often. Read each provider’s current page '
        'before you sign up or claim an offer. Not affiliated with any provider.</div>',
        '<section id="fronts"><h2>Browse by service front</h2><div class="cards">' + ''.join(fronts_cards) + '</div></section>',
        '<section id="live"><h2>Confirmed headline offers</h2>'
        '<p>Confirmed against the provider’s official page. Partly confirmed and ended offers are on the '
        '<a href="verification.html">live checks page</a>.</p>'
        '<div class="tablewrap"><table class="stack"><caption class="visually-hidden">Confirmed headline offers with verified terms</caption>'
        '<thead><tr><th scope="col">Offer</th><th scope="col">Provider</th><th scope="col">Verified terms</th>'
        '<th scope="col">Official page</th></tr></thead><tbody>' + live_rows + '</tbody></table></div></section>',
        '<section id="directory"><h2>Provider directory</h2>'
        '<p class="muted">Every provider with a page. Filter with the search box at the top.</p>'
        '<ul class="providers" id="provider-list">' + ''.join(list_items) + '</ul></section>',
        '<section id="faq"><h2>Frequently asked questions</h2>' + faq_html + '</section>',
        '<section id="downloads"><h2>Downloads and data</h2><div class="cards">'
        '<a class="card" href="downloads/Freebies_Report.pdf"><span class="card-body"><strong>Full report (PDF)</strong>'
        '<span class="meta">All providers and findings</span></span></a>'
        '<a class="card" href="downloads/Freebies_Report.docx"><span class="card-body"><strong>Full report (DOCX)</strong>'
        '<span class="meta">Editable Word version</span></span></a>'
        '<a class="card" href="research/INDEX.md"><span class="card-body"><strong>Index (Markdown)</strong>'
        '<span class="meta">Quick hits, changes, corrections</span></span></a>'
        '<a class="card" href="data/registry.json"><span class="card-body"><strong>All providers (JSON)</strong>'
        '<span class="meta">Structured data behind the site</span></span></a>'
        '</div></section>',
        '<section class="report-cta"><h2>Spotted an outdated offer?</h2>'
        '<p>Open an issue on GitHub with the provider name and the current terms.</p>'
        f'<a class="btn" href="{REPO_URL}/issues/new" rel="noopener">Report an outdated offer</a></section>',
    ]
    write('index.html', shell('index.html', title, desc, 0, '\n'.join(body), ldb))


def write_static():
    (OUT / 'assets').mkdir(exist_ok=True)
    (OUT / 'assets/style.css').write_text(CSS, encoding='utf-8')
    (OUT / 'assets/app.js').write_text(JS, encoding='utf-8')
    (OUT / 'assets/favicon.svg').write_text(FAVICON, encoding='utf-8')
    (OUT / 'site.webmanifest').write_text(json.dumps({
        'name': SITE_NAME, 'short_name': 'Free Credits', 'start_url': './', 'display': 'browser',
        'background_color': '#FFFFFF', 'theme_color': '#0F766E',
        'icons': [{'src': 'assets/favicon.svg', 'sizes': 'any', 'type': 'image/svg+xml'}]}, indent=2), encoding='utf-8')
    (OUT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n', encoding='utf-8')
    today = ASOF
    urls = [BASE if p == 'index.html' else BASE + p for p in PAGES if not p.startswith('404')]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f'  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>' for u in urls]
    xml.append('</urlset>')
    (OUT / 'sitemap.xml').write_text('\n'.join(xml) + '\n', encoding='utf-8')


CSS = """:root{--teal:#0F766E;--teal-hi:#0D9488;--teal-soft:#CCFBF1;--teal-wash:#F0FDFA;--ink:#0F172A;--ink-2:#1E293B;--muted:#475569;--line:#D9E3EA;--surface:#FFFFFF;--zebra:#F8FAFC;--amber:#F59E0B;--amber-wash:#FFF7E6;--amber-line:#F5C77E;--amber-ink:#78350F;--ok:#DCFCE7;--ok-ink:#14532D;--part:#FEF3C7;--part-ink:#78350F;--bad:#FEE2E2;--bad-ink:#7F1D1D;--off:#E5E7EB;--off-ink:#374151;--info:#E0F2FE;--info-ink:#0C4A6E;--radius:14px;--shadow:0 1px 2px rgba(15,23,42,.06),0 4px 14px rgba(15,23,42,.06)}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth;scroll-padding-top:84px}
body{margin:0;font:400 16px/1.6 "DM Sans",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:var(--ink);background:var(--surface)}
h1,h2,h3,.brand span,.stat b,.card strong,.foot-title{font-family:"Space Grotesk",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
a{color:var(--teal);text-underline-offset:3px}
a:hover{color:var(--ink)}
img,svg{max-width:100%}
:focus-visible{outline:3px solid var(--amber);outline-offset:3px;border-radius:4px}
.skip{position:absolute;left:-9999px;top:auto}
.skip:focus{left:16px;top:8px;background:#fff;color:var(--ink);padding:8px 12px;z-index:20;border-radius:8px}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}
main{padding:0 0 40px}
section{scroll-margin-top:84px}
.site-header{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.95);backdrop-filter:saturate(1.4) blur(8px);border-bottom:1px solid var(--line)}
.bar{display:flex;flex-wrap:wrap;gap:10px 24px;align-items:center;justify-content:space-between;padding:12px 20px}
.brand{display:inline-flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);font-weight:700;font-size:18px}
.mark{width:28px;height:28px;flex:none}
.site-header nav{display:flex;flex-wrap:wrap;gap:6px 20px}
.site-header nav a{color:var(--ink-2);text-decoration:none;font-size:15px;font-weight:500;padding:4px 0;border-bottom:2px solid transparent}
.site-header nav a:hover{color:var(--teal);border-bottom-color:var(--teal)}
.hero{margin:0 -20px;padding:40px 20px 36px;background:radial-gradient(900px 380px at 0% 0%,var(--teal-soft) 0%,rgba(204,251,241,0) 60%),linear-gradient(180deg,var(--teal-wash) 0%,#fff 100%);border-bottom:1px solid var(--line)}
.eyebrow{display:inline-block;margin:0 0 14px;padding:4px 12px;border-radius:999px;background:var(--surface);border:1px solid var(--teal-soft);color:var(--teal);font-size:13px;font-weight:600;letter-spacing:.02em}
h1{font-size:clamp(30px,6vw,54px);line-height:1.06;color:var(--ink);margin:0 0 14px;letter-spacing:-.02em;max-width:18ch}
.lead{font-size:clamp(17px,2.2vw,19px);color:var(--ink-2);max-width:62ch;margin:0 0 22px}
.hero-search label{display:block;font-weight:600;font-size:15px;margin:0 0 6px}
.search{width:100%;max-width:640px;min-height:52px;padding:12px 16px;font:500 16px "DM Sans",system-ui,sans-serif;color:var(--ink);background:#fff;border:2px solid #7C8BA0;border-radius:12px;-webkit-appearance:none;appearance:none}
.search::placeholder{color:#64748B}
.search:focus{outline:3px solid var(--amber);outline-offset:2px;border-color:var(--teal)}
#search-status{margin:8px 0 0;font-size:14px}
.cta{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0 0}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 18px;border-radius:999px;text-decoration:none;font-weight:600;font-size:15px;border:2px solid var(--teal);color:var(--teal);background:#fff;transition:background .2s,color .2s,border-color .2s}
.btn:hover{background:var(--teal-wash);color:var(--ink)}
.btn.primary{background:var(--teal);color:#fff}
.btn.primary:hover{background:var(--ink);border-color:var(--ink);color:#fff}
.btn.ghost{border-color:transparent;background:transparent}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:28px 0 8px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow)}
.stat b{display:block;font-size:clamp(26px,4vw,34px);line-height:1.1;color:var(--teal)}
.stat span{font-size:14px;color:var(--muted)}
h2{font-size:clamp(22px,3.2vw,28px);line-height:1.2;color:var(--ink);margin:44px 0 10px;padding-top:6px}
h2::before{content:"";display:block;width:44px;height:4px;border-radius:4px;background:var(--amber);margin:0 0 10px}
h3{font-size:18px;color:var(--ink);margin:22px 0 8px}
.note{background:var(--amber-wash);border:1px solid var(--amber-line);border-left:5px solid var(--amber);border-radius:12px;padding:14px 16px;margin:24px 0;color:var(--amber-ink)}
.note p{margin:6px 0 0}
.note strong{color:var(--amber-ink)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.card{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px;background:var(--surface);color:var(--ink);text-decoration:none;box-shadow:var(--shadow);transition:transform .2s,border-color .2s,box-shadow .2s}
.card:hover{border-color:var(--teal-hi);transform:translateY(-2px);box-shadow:0 10px 24px rgba(15,118,110,.14);color:var(--ink)}
.card-body{display:flex;flex-direction:column;gap:2px;min-width:0}
.card strong{font-size:16.5px;line-height:1.3;color:var(--ink)}
.meta{font-size:14px;color:var(--muted)}
.ico{flex:none;width:40px;height:40px;padding:8px;border-radius:12px;background:var(--teal-wash);color:var(--teal);fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);margin:14px 0;background:var(--surface);-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;min-width:560px;font-size:14.5px}
th,td{text-align:left;padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
thead th{background:var(--ink-2);color:#fff;font-weight:600}
tbody tr:nth-child(even){background:var(--zebra)}
tbody th{font-weight:600}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:600;white-space:nowrap;margin:0 4px 0 0;vertical-align:middle}
.v-confirmed,.conf-high{background:var(--ok);color:var(--ok-ink)}
.v-partly_confirmed,.conf-low{background:var(--part);color:var(--part-ink)}
.v-incorrect,.v-no_longer_available{background:var(--bad);color:var(--bad-ink)}
.v-unverifiable{background:var(--off);color:var(--off-ink)}
.conf-medium{background:var(--info);color:var(--info-ink)}
.crumbs{font-size:14px;color:var(--muted);margin-top:18px}
.crumbs a{color:var(--muted)}
.list{padding-left:18px;columns:1 260px;column-gap:26px}
.list li{margin:4px 0;break-inside:avoid}
.providers{list-style:none;padding:0;margin:0;columns:1 280px;column-gap:14px}
.providers li{margin:0 0 8px;break-inside:avoid;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:#fff}
.providers li[hidden]{display:none}
.providers a{font-weight:600}
.finding{border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;margin:14px 0;background:var(--surface);box-shadow:var(--shadow)}
.finding h3{margin:0 0 8px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
dl{display:grid;grid-template-columns:minmax(0,1fr);gap:2px 14px;margin:10px 0 0;font-size:15px}
dt{color:var(--muted);font-weight:600;margin-top:8px}
dd{margin:0;min-width:0;overflow-wrap:anywhere}
.faq-item{border:1px solid var(--line);border-radius:12px;background:#fff;margin:10px 0;overflow:hidden}
.faq-item summary{cursor:pointer;list-style:none;padding:14px 46px 14px 16px;font-weight:600;position:relative;min-height:44px}
.faq-item summary::-webkit-details-marker{display:none}
.faq-item summary::after{content:"+";position:absolute;right:16px;top:50%;transform:translateY(-50%);font-size:22px;line-height:1;color:var(--teal)}
.faq-item[open] summary::after{content:"\u2212"}
.faq-item p{margin:0;padding:0 16px 14px;color:var(--ink-2)}
.report-cta{margin:48px 0 0;padding:24px;border-radius:var(--radius);background:var(--ink);color:#E2E8F0}
.report-cta h2{color:#fff;margin-top:0}
.report-cta h2::before{background:var(--amber)}
.report-cta p{color:#E2E8F0;max-width:60ch}
.report-cta .btn{border-color:#fff;color:#fff}
.report-cta .btn:hover{background:#fff;color:var(--ink)}
.site-footer{background:var(--ink);color:#CBD5E1;font-size:14px;padding:28px 0 36px;margin-top:56px}
.site-footer a{color:#99F6E4}
.foot-title{color:#fff;font-weight:700;font-size:16px;margin:0 0 6px}
.foot-links{display:flex;flex-wrap:wrap;gap:8px 18px;margin:12px 0 0}
.visually-hidden{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
dd,p,li,h1,h2,h3{overflow-wrap:anywhere}
td a{white-space:nowrap}
@media (min-width:640px){.stats{grid-template-columns:repeat(4,minmax(0,1fr))}.hero{padding:60px 20px 52px}main{padding-bottom:64px}dl{grid-template-columns:max-content minmax(0,1fr)}dt{margin-top:0}}
@media (min-width:900px){.site-header nav{gap:6px 24px}}
@media (max-width:640px){.hero{margin:0 -16px;padding:32px 16px 28px}.wrap{padding:0 16px}.bar{padding:12px 16px}.finding{padding:14px}.report-cta{padding:20px}.brand{font-size:17px}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}.card:hover{transform:none}}
@media (max-width:640px){table.stack{min-width:0}table.stack thead{position:absolute;left:-9999px}table.stack tr{display:block;padding:10px 12px;border-bottom:1px solid var(--line)}table.stack td{display:block;border:0;padding:3px 0}table.stack td::before{content:attr(data-label);display:block;font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.04em}}
@media print{.site-header,.site-footer,.skip,.cta,.hero-search,.report-cta{display:none}body{font-size:12px}}
"""


JS = """(function () {
  var input = document.getElementById('provider-search');
  if (!input) { return; }
  var items = Array.prototype.slice.call(document.querySelectorAll('#provider-list [data-provider]'));
  var status = document.getElementById('search-status');
  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    var shown = 0;
    items.forEach(function (el) {
      var hit = !q || el.getAttribute('data-provider').indexOf(q) !== -1;
      el.hidden = !hit;
      if (hit) { shown += 1; }
    });
    if (status) { status.textContent = shown + (shown === 1 ? ' provider' : ' providers') + ' shown'; }
  });
})();
"""

FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" '
           'fill="#0F766E"/><text x="32" y="45" font-size="40" text-anchor="middle" fill="#fff" '
           'font-family="Arial, sans-serif" font-weight="700">$</text></svg>\n')


def write_extras():
    (OUT / 'data').mkdir(parents=True, exist_ok=True)
    for name in ('registry.json', 'quickhits.json', 'verification.json'):
        shutil.copyfile(ROOT / 'data' / name, OUT / 'data' / name)
    (OUT / 'CNAME').write_text(CUSTOM_DOMAIN + chr(10), encoding='utf-8')
    (OUT / '.nojekyll').write_text('', encoding='utf-8')


def build_all():
    OUT.mkdir(parents=True, exist_ok=True)
    build_index()
    build_fronts()
    build_providers()
    build_verification()
    build_changes()
    build_404()
    write_static()
    write_extras()


if __name__ == '__main__':
    if '--check' in sys.argv:
        published = OUT
        OUT = Path(tempfile.mkdtemp(prefix='site-check-'))
        build_all()
        stale = []
        for f in sorted(p for p in OUT.rglob('*') if p.is_file()):
            rel = f.relative_to(OUT)
            target = published / rel
            if not target.exists() or target.read_bytes() != f.read_bytes():
                stale.append(rel.as_posix())
        if stale:
            print('stale output, rebuild with: python tools/build_site.py')
            for s in stale[:25]:
                print('  ' + s)
            sys.exit(1)
        print(f'check passed: {len(PAGES)} generated files match docs/')
    else:
        build_all()
        print(f'pages written: {len(PAGES)} (fronts {sum(1 for p in PAGES if p.startswith("fronts/"))}, '
              f'providers {sum(1 for p in PAGES if p.startswith("providers/"))})')
        print('sitemap urls:', sum(1 for p in PAGES if not p.startswith('404')))
