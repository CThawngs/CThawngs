#!/usr/bin/env python3
"""Refresh data/repos.json from the GitHub API (no token needed, public data).

Descriptions and languages come straight from GitHub, so project cards never
drift from the repos again.
"""
import json
import os
import sys
from pathlib import Path

import requests

USER = os.environ.get("GITHUB_USER", "CThawngs")
OUT = Path(__file__).resolve().parent.parent / "data" / "repos.json"
API = "https://api.github.com"


def main():
    r = requests.get(f"{API}/users/{USER}/repos",
                     params={"per_page": 100, "sort": "pushed"},
                     headers={"Accept": "application/vnd.github+json",
                              "User-Agent": "profile-readme-bot"},
                     timeout=30)
    r.raise_for_status()
    repos = [
        {"name": x["name"], "description": x.get("description"),
         "language": x.get("language"), "stars": x.get("stargazers_count", 0),
         "fork": x.get("fork", False), "archived": x.get("archived", False)}
        for x in r.json() if not x.get("fork")
    ]
    if not repos:
        sys.exit("GitHub API returned no repos - aborting without touching the cache.")
    OUT.write_text(json.dumps(repos, indent=1), encoding="utf-8")
    print(f"{len(repos)} repos -> {OUT}")


if __name__ == "__main__":
    main()