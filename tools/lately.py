#!/usr/bin/env python3
"""Fill the Lately section of the profile README with recent public work.

The public events feed used to carry commit messages and no longer does, so the
list is built from the repositories themselves: the most recently pushed public
repositories, and the newest commit on each. Private repositories are filtered
out explicitly rather than trusted to stay out, because this file writes into a
page anyone can read.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- lately:start -->"
END = "<!-- lately:end -->"
USER = os.environ.get("PROFILE_USER", "rmz-oz")
LIMIT = 5


def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-lately")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print("%s: %s" % (path, exc), file=sys.stderr)
        return None


def recent_work(user, limit):
    repos = api("/users/%s/repos?sort=pushed&per_page=30" % user) or []
    out = []
    for repo in repos:
        if repo.get("private") or repo.get("fork") or repo.get("archived"):
            continue
        commits = api("/repos/%s/commits?per_page=1" % repo["full_name"])
        if not commits:
            continue
        commit = commits[0]["commit"]
        out.append({
            "name": repo["name"],
            "url": repo["html_url"],
            "subject": commit["message"].splitlines()[0],
            "day": commit["committer"]["date"][:10],
        })
        if len(out) == limit:
            break
    return out


def render(entries):
    if not entries:
        return "Nothing public to show yet."
    lines = []
    for item in entries:
        subject = item["subject"]
        if len(subject) > 68:
            subject = subject[:67].rstrip() + "…"
        lines.append("- [%s](%s) · %s · %s" % (item["name"], item["url"], subject, item["day"]))
    return "\n".join(lines)


def main():
    text = README.read_text(encoding="utf-8")
    block = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not block.search(text):
        print("markers are missing from the README", file=sys.stderr)
        return 1

    body = render(recent_work(USER, LIMIT))
    updated = block.sub("%s\n%s\n%s" % (START, body, END), text)
    if updated == text:
        print("no change")
        return 0
    README.write_text(updated, encoding="utf-8")
    print("updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
