#!/usr/bin/env python3
"""build.py - profile.json + README.tpl.md  ->  README.md + assets/*.svg

Single source of truth: edit profile.json (content) or README.tpl.md (layout), then run
    python build.py            # normal: fetches GitHub data, falls back to data/*.json caches
    python build.py --offline  # never touch the network (uses caches only)
    python build.py --static   # frozen SVG frames, handy for previews/screenshots
GitHub Actions (.github/workflows/build.yml) runs this automatically on every push that touches
profile.json / README.tpl.md / build.py, and once a day to refresh the heatmap and repo cards.

Python standard library only - no pip install, no virtualenv.
"""
import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from html import escape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS, DATA = ROOT / "assets", ROOT / "data"
SANS = "-apple-system,'Segoe UI',Helvetica,Arial,'Noto Sans',sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

STATIC = False
OFFLINE = False
WRITTEN = set()
T = {}  # theme, filled from profile.json


def warn(msg):
    print("  ! " + msg, file=sys.stderr)


# ----------------------------------------------------------------------------------------------
# variables: {{a.b.0.c}} and {{list|join}} / {{list|join:4}} / {{text|cap}}
# ----------------------------------------------------------------------------------------------
TOKEN = re.compile(r"\{\{\s*([A-Za-z_][\w.]*)\s*(?:\|\s*(\w+)(?::(\d+))?)?\s*\}\}")


def lookup(cfg, path):
    cur = cfg
    for part in path.split("."):
        try:
            cur = cur[int(part)] if isinstance(cur, list) else cur[part]
        except (KeyError, IndexError, ValueError, TypeError):
            raise KeyError(f"variable '{path}' not found in profile.json")
    return cur


def interpolate(value, cfg):
    if isinstance(value, str):
        def sub(m):
            v = lookup(cfg, m.group(1))
            flt, n = m.group(2), m.group(3)
            if flt == "join":
                v = " · ".join(str(x) for x in (v[:int(n)] if n else v))
            elif flt == "cap":
                v = str(v)[:1].upper() + str(v)[1:]
            return str(v)
        for _ in range(6):  # nested references resolve over a few passes
            new = TOKEN.sub(sub, value)
            if new == value:
                break
            value = new
        return value
    if isinstance(value, list):
        return [interpolate(v, cfg) for v in value]
    if isinstance(value, dict):
        return {k: interpolate(v, cfg) for k, v in value.items()}
    return value


def load_config():
    raw = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    return interpolate(raw, raw)


# ----------------------------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------------------------
def esc(s):
    return escape(str(s), quote=True)


def tw(s, size, mono=False, bold=False):
    """rough text width in px"""
    return len(s) * size * (0.6 if mono else (0.585 if bold else 0.545))


def wrap_px(text, size, maxw, bold=False, mono=False, max_lines=None):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if tw(trial, size, mono, bold) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;:") + "…"
    return lines


def fit(text, size, maxw, mono=True):
    if tw(text, size, mono) <= maxw:
        return text
    while text and tw(text + "…", size, mono) > maxw:
        text = text[:-1]
    return text.rstrip() + "…"


def anim(markup):
    return "" if STATIC else f"<{markup}/>"


def write_svg(rel, svg):
    path = ASSETS / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    WRITTEN.add(path.resolve())
    print(f"  svg  assets/{rel}")


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")


def http_get(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-builder", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def github_repo_ref(url):
    """'https://github.com/owner/repo' -> 'owner/repo'; None if it is not a GitHub repo link."""
    if not url:
        return None
    m = re.match(r"https?://github\.com/([^/\s]+)/([^/\s#?]+)", url)
    return f"{m.group(1)}/{m.group(2)[:-4] if m.group(2).endswith('.git') else m.group(2)}" if m else None


def check_project_links(cfg):
    """Online mode: an open-source project whose GitHub repo answers 404 (deleted, or turned
    private) falls back to the portfolio link, so the README never links to a page that 404s.
    Closed-source projects are not checked: they link to their deployed site, not to a repo."""
    for p in cfg["projects"]:
        if p.get("visibility") == "private":
            continue
        ref = github_repo_ref(p.get("url"))
        if not ref:
            continue
        try:
            http_get(f"https://api.github.com/repos/{ref}", headers={"Accept": "application/vnd.github+json"})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                warn(f"project '{p['title']}': github.com/{ref} returned 404 (private or deleted) - using the portfolio link")
                p["url"] = None
            else:
                warn(f"project '{p['title']}': GitHub API returned HTTP {e.code} for {ref} - keeping the configured URL")
        except Exception as e:
            warn(f"project '{p['title']}': could not reach the GitHub API for {ref} ({e.__class__.__name__}) - keeping the configured URL")


def project_link(cfg, p):
    """(href, label) for a project card.

    closed source -> the deployed site (site), open source -> the GitHub repo (url),
    nothing usable -> the portfolio."""
    if p.get("visibility") == "private":
        site = p.get("site")
        return (site, "view site") if site else (cfg["links"]["portfolio"], "details on portfolio")
    url = p.get("url")
    return (url, "view repo") if url else (cfg["links"]["portfolio"], "details on portfolio")


# ----------------------------------------------------------------------------------------------
# data: contribution calendar + repo metadata (both cached in data/)
# ----------------------------------------------------------------------------------------------
class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.tips, self._tip, self._buf = {}, {}, None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "td" and a.get("data-date") and "ContributionCalendar-day" in (a.get("class") or ""):
            self.cells[a.get("id")] = (a["data-date"], int(a.get("data-level") or 0))
        elif tag == "tool-tip":
            self._tip, self._buf = a.get("for"), []

    def handle_data(self, data):
        if self._tip:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self._tip:
            self.tips[self._tip] = " ".join(self._buf).strip()
            self._tip = None


def parse_calendar(html_text):
    p = CalendarParser()
    p.feed(html_text)
    days = []
    for cid, (d, level) in p.cells.items():
        m = re.match(r"(\d+)", p.tips.get(cid, ""))
        days.append({"date": d, "count": int(m.group(1)) if m else 0, "level": level})
    days.sort(key=lambda x: x["date"])
    return days


def calendar_stats(days):
    total = sum(d["count"] for d in days)
    best = max(days, key=lambda d: d["count"], default=None)
    longest = cur = 0
    for d in days:
        cur = cur + 1 if d["count"] else 0
        longest = max(longest, cur)
    streak = 0
    for d in reversed(days):
        if d["count"]:
            streak += 1
        elif d["date"] == date.today().isoformat():
            continue
        else:
            break
    return {"total": total, "longest_streak": longest, "current_streak": streak,
            "best_day": best["date"] if best and best["count"] else None,
            "best_count": best["count"] if best else 0}


def get_contributions(handle):
    path = DATA / "contributions.json"
    if not OFFLINE:
        try:
            days = parse_calendar(http_get(f"https://github.com/users/{handle}/contributions"))
            if days:
                data = {"user": handle, "days": days, **calendar_stats(days)}
                write_json(path, data)
                return data
            warn("contribution calendar parsed to 0 days (GitHub markup changed?) - using cache")
        except Exception as e:
            warn(f"could not fetch contributions ({e}) - using cache")
    return read_json(path, None)


# ----------------------------------------------------------------------------------------------
# SVG: header
# ----------------------------------------------------------------------------------------------
def make_header(cfg):
    W, H = 960, 250
    p, hero = cfg["person"], cfg["hero"]
    roles = hero["roles"]
    n, cycle, cw = len(roles), 4.6 * len(roles), 13.2
    typing = []
    for i, role in enumerate(roles):
        text = "> " + role
        wc = len(text) * cw
        x0 = (W - wc) / 2
        t0, ta, tb, tc = i / n, i / n + 0.30 / n, i / n + 0.80 / n, i / n + 0.92 / n
        pts = ([(0.0, 0.0)] if t0 > 0 else []) + [(t0, 0.0), (ta, wc), (tb, wc), (tc, 0.0), (1.0, 0.0)]
        kt = ";".join(f"{a:.4f}" for a, _ in pts)
        wv = ";".join(f"{b:.1f}" for _, b in pts)
        xv = ";".join(f"{x0 + b:.1f}" for _, b in pts)
        first = wc if STATIC and i == 0 else 0
        vis_kt = f"0;{max(t0, 1e-4):.4f};{max(t0, 1e-4) + 0.001:.4f};{tc:.4f};{tc + 0.001:.4f};1"
        vis = (anim(f'animate attributeName="opacity" dur="{cycle}s" repeatCount="indefinite" keyTimes="{vis_kt}" values="0;0;1;1;0;0"') if i
               else anim(f'animate attributeName="opacity" dur="{cycle}s" repeatCount="indefinite" keyTimes="0;{tc:.4f};{tc + 0.001:.4f};1" values="1;1;0;0"'))
        typing.append(f"""
  <clipPath id="clip{i}"><rect x="{x0:.1f}" y="170" height="44" width="{first:.1f}">{anim(f'animate attributeName="width" dur="{cycle}s" repeatCount="indefinite" keyTimes="{kt}" values="{wv}"')}</rect></clipPath>
  <text x="{x0:.1f}" y="200" font-family="{MONO}" font-size="22" fill="{T['text']}" clip-path="url(#clip{i})" xml:space="preserve"><tspan fill="{T['teal']}">&gt;</tspan> {esc(role)}</text>
  <g opacity="{1 if (STATIC and i == 0) else 0}">{vis}<rect y="175" width="2.5" height="28" fill="{T['teal']}">{anim(f'animate attributeName="x" dur="{cycle}s" repeatCount="indefinite" keyTimes="{kt}" values="{xv}"')}{anim('animate attributeName="opacity" dur="0.9s" repeatCount="indefinite" values="1;1;0;0" keyTimes="0;0.5;0.5001;1"')}</rect></g>""")

    symbols = [("&lt;/&gt;", 70, 70, 28, 11), ("{ }", 880, 60, 30, 13), ("AI", 150, 200, 26, 9), ("=&gt;", 820, 190, 24, 12),
               ("01", 40, 150, 20, 10), ("#", 905, 135, 26, 8), ("fn()", 300, 38, 18, 14), ("git", 665, 40, 18, 10)]
    sym = "".join(f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{s}" fill="{T["teal"]}" opacity="0.16">{t}'
                  + anim(f'animateTransform attributeName="transform" type="translate" values="0 0;0 -10;0 0" dur="{d}s" repeatCount="indefinite"') + "</text>"
                  for t, x, y, s, d in symbols)

    def orb(cx, cy, r, color, dx, dy, dur):
        return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="0.38" filter="url(#blur)">'
                + anim(f'animate attributeName="cx" values="{cx};{cx + dx};{cx}" dur="{dur}s" repeatCount="indefinite"')
                + anim(f'animate attributeName="cy" values="{cy};{cy + dy};{cy}" dur="{dur * 1.3:.1f}s" repeatCount="indefinite"') + "</circle>")

    def fade(begin):
        return (anim(f'animate attributeName="opacity" from="0" to="1" begin="{begin}s" dur="0.9s" fill="freeze"')
                + anim(f'animateTransform attributeName="transform" type="translate" from="0 14" to="0 0" begin="{begin}s" dur="0.9s" fill="freeze"'))

    init = 1 if STATIC else 0
    label = f"{p['name']} ({p['handle']}): {', '.join(roles)}"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a0f1f"/><stop offset="0.55" stop-color="#131a33"/><stop offset="1" stop-color="#0b1a26"/></linearGradient>
    <linearGradient id="name" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{T['teal']}"/><stop offset="0.5" stop-color="{T['blue']}"/><stop offset="1" stop-color="{T['violet']}"/>{anim('animate attributeName="x1" values="0;1;0" dur="8s" repeatCount="indefinite"')}</linearGradient>
    <linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{T['teal']}" stop-opacity="0"/><stop offset="0.5" stop-color="{T['teal']}"/><stop offset="1" stop-color="{T['violet']}" stop-opacity="0"/></linearGradient>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#fff" stroke-opacity="0.045"/></pattern>
    <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="38"/></filter>
    <clipPath id="round"><rect width="{W}" height="{H}" rx="18"/></clipPath>
  </defs>
  <g clip-path="url(#round)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    {orb(160, 70, 90, T['teal'], 120, 40, 14)}{orb(560, 230, 100, T['violet'], -140, -50, 18)}{orb(840, 60, 85, T['pink'], -90, 60, 16)}
    <rect width="{W}" height="{H}" fill="url(#grid)"/>
    {sym}
    <g opacity="{init}">{fade(0.1)}<text x="{W / 2}" y="62" text-anchor="middle" font-family="{SANS}" font-size="19" fill="{T['muted']}" letter-spacing="3">{esc(hero['greeting'])}</text></g>
    <g opacity="{init}">{fade(0.35)}<text x="{W / 2}" y="128" text-anchor="middle" font-family="{SANS}" font-size="68" font-weight="800" fill="url(#name)" letter-spacing="1">{esc(p['name'])}</text></g>
    <g opacity="{init}">{fade(0.6)}<text x="{W / 2}" y="154" text-anchor="middle" font-family="{MONO}" font-size="16" fill="{T['muted']}">@{esc(p['handle'])}</text></g>
    {''.join(typing)}
    <rect x="0" y="{H - 3}" width="{W}" height="3" fill="url(#line)"/>
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{T['border']}"/>
</svg>"""
    write_svg("header.svg", svg)


# ----------------------------------------------------------------------------------------------
# SVG: ASCII portrait + info card (same height so they line up in the table)
# ----------------------------------------------------------------------------------------------
CARD_W, CARD_FS, CARD_LH, CHROME_H = 540, 13, 30, 34
PORTRAIT_CW, PORTRAIT_RH, PORTRAIT_PAD = 6.0, 9.6, 14


def make_portrait_and_card(cfg):
    p = cfg["person"]
    art = (DATA / "portrait.txt").read_text(encoding="utf-8").splitlines() if (DATA / "portrait.txt").exists() else []
    cols = max((len(l) for l in art), default=40)
    pw = cols * PORTRAIT_CW + 28
    art_h = len(art) * PORTRAIT_RH + 2 * PORTRAIT_PAD + 22 + 34
    rows = cfg["info_card"]
    H = round(max(art_h, CHROME_H + len(rows) * CARD_LH + 60))

    # ---- portrait: the art only, no filename label, no status caption
    clips, texts = [], []
    for i, line in enumerate(art):
        y = PORTRAIT_PAD + 22 + (i + 1) * PORTRAIT_RH - 2
        begin, width = 0.25 + i * 0.045, cols * PORTRAIT_CW
        clips.append(f'<clipPath id="r{i}"><rect x="{PORTRAIT_PAD}" y="{y - PORTRAIT_RH + 1:.1f}" height="{PORTRAIT_RH}" width="{width if STATIC else 0}">'
                     + anim(f'animate attributeName="width" from="0" to="{width}" begin="{begin:.2f}s" dur="0.9s" fill="freeze"') + "</rect></clipPath>")
        texts.append(f'<text x="{PORTRAIT_PAD}" y="{y:.1f}" clip-path="url(#r{i})" xml:space="preserve">{esc(line)}</text>')
        if not STATIC:
            texts.append(f'<rect y="{y - PORTRAIT_RH + 1:.1f}" width="{PORTRAIT_CW}" height="{PORTRAIT_RH - 1}" fill="{T["teal"]}" opacity="0">'
                         f'<animate attributeName="x" from="{PORTRAIT_PAD}" to="{PORTRAIT_PAD + width}" begin="{begin:.2f}s" dur="0.9s" fill="freeze"/>'
                         f'<animate attributeName="opacity" values="0.9;0.9;0" keyTimes="0;0.97;1" begin="{begin:.2f}s" dur="0.9s" fill="freeze"/></rect>')
    write_svg("ascii-portrait.svg", f"""<svg xmlns="http://www.w3.org/2000/svg" width="{pw:.0f}" height="{H}" viewBox="0 0 {pw:.0f} {H}" role="img" aria-label="ASCII portrait of {esc(p['name'])}">
  <defs>{''.join(clips)}<linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9be9ff"/><stop offset="1" stop-color="{T['violet']}"/></linearGradient></defs>
  <rect x="0.5" y="0.5" width="{pw - 1:.0f}" height="{H - 1}" rx="12" fill="{T['panel']}" stroke="{T['border']}"/>
  <circle cx="18" cy="17" r="4.5" fill="#ff5f56"/><circle cx="33" cy="17" r="4.5" fill="#ffbd2e"/><circle cx="48" cy="17" r="4.5" fill="#27c93f"/>
  <g font-family="{MONO}" font-size="10" fill="url(#pg)">{"".join(texts)}</g>
</svg>""")

    # ---- info card: key/value rows fill the frame - equal top/bottom padding, line height from what is left
    x_key, x_val = 24, 126
    maxw = CARD_W - x_val - 18
    pad = 22
    fs = CARD_FS
    lh = max((H - CHROME_H - 2 * pad - fs) / max(len(rows) - 1, 1), fs * 1.6)
    y0 = CHROME_H + pad + fs * 0.85
    out = []
    for i, (k, v) in enumerate(rows):
        y, begin = y0 + i * lh, 0.5 + i * 0.16
        v2 = fit(v, CARD_FS, maxw)
        if v2 != v:
            warn(f"info_card '{k}' is too long and was shortened: {v}")
        out.append(f'<g opacity="{1 if STATIC else 0}">'
                   + anim(f'animate attributeName="opacity" from="0" to="1" begin="{begin:.2f}s" dur="0.45s" fill="freeze"')
                   + anim(f'animateTransform attributeName="transform" type="translate" from="-10 0" to="0 0" begin="{begin:.2f}s" dur="0.45s" fill="freeze"')
                   + f'<text x="{x_key}" y="{y}" fill="{T["teal"]}" font-weight="700">{esc(k)}</text><text x="{x_val}" y="{y}" fill="{T["text"]}">{esc(v2)}</text></g>')
    label = f"{p['full_name']}, {p['role']}, {p['location']}"
    write_svg("info-card.svg", f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{H}" viewBox="0 0 {CARD_W} {H}" role="img" aria-label="{esc(label)}">
  <rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{H - 1}" rx="12" fill="{T['panel']}" stroke="{T['border']}"/>
  <path d="M0.5 12.5a12 12 0 0 1 12-12H{CARD_W - 12.5}a12 12 0 0 1 12 12V34H0.5z" fill="#161b22"/>
  <circle cx="18" cy="17" r="4.5" fill="#ff5f56"/><circle cx="33" cy="17" r="4.5" fill="#ffbd2e"/><circle cx="48" cy="17" r="4.5" fill="#27c93f"/>
  <g font-family="{MONO}" font-size="{CARD_FS}" xml:space="preserve">
    {''.join(out)}
  </g>
</svg>""")


# ----------------------------------------------------------------------------------------------
# SVG: project cards
# ----------------------------------------------------------------------------------------------
FOLDER = ('<path fill="{c}" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/>')


def card_frame(w, h, label, inner, shimmer_dur=8):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{T['teal']}" stop-opacity="0"/><stop offset="0.5" stop-color="{T['teal']}"/><stop offset="1" stop-color="{T['violet']}" stop-opacity="0"/></linearGradient>
  <clipPath id="c"><rect width="{w}" height="{h}" rx="12"/></clipPath></defs>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{T['panel']}" stroke="{T['border']}"/>
  <g clip-path="url(#c)"><rect x="-{w}" y="0" width="{w}" height="2.5" fill="url(#g)">{anim(f'animate attributeName="x" from="-{w}" to="{w}" dur="{shimmer_dur}s" repeatCount="indefinite"')}</rect></g>
  <svg x="22" y="14" width="16" height="16" viewBox="0 0 16 16">{FOLDER.format(c=T['blue'])}</svg>
  {inner}
</svg>"""


def project_card(proj, link_label):
    w, h = 424, 176
    lines = wrap_px(proj["description"], 13, w - 44, max_lines=3)
    desc = "".join(f'<text x="22" y="{70 + i * 18}" font-family="{SANS}" font-size="13" fill="{T["muted"]}">{esc(l)}</text>' for i, l in enumerate(lines))
    tags, x = "", 22
    for tag in proj["tags"]:
        tww = tw(tag, 10.5) + 16
        if x + tww > w - 20:
            break
        tags += (f'<rect x="{x:.0f}" y="{h - 52}" width="{tww:.0f}" height="20" rx="10" fill="{T["violet"]}" fill-opacity="0.12" stroke="{T["violet"]}" stroke-opacity="0.45"/>'
                 f'<text x="{x + tww / 2:.0f}" y="{h - 38}" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="{T["text"]}">{esc(tag)}</text>')
        x += tww + 6
    # classification pill on the date line (right): open source vs closed source
    closed = proj.get("visibility") == "private"
    vlabel, vcolor = ("closed source", T["pink"]) if closed else ("open source", T["teal"])
    vw = tw(vlabel, 10) + 16
    badge = (f'<rect x="{w - 22 - vw:.0f}" y="33" width="{vw:.0f}" height="19" rx="9.5" fill="{vcolor}" fill-opacity="0.12" stroke="{vcolor}" stroke-opacity="0.5"/>'
             f'<text x="{w - 22 - vw / 2:.0f}" y="47" text-anchor="middle" font-family="{SANS}" font-size="10" fill="{vcolor}">{esc(vlabel)}</text>')
    inner = (f'<text x="46" y="27" font-family="{SANS}" font-size="15" font-weight="700" fill="{T["blue"]}">{esc(proj["title"])}</text>'
             f'<text x="22" y="47" font-family="{MONO}" font-size="11" fill="{T["muted"]}">{esc(proj["date"])}</text>'
             f'{badge}{desc}{tags}<text x="{w - 22}" y="{h - 14}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{T["teal"]}">{esc(link_label)} ↗</text>')
    return card_frame(w, h, f"{proj['title']}: {proj['description']}", inner, 7)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ----------------------------------------------------------------------------------------------
# SVG: contribution heatmap + footer
# ----------------------------------------------------------------------------------------------
def make_heatmap(data):
    W, CELL, GAP, LEFT, TOP = 860, 12, 3, 38, 30  # no title line: grid sits near the top
    palette = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    placeholder = not data
    if placeholder:
        end = date.today()
        days = [{"date": (end - timedelta(days=364 - i)).isoformat(), "count": 0, "level": 0} for i in range(365)]
        data = {"days": days}
    days = data["days"]
    first = datetime.fromisoformat(days[0]["date"]).date()
    lead = (first.weekday() + 1) % 7
    cells, months, last_m = [], [], None
    for i, d in enumerate(days):
        pos = i + lead
        col, row = pos // 7, pos % 7
        x, y = LEFT + col * (CELL + GAP), TOP + row * (CELL + GAP)
        dt = datetime.fromisoformat(d["date"]).date()
        if dt.month != last_m and dt.day <= 7:
            months.append((x, dt.strftime("%b")))
            last_m = dt.month
        cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{palette[d["level"]]}"><title>{d["count"]} contributions on {dt.strftime("%b %d, %Y")}</title></rect>')
    grid_w = LEFT + (len(days) + lead + 6) // 7 * (CELL + GAP)
    grid_h = TOP + 7 * (CELL + GAP)
    H = grid_h + 62
    ml = "".join(f'<text x="{x}" y="{TOP - 10}" font-family="{SANS}" font-size="11" fill="{T["muted"]}">{m}</text>' for x, m in months)
    dl = "".join(f'<text x="0" y="{TOP + r * (CELL + GAP) + 10}" font-family="{SANS}" font-size="10.5" fill="{T["muted"]}">{n}</text>' for r, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")))
    lx = W - 20 - 5 * (CELL + 4) - 70
    legend = (f'<text x="{lx}" y="{grid_h + 16}" font-family="{SANS}" font-size="11" fill="{T["muted"]}">Less</text>'
              + "".join(f'<rect x="{lx + 32 + i * (CELL + 4)}" y="{grid_h + 6}" width="{CELL}" height="{CELL}" rx="3" fill="{c}"/>' for i, c in enumerate(palette))
              + f'<text x="{lx + 32 + 5 * (CELL + 4) + 4}" y="{grid_h + 16}" font-family="{SANS}" font-size="11" fill="{T["muted"]}">More</text>')

    def stat(x, label, val):
        return f'<text x="{x}" y="{grid_h + 44}" font-family="{MONO}" font-size="12.5" fill="{T["muted"]}">{label} <tspan fill="{T["text"]}" font-weight="700">{val}</tspan></text>'

    if placeholder:
        stats = f'<text x="22" y="{grid_h + 44}" font-family="{MONO}" font-size="12.5" fill="{T["muted"]}">⟳ waiting for the first sync (GitHub Actions runs build.py daily)</text>'
    else:
        best = f'{data["best_count"]} on {datetime.fromisoformat(data["best_day"]).strftime("%b %d")}' if data.get("best_day") else "—"
        stats = (stat(22, "total", f'{data["total"]:,}') + stat(190, "current streak", f'{data["current_streak"]}d')
                 + stat(400, "longest streak", f'{data["longest_streak"]}d') + stat(630, "best day", best))
    sweep = ""
    if not STATIC:
        sweep = (f'<g clip-path="url(#gridclip)"><rect x="{LEFT - 140}" y="{TOP}" width="140" height="{7 * (CELL + GAP)}" fill="url(#sweep)">'
                 f'<animate attributeName="x" from="{LEFT - 140}" to="{grid_w}" dur="5s" begin="0s;sw.end+4s" id="sw"/></rect></g>')
    write_svg("contrib-heatmap.svg", f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contribution heatmap for the last year">
  <defs><clipPath id="gridclip"><rect x="{LEFT}" y="{TOP}" width="{grid_w - LEFT}" height="{7 * (CELL + GAP)}"/></clipPath>
  <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#7ee8d8" stop-opacity="0.22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{T['panel']}" stroke="{T['border']}"/>
  <g transform="translate({(W - grid_w) // 2 + 4} 0)">{ml}{dl}{''.join(cells)}{sweep}</g>
  <g>{legend}</g>{stats}
</svg>""")


def make_footer(cfg):
    W, H, P = 960, 130, 480

    def wave(amp, off, color, op, dur, y):
        pts = " ".join(f"L{x} {y + amp * math.sin((x / P) * 2 * math.pi + off):.1f}" for x in range(-P, W + P + 1, 20))
        return (f'<path d="M-{P} {H} {pts} L{W + P} {H} Z" fill="{color}" fill-opacity="{op}">'
                + anim(f'animateTransform attributeName="transform" type="translate" from="0 0" to="-{P} 0" dur="{dur}s" repeatCount="indefinite"') + "</path>")

    text = cfg["footer"]["text"]
    write_svg("footer.svg", f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(text)}">
  <defs><linearGradient id="t" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{T['teal']}"/><stop offset="1" stop-color="{T['violet']}"/></linearGradient></defs>
  {wave(10, 0, T['teal'], 0.18, 9, 70)}{wave(8, 2, T['blue'], 0.20, 13, 82)}{wave(7, 4, T['violet'], 0.28, 17, 94)}
  <text x="{W / 2}" y="50" text-anchor="middle" font-family="{MONO}" font-size="15" fill="url(#t)">{esc(text)}</text>
</svg>""")


# ----------------------------------------------------------------------------------------------
# README
# ----------------------------------------------------------------------------------------------
def grid(cards):
    rows = []
    for i in range(0, len(cards), 2):
        tds = "".join(f'<td><a href="{esc(h)}"><img src="{s}" width="424" alt="{esc(a)}"></a></td>' for h, s, a in cards[i:i + 2])
        rows.append(f"  <tr>{tds}</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def build_blocks(cfg):
    badges = "\n".join(
        f'<a href="{esc(b["url"])}"><img src="https://img.shields.io/badge/{urllib.parse.quote(b["label"])}-%23{b["color"]}.svg?style=for-the-badge&logo={urllib.parse.quote(b["logo"])}&logoColor=white" alt="{esc(b["label"])}"></a>'
        for b in cfg["badges"])
    # the Projects grid shows the portfolio's featured projects, capped at 6
    cards = [(project_link(cfg, p)[0], f"assets/projects/{slug(p['title'])}.svg",
              f"{p['title']}: {p['description']}") for p in cfg["projects"][:6]]
    trophies = ""
    if cfg["trophies"]["enabled"]:
        trophies = f'<br><br>\n\n<h3>GitHub Trophies</h3>\n\n<img src="{esc(cfg["trophies"]["url"])}" alt="GitHub trophies" width="860">'
    counter = ""
    if cfg["visit_counter"]["enabled"]:
        counter = f'<a href="{esc(cfg["visit_counter"]["link"])}"><img src="{esc(cfg["visit_counter"]["url"])}" alt="Profile views"></a>\n'
    return {"badges": badges, "about": "\n".join("- " + a for a in cfg["about"]),
            "cards_grid": grid(cards), "trophies": trophies, "counter": counter}


def render_readme(cfg, blocks):
    tpl = (ROOT / "README.tpl.md").read_text(encoding="utf-8")
    tpl = re.sub(r"\{\{@(\w+)\}\}", lambda m: blocks[m.group(1)], tpl)
    out = interpolate(tpl, cfg)
    with open(ROOT / "README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print("  md   README.md")


# ----------------------------------------------------------------------------------------------
def main():
    global STATIC, OFFLINE, T
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", action="store_true")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    STATIC, OFFLINE = args.static, args.offline

    try:
        cfg = load_config()
    except KeyError as e:
        sys.exit(f"profile.json error: {e.args[0]}")
    T = cfg["theme"]
    print("Building profile ...")

    if not OFFLINE:
        check_project_links(cfg)

    make_header(cfg)
    make_portrait_and_card(cfg)
    for p in cfg["projects"][:6]:
        write_svg(f"projects/{slug(p['title'])}.svg", project_card(p, project_link(cfg, p)[1]))
    make_heatmap(get_contributions(cfg["person"]["handle"]) if not OFFLINE else read_json(DATA / "contributions.json", None))
    make_footer(cfg)
    render_readme(cfg, build_blocks(cfg))

    for f in ASSETS.rglob("*.svg"):  # remove SVGs that are no longer produced (renamed/removed items)
        if f.resolve() not in WRITTEN:
            f.unlink()
            print(f"  del  {f.relative_to(ROOT)}")
    print("Done.")


if __name__ == "__main__":
    main()
