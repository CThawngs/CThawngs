#!/usr/bin/env python3
"""Generate README.md from data/profile.json + data/repos.json.

Run: python scripts/make_readme.py
Nothing about the layout, headings or socials is hardcoded here - edit
data/profile.json and re-run.
"""
import sys
from pathlib import Path

from profile_config import pins, profile, repos

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
WIDTH = 860


def check(p):
    """Fail loudly instead of shipping a README with a dead link."""
    cache = repos()
    missing = [n for n in p["pins"] if n not in cache]
    nocard = [n for n in p["pins"] if not (ROOT / "assets/projects" / f"{n}.svg").exists()]
    if missing:
        sys.exit(f"Pinned repos not found on GitHub: {missing} - fix data/profile.json pins")
    if nocard:
        sys.exit(f"No card generated for: {nocard} - run python scripts/make_assets.py")


def badges(p):
    return "\n".join(
        f'<a href="{s["url"]}"><img src="https://img.shields.io/badge/{s["label"]}-{s["color"]}.svg'
        f'?style=for-the-badge&logo={s["logo"]}&logoColor=white" alt="{s["label"]}"></a>'
        for s in p["socials"])


def project_grid(p):
    """Two-column <table>; one <td> per cell, odd count gets no filler cell."""
    cells = [
        (f'<a href="https://github.com/{p["user"]}/{name}">'
         f'<img src="assets/projects/{name}.svg" width="424" alt="{name}"></a>')
        for name, *_ in pins(p)
    ]
    rows = ["<table>"]
    for i in range(0, len(cells), 2):
        pair = cells[i:i + 2]
        tds = "".join(f"<td>{c}</td>" for c in pair)
        rows.append(f"  <tr>{tds}</tr>")
    rows.append("</table>")
    return "\n".join(rows)


def render():
    p = profile()
    s = p["sections"]

    about = "\n".join(f"- {line}" for line in p["about"])
    return f"""<div align="center">

<img src="assets/header.svg" width="100%" alt="{p['tagline']}">

<br>

{badges(p)}

<br><br>

<table>
  <tr>
    <td valign="top"><img src="assets/ascii-portrait.svg" alt="ASCII portrait of {p['name']}"></td>
    <td valign="top"><img src="assets/info-card.svg" alt="{p['name']} — {p['tagline']}"></td>
  </tr>
</table>

</div>

<br>

<h3 align="center">{s['about']}</h3>

{about}

<br>

<div align="center">

<h3>{s['skills']}</h3>

<img src="assets/skills.svg" width="{WIDTH}" alt="Skills">

<br><br>

<h3>{s['projects']}</h3>

{project_grid(p)}

<br>

<h3>{s['contributions']}</h3>

<img src="assets/contrib-heatmap.svg" width="{WIDTH}" alt="GitHub contribution heatmap for the last year">

<br><br>

<h3>{s['achievements']}</h3>

<img src="https://github-trophies.vercel.app/?username={p['user']}&theme=radical&no-frame=true&no-bg=true&margin-w=4&column=7" alt="GitHub trophies" width="{WIDTH}">

<br>

<img src="assets/footer.svg" width="100%" alt="Thanks for stopping by">

</div>
"""


if __name__ == "__main__":
    check(profile())
    README.write_text(render(), encoding="utf-8", newline="\n")
    print("wrote", README)