#!/usr/bin/env python3
"""Generate the animated SVG assets used by README.md.

Everything is self-hosted (no third-party image services), so the profile
never breaks when an external API is down or rate-limited.

Usage:  python scripts/make_assets.py            # animated
        STATIC=1 python scripts/make_assets.py   # frozen frames (for previews)
Edit the CONFIG block below, re-run, commit the files in assets/.
"""
import os
import math
import textwrap
from html import escape
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
(ASSETS / "projects").mkdir(parents=True, exist_ok=True)
STATIC = os.environ.get("STATIC") == "1"

# --------------------------------------------------------------------------
# CONFIG - edit freely
# --------------------------------------------------------------------------
NAME = "Chí Thắng"
HANDLE = "CThawngs"
ROLES = [
    "Solo AI Product Builder",
    "Full-stack Web Developer",
    "Vibe-coding with AI Agents",
    "Student from Ho Chi Minh City",
]
CARD_ROWS = [  # (key, value)  - keep values <= ~50 characters
    ("Name", "Chí Thắng (CThawngs)"),
    ("Role", "Solo AI product builder · Student"),
    ("Location", "Ho Chi Minh City, Vietnam"),
    ("Now", "Zero Council · multi-agent AI decision app"),
    ("Prev", "ReactJS internship · client web projects"),
    ("Stack", "TypeScript · Next.js · React · Python · C#"),
    ("AI Tools", "Claude Code · Hermes · Codex · Cursor"),
    ("Focus", "AI agents · automation · web apps"),
    ("Contact", "nguyenchithang2804@gmail.com"),
]
SKILLS = [  # (group, colour, items)
    ("Languages", "#2dd4bf", ["TypeScript", "JavaScript", "Python", "C#", "C", "C++", "Java", "PHP"]),
    ("Web & Frameworks", "#60a5fa", ["React", "Next.js", "Tailwind CSS", "HTML", "CSS", "REST APIs"]),
    ("Data", "#fbbf24", ["MySQL", "SQLite"]),
    ("AI & Automation", "#a78bfa", ["AI Agents", "Claude Code", "n8n", "Make", "Notion API"]),
    ("Design", "#f472b6", ["Canva", "Photoshop", "Google Stitch"]),
    ("Dev Tools", "#34d399", ["Git", "GitHub", "GitHub Actions (CI/CD)"]),
]
# (repo, description, language, template?)
# (repo, description, language, template?, featured?)
PROJECTS = [
    ("Zero-Council", "Multi-agent AI decision-support web app. My primary university specialized project (Đồ án Chuyên ngành).", "TypeScript", False, True),
    ("Netflix", "Modern, responsive Netflix clone showcasing dynamic design and AI-enhanced coding.", "CSS", False, False),
    ("Gemini-Chatbot", "A website that integrates an AI chatbot by calling the Gemini API.", "JavaScript", True, False),
    ("Calculator", "User-friendly web app for quick, basic arithmetic: add, subtract, multiply, divide.", "CSS", False, False),
    ("Apple-Store-Website", "Web design code recreating the look and feel of the Apple Store website.", "HTML", True, False),
    ("Website-SuperCars-1-Page", "One-page website showcasing supercars with a bold visual layout.", "HTML", False, False),
    ("The-Band", "Band website built with HTML and CSS: a clean, responsive landing page.", "CSS", False, False),
    ("Nails-Hair_Yen_Nga", "Practical nails & hair website I developed for a real client.", "HTML", False, False),
    ("Todo-App", "My first task using ReactJS during my internship.", "JavaScript", False, False),
    ("Women-Day", "Happy October 20th: glowing pink clouds with hearts falling like rain.", "CSS", False, False),
]
LANG_COLORS = {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "CSS": "#9b6bd6",
               "HTML": "#e34c26", "Python": "#3572a5"}

# palette
TEAL, VIOLET, PINK, BLUE = "#2dd4bf", "#a78bfa", "#f472b6", "#60a5fa"
BG, PANEL, BORDER, TEXT, MUTED = "#0d1117", "#161b22", "#30363d", "#e6edf3", "#8b949e"
SANS = "-apple-system,'Segoe UI',Helvetica,Arial,'Noto Sans',sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"


def write(path, svg):
    Path(path).write_text(svg, encoding="utf-8")
    print("wrote", Path(path).relative_to(ROOT), f"({len(svg)//1024 or 1} KB)")


def anim(tag_attrs, static_value=None):
    """Return an <animate*/> element, or '' when STATIC preview is on."""
    return "" if STATIC else f"<{tag_attrs}/>"


# --------------------------------------------------------------------------
# 1. HEADER BANNER
# --------------------------------------------------------------------------
def make_header():
    W, H = 960, 250
    n = len(ROLES)
    cycle = 4.6 * n
    cw = 13.2  # monospace char width at 22px
    typing = []
    for i, role in enumerate(ROLES):
        text = "> " + role
        wc = len(text) * cw
        x0 = (W - wc) / 2
        t0, ta, tb, tc = i / n, i / n + 0.30 / n, i / n + 0.80 / n, i / n + 0.92 / n
        pts = [(0.0, 0.0)] if t0 > 0 else []
        pts += [(t0, 0.0), (ta, wc), (tb, wc), (tc, 0.0), (1.0, 0.0)]
        kt = ";".join(f"{p[0]:.4f}" for p in pts)
        wv = ";".join(f"{p[1]:.1f}" for p in pts)
        xv = ";".join(f"{x0 + p[1]:.1f}" for p in pts)
        first_w = wc if STATIC and i == 0 else 0
        typing.append(f"""
  <clipPath id="clip{i}"><rect x="{x0:.1f}" y="170" height="44" width="{first_w:.1f}">
    {anim(f'animate attributeName="width" dur="{cycle}s" repeatCount="indefinite" keyTimes="{kt}" values="{wv}"')}
  </rect></clipPath>
  <text x="{x0:.1f}" y="200" font-family="{MONO}" font-size="22" fill="{TEXT}" clip-path="url(#clip{i})" xml:space="preserve"><tspan fill="{TEAL}">&gt;</tspan> {escape(role)}</text>
  <g opacity="{1 if (STATIC and i == 0) else 0}">
    {anim(f'animate attributeName="opacity" dur="{cycle}s" repeatCount="indefinite" keyTimes="0;{max(t0,0.0001):.4f};{max(t0,0.0001)+0.001:.4f};{tc:.4f};{tc+0.001:.4f};1" values="0;0;1;1;0;0"') if i else anim(f'animate attributeName="opacity" dur="{cycle}s" repeatCount="indefinite" keyTimes="0;{tc:.4f};{tc+0.001:.4f};1" values="1;1;0;0"')}
    <rect y="175" width="2.5" height="28" fill="{TEAL}">
      {anim(f'animate attributeName="x" dur="{cycle}s" repeatCount="indefinite" keyTimes="{kt}" values="{xv}"')}
      {anim('animate attributeName="opacity" dur="0.9s" repeatCount="indefinite" values="1;1;0;0" keyTimes="0;0.5;0.5001;1"')}
    </rect>
  </g>""")

    symbols = [("&lt;/&gt;", 70, 70, 28, 11), ("{ }", 880, 60, 30, 13), ("AI", 150, 200, 26, 9),
               ("=&gt;", 820, 190, 24, 12), ("01", 40, 150, 20, 10), ("#", 905, 135, 26, 8),
               ("fn()", 300, 38, 18, 14), ("git", 665, 40, 18, 10)]
    sym_svg = ""
    for s, x, y, size, d in symbols:
        sym_svg += (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" fill="{TEAL}" opacity="0.16">{s}'
                    + anim(f'animateTransform attributeName="transform" type="translate" values="0 0;0 -10;0 0" dur="{d}s" repeatCount="indefinite"')
                    + "</text>\n")

    def orb(cx, cy, r, color, dx, dy, dur):
        return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="0.38" filter="url(#blur)">'
                + anim(f'animate attributeName="cx" values="{cx};{cx+dx};{cx}" dur="{dur}s" repeatCount="indefinite"')
                + anim(f'animate attributeName="cy" values="{cy};{cy+dy};{cy}" dur="{dur*1.3:.1f}s" repeatCount="indefinite"')
                + "</circle>")

    fade = lambda begin, dur="0.9s": (anim(f'animate attributeName="opacity" from="0" to="1" begin="{begin}s" dur="{dur}" fill="freeze"')
                                      + anim(f'animateTransform attributeName="transform" type="translate" from="0 14" to="0 0" begin="{begin}s" dur="{dur}" fill="freeze"'))
    init = 0 if not STATIC else 1

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{NAME} ({HANDLE}) - {', '.join(ROLES)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a0f1f"/><stop offset="0.55" stop-color="#131a33"/><stop offset="1" stop-color="#0b1a26"/></linearGradient>
    <linearGradient id="name" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{TEAL}"/><stop offset="0.5" stop-color="{BLUE}"/><stop offset="1" stop-color="{VIOLET}"/>
      {anim('animate attributeName="x1" values="0;1;0" dur="8s" repeatCount="indefinite"')}</linearGradient>
    <linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{TEAL}" stop-opacity="0"/><stop offset="0.5" stop-color="{TEAL}"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#fff" stroke-opacity="0.045"/></pattern>
    <filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="38"/></filter>
    <clipPath id="round"><rect width="{W}" height="{H}" rx="18"/></clipPath>
  </defs>
  <g clip-path="url(#round)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    {orb(160, 70, 90, TEAL, 120, 40, 14)}
    {orb(560, 230, 100, VIOLET, -140, -50, 18)}
    {orb(840, 60, 85, PINK, -90, 60, 16)}
    <rect width="{W}" height="{H}" fill="url(#grid)"/>
    {sym_svg}
    <g opacity="{init}">{fade(0.1)}
      <text x="{W/2}" y="62" text-anchor="middle" font-family="{SANS}" font-size="19" fill="{MUTED}" letter-spacing="3">HI 👋  I'M</text></g>
    <g opacity="{init}">{fade(0.35)}
      <text x="{W/2}" y="128" text-anchor="middle" font-family="{SANS}" font-size="68" font-weight="800" fill="url(#name)" letter-spacing="1">{NAME}</text></g>
    <g opacity="{init}">{fade(0.6)}
      <text x="{W/2}" y="154" text-anchor="middle" font-family="{MONO}" font-size="16" fill="{MUTED}">@{HANDLE}</text></g>
    {''.join(typing)}
    <rect x="0" y="{H-3}" width="{W}" height="3" fill="url(#line)"/>
  </g>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="18" fill="none" stroke="{BORDER}"/>
</svg>"""
    write(ASSETS / "header.svg", svg)


# --------------------------------------------------------------------------
# 2. ASCII PORTRAIT (from scripts/source/portrait.png, a transparent cut-out)
# --------------------------------------------------------------------------
def make_portrait(cols=56, cw=6.0, rh=9.6, crop=(0.36, 0.0, 1.0, 0.43), min_height=0):
    import cv2
    RAMP = " .'`^:;-~+=*xoO#%@"
    im = Image.open(ROOT / "scripts/source/portrait.png").convert("RGBA")
    alpha = im.split()[3]
    bbox = alpha.point(lambda v: 255 if v > 128 else 0).getbbox()
    im = im.crop(bbox)
    # head & shoulders crop so the face stays readable at ASCII resolution
    cx0, cy0, cx1, cy1 = crop
    im = im.crop((int(im.width * cx0), int(im.height * cy0), int(im.width * cx1), int(im.height * cy1)))
    alpha = im.split()[3]
    rows = round(cols * (im.height / im.width) * (cw / rh))
    # local contrast (CLAHE) on luminance, like the blog's pipeline
    gray = np.asarray(im.convert("L"))
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6))
    lum = Image.fromarray(clahe.apply(gray))
    edges = lum.filter(ImageFilter.FIND_EDGES)
    lum_s = np.asarray(lum.resize((cols, rows), Image.LANCZOS), dtype=float) / 255
    edg_s = np.asarray(edges.resize((cols, rows), Image.LANCZOS), dtype=float) / 255
    a_s = np.asarray(alpha.resize((cols, rows), Image.LANCZOS), dtype=float) / 255
    out_rows = []
    for y in range(rows):
        line = []
        for x in range(cols):
            if a_s[y, x] < 0.45:
                line.append(" ")
                continue
            d = 0.12 + 0.70 * (lum_s[y, x] ** 1.6) + 1.8 * edg_s[y, x]
            d = max(0.0, min(0.999, d))
            line.append(RAMP[int(d * (len(RAMP) - 1)) + 1 if d > 0.02 else 1])
        out_rows.append("".join(line))
    pad, W = 14, cols * cw + 28
    H = max(rows * rh + 2 * pad + 22 + 34, min_height)
    clips, texts = [], []
    for i, line in enumerate(out_rows):
        y = pad + 22 + (i + 1) * rh - 2
        begin = 0.25 + i * 0.045
        width = cols * cw
        cw_attr = width if STATIC else 0
        clips.append(f'<clipPath id="r{i}"><rect x="{pad}" y="{y-rh+1:.1f}" height="{rh:.1f}" width="{cw_attr}">'
                     + anim(f'animate attributeName="width" from="0" to="{width}" begin="{begin:.2f}s" dur="0.9s" fill="freeze"')
                     + "</rect></clipPath>")
        texts.append(f'<text x="{pad}" y="{y:.1f}" clip-path="url(#r{i})" xml:space="preserve">{escape(line)}</text>')
        if not STATIC:
            texts.append(f'<rect y="{y-rh+1:.1f}" width="{cw}" height="{rh-1:.1f}" fill="{TEAL}" opacity="0">'
                         f'<animate attributeName="x" from="{pad}" to="{pad+width}" begin="{begin:.2f}s" dur="0.9s" fill="freeze"/>'
                         f'<animate attributeName="opacity" values="0.9;0.9;0" keyTimes="0;0.97;1" begin="{begin:.2f}s" dur="0.9s" fill="freeze"/></rect>')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="ASCII portrait of {NAME}">
  <defs>{''.join(clips)}
    <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9be9ff"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>
  <rect x="0.5" y="0.5" width="{W-1:.0f}" height="{H-1:.0f}" rx="12" fill="#0b1020" stroke="{BORDER}"/>
  <circle cx="18" cy="17" r="4.5" fill="#ff5f56"/><circle cx="33" cy="17" r="4.5" fill="#ffbd2e"/><circle cx="48" cy="17" r="4.5" fill="#27c93f"/>
  <text x="{W-14:.0f}" y="21" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{MUTED}">portrait.txt</text>
  <g font-family="{MONO}" font-size="10" fill="url(#pg)">{''.join(texts)}</g>
  <circle cx="{pad+4}" cy="{H-20:.0f}" r="4" fill="#27c93f">{anim('animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"')}</circle>
  <text x="{pad+14}" y="{H-16:.0f}" font-family="{MONO}" font-size="11.5" fill="{MUTED}">{HANDLE} · open to opportunities</text>
</svg>"""
    write(ASSETS / "ascii-portrait.svg", svg)
    return H


# --------------------------------------------------------------------------
# 3. NEOFETCH-STYLE INFO CARD
# --------------------------------------------------------------------------
def make_card(height):
    W = 540
    fs, lh, x_key, x_val = 13, 26, 24, 118
    y0 = 112
    rows = []
    for i, (k, v) in enumerate(CARD_ROWS):
        y = y0 + i * lh
        begin = 0.5 + i * 0.16
        o = 1 if STATIC else 0
        rows.append(f'<g opacity="{o}">'
                    + anim(f'animate attributeName="opacity" from="0" to="1" begin="{begin:.2f}s" dur="0.45s" fill="freeze"')
                    + anim(f'animateTransform attributeName="transform" type="translate" from="-10 0" to="0 0" begin="{begin:.2f}s" dur="0.45s" fill="freeze"')
                    + f'<text x="{x_key}" y="{y}" fill="{TEAL}" font-weight="700">{escape(k)}</text>'
                    + f'<text x="{x_val}" y="{y}" fill="{TEXT}">{escape(v)}</text></g>')
    y_pal = y0 + len(CARD_ROWS) * lh + 14
    pal = ["#ff5f56", "#ffbd2e", "#27c93f", TEAL, BLUE, VIOLET, PINK, "#e6edf3"]
    pal_svg = "".join(f'<rect x="{x_key + i*30}" y="{y_pal}" width="26" height="14" rx="3" fill="{c}"/>' for i, c in enumerate(pal))
    H = max(height, y_pal + 40)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}" role="img" aria-label="About {NAME}">
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1:.0f}" rx="12" fill="#0b1020" stroke="{BORDER}"/>
  <path d="M0.5 12.5a12 12 0 0 1 12-12H{W-12.5}a12 12 0 0 1 12 12V34H0.5z" fill="{PANEL}"/>
  <circle cx="18" cy="17" r="4.5" fill="#ff5f56"/><circle cx="33" cy="17" r="4.5" fill="#ffbd2e"/><circle cx="48" cy="17" r="4.5" fill="#27c93f"/>
  <text x="{W/2}" y="21" text-anchor="middle" font-family="{MONO}" font-size="11" fill="{MUTED}">{HANDLE.lower()}@github: ~ — zsh</text>
  <g font-family="{MONO}" font-size="{fs}" xml:space="preserve">
    <text x="{x_key}" y="56" fill="{MUTED}"><tspan fill="{TEAL}">$</tspan> neofetch</text>
    <text x="{x_key}" y="{y0-26}" fill="{VIOLET}" font-weight="700" font-size="14">{HANDLE.lower()}@github</text>
    <text x="{x_key}" y="{y0-12}" fill="{MUTED}" font-size="11">{"─" * 38}</text>
    {''.join(rows)}
    {pal_svg}
    <text x="{x_key}" y="{y_pal+38 if y_pal+38 < H-8 else H-10:.0f}" fill="{MUTED}" font-size="12"><tspan fill="{TEAL}">$</tspan> <tspan>open to internships &amp; collaborations</tspan>
      {anim('animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5001;1" dur="1s" repeatCount="indefinite"') if False else ''}</text>
  </g>
</svg>"""
    write(ASSETS / "info-card.svg", svg)


# --------------------------------------------------------------------------
# 4. SKILLS
# --------------------------------------------------------------------------
def make_skills():
    W = 860
    fs, pad_x, h, gap = 13, 13, 30, 10
    label_w = 150
    y = 14
    out, idx = [], 0
    for group, color, items in SKILLS:
        x = label_w
        out.append(f'<text x="0" y="{y+h/2+4:.0f}" font-family="{MONO}" font-size="12.5" fill="{MUTED}">{escape(group)}</text>')
        row_y = y
        for it in items:
            w = len(it) * 7.9 + 40
            if x + w > W:
                x = label_w
                row_y += h + gap
            begin = idx * 0.35  # pills are always visible; only the dot softly pulses
            idx += 1
            out.append('<g>'
                       + f'<rect x="{x:.0f}" y="{row_y}" width="{w:.0f}" height="{h}" rx="{h/2}" fill="{color}" fill-opacity="0.12" stroke="{color}" stroke-opacity="0.55"/>'
                       + f'<circle cx="{x+14:.0f}" cy="{row_y+h/2}" r="3" fill="{color}">'
                       + anim(f'animate attributeName="opacity" values="1;0.25;1" dur="3.2s" begin="{begin:.2f}s" repeatCount="indefinite"')
                       + '</circle>'
                       + f'<text x="{x+24:.0f}" y="{row_y+h/2+4.5}" font-family="{SANS}" font-size="{fs}" font-weight="600" fill="{TEXT}">{escape(it)}</text></g>')
            x += w + gap
        y = row_y + h + 20
    H = y - 6
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H:.0f}" viewBox="0 0 {W} {H:.0f}" role="img" '
           f'aria-label="Skills: {escape(", ".join(i for _, _, its in SKILLS for i in its))}">'
           + "".join(out) + "</svg>")
    write(ASSETS / "skills.svg", svg)


# --------------------------------------------------------------------------
# 5. PROJECT CARDS
# --------------------------------------------------------------------------
def card_svg(name, desc, lang, template, w, h, featured=False):
    wrap = 52
    lines = textwrap.wrap(desc, wrap)[:3]
    dlines = "".join(f'<text x="22" y="{58 + i*19}" font-family="{SANS}" font-size="13" fill="{MUTED}">{escape(l)}</text>'
                     for i, l in enumerate(lines))
    lc = LANG_COLORS.get(lang, MUTED)
    tag = ""
    if template:
        tag = (f'<rect x="{w-92}" y="14" width="70" height="20" rx="10" fill="none" stroke="{BORDER}"/>'
               f'<text x="{w-57}" y="28" text-anchor="middle" font-family="{SANS}" font-size="11" fill="{MUTED}">Template</text>')
    if featured:
        tag = (f'<rect x="{w-112}" y="14" width="92" height="22" rx="11" fill="{TEAL}" fill-opacity="0.14" stroke="{TEAL}" stroke-opacity="0.6"/>'
               f'<text x="{w-66}" y="29" text-anchor="middle" font-family="{SANS}" font-size="11.5" font-weight="700" fill="{TEAL}">★ FEATURED</text>')
    shimmer = anim(f'animate attributeName="x" from="-{w}" to="{w}" dur="{6 if featured else 8}s" repeatCount="indefinite"')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Repository {escape(name)}: {escape(desc)}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{TEAL}" stop-opacity="0"/><stop offset="0.5" stop-color="{TEAL}"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>
  <clipPath id="c"><rect width="{w}" height="{h}" rx="12"/></clipPath></defs>
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="12" fill="#0b1020" stroke="{TEAL if featured else BORDER}" stroke-opacity="{0.55 if featured else 1}"/>
  <g clip-path="url(#c)"><rect x="-{w}" y="0" width="{w}" height="2.5" fill="url(#g)">{shimmer}</rect></g>
  <svg x="22" y="14" width="16" height="16" viewBox="0 0 16 16"><path fill="{BLUE}" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/></svg>
  <text x="46" y="27" font-family="{SANS}" font-size="{16 if featured else 15}" font-weight="700" fill="{BLUE}">{escape(name)}</text>
  {tag}
  {dlines}
  <circle cx="26" cy="{h-22}" r="5.5" fill="{lc}"/>
  <text x="38" y="{h-17.5}" font-family="{SANS}" font-size="12" fill="{MUTED}">{escape(lang)}</text>
  <text x="{w-22}" y="{h-17.5}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{TEAL}">view repo ↗</text>
</svg>"""


def make_projects():
    for name, desc, lang, tpl, feat in PROJECTS:
        write(ASSETS / "projects" / f"{name}.svg", card_svg(name, desc, lang, tpl, 424, 132, featured=feat))


# --------------------------------------------------------------------------
# 6. FOOTER WAVE
# --------------------------------------------------------------------------
def make_footer():
    W, H, P = 960, 130, 480

    def wave(amp, off, color, op, dur, y):
        pts = " ".join(f"L{x} {y + amp*math.sin((x/P)*2*math.pi + off):.1f}" for x in range(-P, W + P + 1, 20))
        d = f"M-{P} {H} {pts} L{W+P} {H} Z"
        a = anim(f'animateTransform attributeName="transform" type="translate" from="0 0" to="-{P} 0" dur="{dur}s" repeatCount="indefinite"')
        return f'<path d="{d}" fill="{color}" fill-opacity="{op}">{a}</path>'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Thanks for visiting">
  <defs><linearGradient id="t" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{TEAL}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>
  {wave(10, 0, TEAL, 0.18, 9, 70)}{wave(8, 2, BLUE, 0.20, 13, 82)}{wave(7, 4, VIOLET, 0.28, 17, 94)}
  <text x="{W/2}" y="50" text-anchor="middle" font-family="{MONO}" font-size="15" fill="url(#t)">// thanks for stopping by — let's build something together ✦</text>
</svg>"""
    write(ASSETS / "footer.svg", svg)


if __name__ == "__main__":
    make_header()
    h = make_portrait(min_height=400)
    make_card(h)
    make_skills()
    make_projects()
    make_footer()
