#!/usr/bin/env python3
"""data/contributions.json -> assets/contrib-heatmap.svg  (GitHub-style, animated)

Run with --empty to render the placeholder shown before the first sync.
"""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "assets" / "contrib-heatmap.svg"

W = 860
CELL, GAP = 12, 3
LEFT, TOP = 38, 46
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MUTED, TEXT, TEAL = "#8b949e", "#e6edf3", "#2dd4bf"


def load(empty):
    if not empty and DATA.exists():
        return json.loads(DATA.read_text())
    end = date.today()
    start = end - timedelta(days=364)
    days = [{"date": (start + timedelta(days=i)).isoformat(), "count": 0, "level": 0} for i in range(365)]
    return {"days": days, "total": None, "longest_streak": None, "current_streak": None,
            "best_day": None, "best_count": 0, "placeholder": True}


def render(d):
    days = d["days"]
    first = datetime.fromisoformat(days[0]["date"]).date()
    lead = (first.weekday() + 1) % 7  # GitHub weeks start on Sunday
    cells, months, last_m = [], [], None
    for i, day in enumerate(days):
        pos = i + lead
        col, row = pos // 7, pos % 7
        x, y = LEFT + col * (CELL + GAP), TOP + row * (CELL + GAP)
        dt = datetime.fromisoformat(day["date"]).date()
        if dt.month != last_m and dt.day <= 7 and row <= 6:
            months.append((x, dt.strftime("%b")))
            last_m = dt.month
        tip = f'<title>{day["count"]} contributions on {dt.strftime("%b %d, %Y")}</title>'
        # cells are always visible (robust if animation is throttled/unsupported)
        cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{PALETTE[day["level"]]}">{tip}</rect>')
    grid_w = LEFT + (len(days) + lead + 6) // 7 * (CELL + GAP)
    grid_h = TOP + 7 * (CELL + GAP)
    H = grid_h + 62
    mlabels = "".join(f'<text x="{x}" y="{TOP-10}" font-family="{SANS}" font-size="11" fill="{MUTED}">{m}</text>' for x, m in months)
    dlabels = "".join(f'<text x="0" y="{TOP + r*(CELL+GAP) + 10}" font-family="{SANS}" font-size="10.5" fill="{MUTED}">{n}</text>'
                      for r, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")))
    legend_x = W - 20 - 5 * (CELL + 4) - 70
    legend = (f'<text x="{legend_x}" y="{grid_h+16}" font-family="{SANS}" font-size="11" fill="{MUTED}">Less</text>'
              + "".join(f'<rect x="{legend_x+32+i*(CELL+4)}" y="{grid_h+6}" width="{CELL}" height="{CELL}" rx="3" fill="{c}"/>' for i, c in enumerate(PALETTE))
              + f'<text x="{legend_x+32+5*(CELL+4)+4}" y="{grid_h+16}" font-family="{SANS}" font-size="11" fill="{MUTED}">More</text>')

    def stat(x, label, val):
        return (f'<text x="{x}" y="{grid_h+44}" font-family="{MONO}" font-size="12.5" fill="{MUTED}">{label} '
                f'<tspan fill="{TEXT}" font-weight="700">{val}</tspan></text>')

    dash = lambda v: "—" if v is None else v
    if d.get("placeholder"):
        stats_svg = (f'<text x="22" y="{grid_h+44}" font-family="{MONO}" font-size="12.5" fill="{MUTED}">'
                     f'⟳ waiting for first sync — run the “Update profile art” workflow once in the Actions tab</text>')
    else:
        best = f'{d["best_count"]} on {datetime.fromisoformat(d["best_day"]).strftime("%b %d")}' if d.get("best_day") else "—"
        stats_svg = (stat(22, "total", f'{d["total"]:,}') + stat(190, "current streak", f'{dash(d["current_streak"])}d')
                     + stat(400, "longest streak", f'{dash(d["longest_streak"])}d') + stat(630, "best day", best))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contribution heatmap for the last year">
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="#0b1020" stroke="#30363d"/>
  <text x="22" y="24" font-family="{MONO}" font-size="13" fill="{TEAL}">$ git log --since="1 year ago" --heatmap</text>
  <defs>
    <clipPath id="grid"><rect x="{LEFT}" y="{TOP}" width="{grid_w-LEFT}" height="{7*(CELL+GAP)}"/></clipPath>
    <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#7ee8d8" stop-opacity="0.22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  </defs>
  <g transform="translate({(W-grid_w)//2 + 4} 0)">{mlabels}{dlabels}{''.join(cells)}
    <g clip-path="url(#grid)"><rect x="{LEFT-140}" y="{TOP}" width="140" height="{7*(CELL+GAP)}" fill="url(#sweep)">
      <animate attributeName="x" from="{LEFT-140}" to="{grid_w}" dur="5s" begin="0s;sw.end+4s" id="sw"/>
    </rect></g>
  </g>
  <g>{legend}</g>
  {stats_svg}
</svg>"""
    OUT.write_text(svg, encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    render(load("--empty" in sys.argv))
