#!/usr/bin/env python3
"""Rewrite the <!--START_SECTION:activity--> block in README.md from
Abhinav1480's live public event feed.

Run by .github/workflows/recent-activity.yml. Every line written here comes
straight from the GitHub Events API — nothing is hand-typed or invented.

Why this exists instead of jamesgeorge007/github-activity-readme: that action
can only serialize Issue/PR/Release events, and this account's public feed is
almost entirely Push and Create events, so it always wrote nothing.
"""

import json
import os
import re
import sys
import urllib.request

USERNAME = os.environ.get("ACTIVITY_USERNAME", "Abhinav1480")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
MAX_LINES = int(os.environ.get("MAX_LINES", "10"))
TARGET_FILE = os.environ.get("TARGET_FILE", "README.md")

API = f"https://api.github.com/users/{USERNAME}/events/public?per_page=100"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "activity-readme",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

START = "<!--START_SECTION:activity-->"
END = "<!--END_SECTION:activity-->"


def link(repo):
    return f"[`{repo}`](https://github.com/{repo})"


def serialize(ev):
    """Turn one event into one markdown line, or None to skip it."""
    etype = ev.get("type")
    repo = (ev.get("repo") or {}).get("name", "")
    payload = ev.get("payload") or {}

    if etype == "PushEvent":
        count = payload.get("size") or payload.get("distinct_size") or 1
        branch = (payload.get("ref") or "").replace("refs/heads/", "")
        where = f"{link(repo)} on `{branch}`" if branch else link(repo)
        plural = "" if count == 1 else "s"
        return f"⬆️ Pushed {count} commit{plural} to {where}"

    if etype == "CreateEvent":
        ref_type = payload.get("ref_type", "repository")
        ref = payload.get("ref") or ""
        if ref_type == "repository":
            return f"📦 Created repository {link(repo)}"
        return f"📦 Created {ref_type} `{ref}` in {link(repo)}"

    if etype == "ForkEvent":
        forkee = (payload.get("forkee") or {}).get("full_name") or repo
        return f"🍴 Forked {link(forkee)} from {link(repo)}"

    if etype == "WatchEvent":
        return f"⭐ Starred {link(repo)}"

    if etype == "PullRequestEvent":
        number = (payload.get("pull_request") or {}).get("number")
        action = payload.get("action") or "updated"
        return f"💪 {action.capitalize()} PR [#{number}](https://github.com/{repo}/pull/{number}) in {link(repo)}"

    if etype == "IssuesEvent":
        number = (payload.get("issue") or {}).get("number")
        action = payload.get("action") or "updated"
        return f"❗ {action.capitalize()} issue [#{number}](https://github.com/{repo}/issues/{number}) in {link(repo)}"

    if etype == "IssueCommentEvent":
        number = (payload.get("issue") or {}).get("number")
        comment = (payload.get("comment") or {}).get("html_url")
        return f"🗣 Commented on [#{number}]({comment}) in {link(repo)}"

    if etype == "ReleaseEvent":
        release = payload.get("release") or {}
        name = release.get("name") or release.get("tag_name")
        url = release.get("html_url")
        return f"🚀 Released [{name}]({url}) in {link(repo)}"

    return None


def fetch_events():
    request = urllib.request.Request(API, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    events = fetch_events()

    lines = []
    seen = set()
    for event in events:  # newest first
        line = serialize(event)
        if not line or line in seen:
            continue
        seen.add(line)
        lines.append(line)
        if len(lines) >= MAX_LINES:
            break

    if not lines:
        print("Found no activity. Leaving README unchanged.")
        return

    with open(TARGET_FILE, encoding="utf-8") as handle:
        readme = handle.read()

    if START not in readme or END not in readme:
        sys.exit(f"Couldn't find the {START} / {END} markers in {TARGET_FILE}.")

    pattern = re.compile(f"({re.escape(START)})(.*?)({re.escape(END)})", re.S)
    new_section = "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))
    updated = pattern.sub(
        lambda match: f"{match.group(1)}\n{new_section}\n{match.group(3)}",
        readme,
    )

    if updated == readme:
        print("No changes detected.")
        return

    with open(TARGET_FILE, "w", encoding="utf-8") as handle:
        handle.write(updated)
    print(f"Wrote {len(lines)} activity lines to {TARGET_FILE}.")


if __name__ == "__main__":
    main()
