#!/usr/bin/env python3
"""Scrape the public contribution calendar (no token needed) -> data/contributions.json"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER = os.environ.get("GITHUB_USER", "CThawngs")
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"


def fetch(user):
    r = requests.get(f"https://github.com/users/{user}/contributions",
                     headers={"User-Agent": "profile-readme-bot"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.find_all("tool-tip")}
    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        m = re.match(r"(\d+)", tips.get(td.get("id"), ""))
        count = int(m.group(1)) if m else 0
        days.append({"date": td["data-date"], "count": count, "level": int(td.get("data-level", 0))})
    days.sort(key=lambda d: d["date"])
    return days


def stats(days):
    total = sum(d["count"] for d in days)
    best = max(days, key=lambda d: d["count"], default=None)
    longest = cur = 0
    for d in days:
        cur = cur + 1 if d["count"] > 0 else 0
        longest = max(longest, cur)
    # current streak: today may still be empty, so allow a one-day grace
    streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            streak += 1
        elif d["date"] == date.today().isoformat():
            continue
        else:
            break
    return {"total": total, "longest_streak": longest, "current_streak": streak,
            "best_day": best["date"] if best and best["count"] else None,
            "best_count": best["count"] if best else 0}


if __name__ == "__main__":
    days = fetch(USER)
    if not days:
        sys.exit("No contribution cells parsed - GitHub markup may have changed.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"user": USER, "days": days, **stats(days)}, indent=1))
    print(f"{len(days)} days, {stats(days)['total']} contributions")
