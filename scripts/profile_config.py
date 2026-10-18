"""Single source of truth for the profile README.

Everything user-editable lives in data/profile.json.
Everything repo-specific (description, language, stars) lives in
data/repos.json, refreshed from the GitHub API by scripts/fetch_repos.py.
No prose is invented here: if GitHub has no description, the card shows none.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "data" / "profile.json"
REPOS_PATH = ROOT / "data" / "repos.json"


def profile():
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def repos():
    """name -> repo metadata. Empty dict when the cache is missing."""
    if not REPOS_PATH.exists():
        return {}
    return {r["name"]: r for r in json.loads(REPOS_PATH.read_text(encoding="utf-8"))}


def pins(p=None, r=None):
    """[(name, description, language, is_template, is_featured)] for the README.

    Description comes from GitHub; data/profile.json "desc_overrides" fills the
    gap for repos GitHub has no description for. Nothing is invented here.
    Repos the user pinned but that no longer exist are skipped rather than
    rendering a dead link.
    """
    p = p or profile()
    cache = r if r is not None else repos()
    over = p.get("desc_overrides", {})
    out = []
    for name in p["pins"]:
        repo = cache.get(name)
        if repo is None:
            continue
        out.append((
            name,
            over.get(name) or repo.get("description") or "",
            repo.get("language") or "",
            name in p.get("templates", []),
            name == p.get("featured"),
        ))
    return out