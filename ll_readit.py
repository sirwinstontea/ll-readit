#!/usr/bin/env python3
"""ll-readit: private, read-only Reddit helper for ONE account (u/readitgold).

What it does (and nothing else):
  replies  - show my own recent posts/comments and the replies/inbox items I received
  ideas    - read public posts in subreddits I take part in, then ask an LLM to
             brainstorm post ideas. Ideas are printed for me to read/edit myself.

What it never does: post, comment, vote, message, or any other write call.
There is no write code in this file. Nothing is posted automatically.
Hard cap on API requests per day (default 90, well under 100).
Reddit data is not used for model training, not sold, not shared.
Local storage: only post/comment IDs, subreddit names, and a daily request counter.
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

import praw

STATE = Path(__file__).with_name("state.json")
DAILY_CAP = int(os.environ.get("REDDIT_DAILY_REQUEST_CAP", "90"))
USER = os.environ.get("REDDIT_USERNAME", "readitgold")
USER_AGENT = f"script:ll-readit:v1.0 (personal read-only script by u/{USER})"


def load_state():
    try:
        s = json.loads(STATE.read_text())
    except (OSError, ValueError):
        s = {}
    today = datetime.date.today().isoformat()
    if s.get("day") != today:
        s = {"day": today, "requests": 0, "seen": s.get("seen", [])[-500:]}
    return s


def save_state(s):
    STATE.write_text(json.dumps(s))


def reddit_client(state):
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        username=USER,
        password=os.environ["REDDIT_PASSWORD"],
        user_agent=USER_AGENT,
        ratelimit_seconds=0,
    )
    reddit.read_only = False  # needed to read my own inbox; script still only calls GETs
    http = reddit._core._requestor._http
    orig = http.request

    def guarded(method, url, **kw):
        if method.upper() != "GET":  # hard guarantee: no writes (token fetch is exempt)
            if "access_token" not in url:
                raise RuntimeError(f"blocked non-GET request: {method} {url}")
        if state["requests"] >= DAILY_CAP:
            raise SystemExit(f"Daily request cap ({DAILY_CAP}) reached. Try tomorrow.")
        state["requests"] += 1
        return orig(method, url, **kw)

    http.request = guarded
    return reddit


def cmd_replies(reddit, state, limit):
    me = reddit.user.me()
    print(f"== My recent posts (u/{me.name}) ==")
    for p in me.submissions.new(limit=limit):
        print(f"[r/{p.subreddit}] {p.title}  ({p.num_comments} comments)  {p.id}")
    print("\n== Replies in my inbox ==")
    for item in reddit.inbox.comment_replies(limit=limit):
        mark = "" if item.id in state["seen"] else "NEW "
        body = item.body.replace("\n", " ")[:200]
        print(f"{mark}[r/{item.subreddit}] u/{item.author}: {body}  ({item.id})")
        if item.id not in state["seen"]:
            state["seen"].append(item.id)


def cmd_ideas(reddit, state, subs, limit, query):
    lines = []
    for name in subs:
        sub = reddit.subreddit(name)
        posts = sub.search(query, sort="top", time_filter="month", limit=limit) if query \
            else sub.top(time_filter="week", limit=limit)
        for p in posts:
            lines.append(f"r/{name}: {p.title}")
    if not lines:
        print("Nothing fetched.")
        return
    try:
        import anthropic
    except ImportError:
        print("Install `anthropic` for idea drafting. Titles fetched:\n" + "\n".join(lines))
        return
    prompt = (
        "These are recent top post titles from subreddits I already take part in:\n"
        + "\n".join(lines)
        + "\n\nBrainstorm 8 original post ideas I could write myself. Ideas only: a one-line "
        "title plus one line of angle each. No finished posts, no copying existing posts."
    )
    msg = anthropic.Anthropic().messages.create(
        model=os.environ.get("LLM_MODEL", "claude-sonnet-5-5"),
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    print("== Post ideas (review and edit; post manually, if at all) ==")
    print(msg.content[0].text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("replies")
    r.add_argument("--limit", type=int, default=10)
    i = sp.add_parser("ideas")
    i.add_argument("subs", nargs="+", help="subreddit names (no r/)")
    i.add_argument("--limit", type=int, default=10)
    i.add_argument("--query", help="optional search term")
    a = ap.parse_args()

    state = load_state()
    try:
        reddit = reddit_client(state)
        if a.cmd == "replies":
            cmd_replies(reddit, state, a.limit)
        else:
            cmd_ideas(reddit, state, a.subs, a.limit, a.query)
    finally:
        save_state(state)
        print(f"\n[requests today: {state['requests']}/{DAILY_CAP}]", file=sys.stderr)


if __name__ == "__main__":
    main()
