"""
reddit_research.py

Read-only Reddit research tools for Phase 0/1 community vetting (see
REDDIT_MCP_SPEC.md, this directory). Uses PRAW in application-only
(read-only) mode -- client_id + client_secret only, no account
password anywhere. No write-capable call (submit_post, submit_comment,
vote, send_message, ...) exists in this module; that's structural, not
a promise of discipline.

Credentials are venture-specific and never live in DJJTB. This module
reads them from environment variables, loaded via python-dotenv from a
.env file whose path is itself configurable (DJJTB_REDDIT_ENV_PATH),
defaulting to swdjj's secrets file since it's the only current
consumer. A future venture points this at its own .env instead of
DJJTB duplicating credentials per-venture.

Required in that .env:
    REDDIT_CLIENT_ID
    REDDIT_CLIENT_SECRET
    REDDIT_USER_AGENT

This module is imported by server.py as MCP tools. It's also runnable
standalone for quick testing without the server:
    python3 -m djjtb.mcp_server.tools.reddit_research get_subreddit_info <name>
"""

import json
import os
import sys
from pathlib import Path

import praw
from dotenv import load_dotenv

DEFAULT_ENV_PATH = Path("/Users/home/Documents/Scripts/Projects/stories-with-DJJ/secrets/.env")
ENV_PATH = Path(os.environ.get("DJJTB_REDDIT_ENV_PATH", DEFAULT_ENV_PATH))

_reddit = None


def _client() -> praw.Reddit:
    """Lazily build and cache a read-only PRAW client.

    Read-only because only client_id/client_secret are passed -- no
    username/password. PRAW drops into read-only mode automatically in
    that case, so this is structural, not a setting someone could flip.
    """
    global _reddit
    if _reddit is not None:
        return _reddit

    load_dotenv(ENV_PATH)
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT")
    if not all([client_id, client_secret, user_agent]):
        raise RuntimeError(
            f"Missing REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET/REDDIT_USER_AGENT in "
            f"{ENV_PATH}. If this is expected -- Reddit API access currently requires manual "
            f"approval via a support ticket, which can take weeks -- this just means that "
            f"hasn't landed yet. See REDDIT_MCP_SPEC.md for the registration process."
        )

    _reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
    return _reddit


def _clean_subreddit_name(name: str) -> str:
    """Strip an optional leading 'r/' or '/r/' -- PRAW wants the bare name."""
    name = name.strip().strip("/")
    if name.lower().startswith("r/"):
        name = name[2:]
    return name


def _post_summary(post) -> dict:
    return {
        "id": post.id,
        "title": post.title,
        "author": str(post.author) if post.author else "[deleted]",
        "score": post.score,
        "num_comments": post.num_comments,
        "created_utc": post.created_utc,
        "url": post.url,
        "permalink": f"https://reddit.com{post.permalink}",
    }


def get_subreddit_info(name: str) -> dict:
    """Subscriber count, active users, description, age, and NSFW flag for a subreddit.

    Phase 0: is it real, and is it big enough to matter.

    Args:
        name: Subreddit name, with or without a leading "r/".

    Returns:
        Dict with name, title, subscribers, active_user_count,
        created_utc, over18, public_description, description, url.
    """
    sub = _client().subreddit(_clean_subreddit_name(name))
    return {
        "name": sub.display_name,
        "title": sub.title,
        "subscribers": sub.subscribers,
        "active_user_count": sub.active_user_count,
        "created_utc": sub.created_utc,
        "over18": sub.over18,
        "public_description": sub.public_description,
        "description": sub.description,
        "url": f"https://reddit.com{sub.url}",
    }


def search_subreddits(query: str, limit: int = 10) -> list[dict]:
    """Discover candidate subreddits by keyword.

    Phase 0: finding options beyond guessing names.

    Args:
        query: Search text.
        limit: Max number of results.

    Returns:
        List of dicts with name, title, subscribers, over18, public_description.
    """
    results = []
    for sub in _client().subreddits.search(query, limit=limit):
        results.append({
            "name": sub.display_name,
            "title": sub.title,
            "subscribers": sub.subscribers,
            "over18": sub.over18,
            "public_description": sub.public_description,
        })
    return results


def get_subreddit_rules(name: str) -> list[dict]:
    """Pull the actual posted rules text for a subreddit.

    Phase 0: self-promo rule check.

    Args:
        name: Subreddit name, with or without a leading "r/".

    Returns:
        List of dicts with short_name, description, violation_reason.
    """
    sub = _client().subreddit(_clean_subreddit_name(name))
    return [
        {
            "short_name": rule.short_name,
            "description": rule.description,
            "violation_reason": rule.violation_reason,
        }
        for rule in sub.rules
    ]


def get_recent_posts(name: str, limit: int = 10, time_filter: str = "week") -> list[dict]:
    """Recent post volume/dates -- actually active vs. a stale listing.

    Phase 0: is this subreddit genuinely active. Uses top-of-period
    rather than /new so limit reflects real volume within the window,
    not just however many posts happened to land most recently.

    Args:
        name: Subreddit name, with or without a leading "r/".
        limit: Max number of posts.
        time_filter: One of "hour", "day", "week", "month", "year", "all".

    Returns:
        List of dicts with id, title, author, score, num_comments,
        created_utc, url, permalink.
    """
    sub = _client().subreddit(_clean_subreddit_name(name))
    return [_post_summary(p) for p in sub.top(time_filter=time_filter, limit=limit)]


def search_posts_in_subreddit(name: str, query: str, limit: int = 10) -> list[dict]:
    """Find existing discussion of a topic within a subreddit.

    Phase 1: judging real fit before ever commenting.

    Args:
        name: Subreddit name, with or without a leading "r/".
        query: Search text.
        limit: Max number of results.

    Returns:
        List of dicts with id, title, author, score, num_comments,
        created_utc, url, permalink.
    """
    sub = _client().subreddit(_clean_subreddit_name(name))
    return [_post_summary(p) for p in sub.search(query, limit=limit)]


def get_post_comments(post_id: str, limit: int = 50) -> list[dict]:
    """Read a full comment thread for real context before a (manual) reply.

    Phase 1: real context before a (manual) reply.

    Args:
        post_id: Reddit submission's base36 id (not the full URL).
        limit: Max number of flattened comments to return.

    Returns:
        List of dicts with id, author, body, score, created_utc, depth.
    """
    submission = _client().submission(id=post_id)
    submission.comments.replace_more(limit=0)
    out = []
    for c in submission.comments.list()[:limit]:
        out.append({
            "id": c.id,
            "author": str(c.author) if c.author else "[deleted]",
            "body": c.body,
            "score": c.score,
            "created_utc": c.created_utc,
            "depth": c.depth,
        })
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m djjtb.mcp_server.tools.reddit_research <tool_name> [args...]")
        sys.exit(1)

    fn_name, *args = sys.argv[1:]
    fn = globals().get(fn_name)
    if fn is None or fn_name.startswith("_") or not callable(fn):
        print(f"Unknown tool: {fn_name}")
        sys.exit(1)
    print(json.dumps(fn(*args), indent=2, default=str))
