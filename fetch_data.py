"""Collect public GitHub stats for the profile cards and save them to data.json.

Run:  python fetch_data.py [username]
Uses the public REST API (set GITHUB_TOKEN to raise the rate limit) and the public
contributions calendar page. No private data is read.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "mvpp12"
OUT = Path(__file__).parent / "data.json"

# Languages that describe markup or tooling rather than code you wrote
IGNORE_LANGS = {"CMake", "C++", "C", "Swift", "Objective-C", "Ruby", "Batchfile", "Shell", "Makefile", "Procfile"}


def get(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": f"{USER}-profile"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def contributions():
    html = get(f"https://github.com/users/{USER}/contributions", accept="text/html")
    levels = {}
    for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*id="([^"]+)"[^>]*data-level="(\d)"', html):
        levels[m.group(2)] = (m.group(1), int(m.group(3)))
    counts = {}
    for m in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        if m.group(1) in levels:
            n = re.match(r"(\d+) contribution", m.group(2))
            counts[m.group(1)] = int(n.group(1)) if n else 0
    days = sorted((d, counts.get(i, 0), lvl) for i, (d, lvl) in levels.items())
    return [{"date": d, "count": c, "level": lvl} for d, c, lvl in days]


def streaks(days):
    today = date.today().isoformat()
    counts = [d["count"] for d in days if d["date"] <= today]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    # Today may not have activity yet; don't break the streak on it
    tail = counts[:-1] if counts and counts[-1] == 0 else counts
    for c in reversed(tail):
        if not c:
            break
        current += 1
    return current, longest


def main():
    user = json.loads(get(f"https://api.github.com/users/{USER}"))
    repos = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"))
    own = [r for r in repos if not r["fork"]]

    langs = {}
    for r in own:
        for lang, n in json.loads(get(r["languages_url"])).items():
            if lang not in IGNORE_LANGS:
                langs[lang] = langs.get(lang, 0) + n
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:4]

    days = contributions()
    year_ago = (date.today() - timedelta(days=365)).isoformat()
    current, longest = streaks(days)

    data = {
        "user": USER,
        "updated": date.today().isoformat(),
        "public_repos": len(own),
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user["followers"],
        "contributions_year": sum(d["count"] for d in days if d["date"] > year_ago),
        "current_streak": current,
        "longest_streak": longest,
        "languages": [{"name": k, "share": v / total} for k, v in top],
        "days": days,
    }
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"wrote {OUT}: {data['public_repos']} repos, {data['contributions_year']} contributions, "
          f"streak {current}/{longest}, langs {[l['name'] for l in data['languages']]}, {len(days)} days")


if __name__ == "__main__":
    main()
