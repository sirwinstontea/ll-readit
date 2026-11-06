# ll-readit

Private, lightweight, **read-only** Reddit script for a single account (u/readitgold). Not a public bot, not a community tool, not commercial.

- `python ll_readit.py replies` - my own recent posts and the replies I received.
- `python ll_readit.py ideas <sub> [<sub>...] [--query term]` - reads public top posts in subreddits I take part in and has an LLM brainstorm post *ideas* (titles + angles only).

## Compliance
- Official Data API via OAuth (PRAW), descriptive User-Agent, rate limits honored.
- No posting, commenting, voting or messaging. Code blocks every non-GET request.
- Hard cap of 90 API requests/day (counter in `state.json`).
- A human reads and edits every idea; nothing is ever posted automatically.
- Reddit data is not used to train or fine-tune any model, not sold, not shared. Post titles go to an LLM API for inference only when `ideas` is run.
- Local storage: post/comment IDs, subreddit names, daily request count only.

## Setup
`pip install -r requirements.txt`, create a "script" app at reddit.com/prefs/apps once approved, copy `.env.example` values into your environment.
