# Reddit Research MCP — Build Spec (for Claude Code)

## Context — what this is and why it lives here

This tool supports Phase 0 of the swdjj growth plan (`GROWTH_PLAN.md`, swdjj repo) — vetting real
communities (subscriber counts, activity, self-promo rules) before any human engagement starts.
It's read-only by design: no post/comment/vote/DM tools exist in this server at all, structurally,
not by discipline. Posting stays manual — a person's own aged account, a person's own words.

**Why this lives in DJJTB, not the swdjj repo.** This tool has zero swdjj-specific logic —
`get_subreddit_info`, `search_subreddits`, etc. would run unchanged for any future venture (the
portrait service, or whatever comes after). DJJTB already has real MCP server infrastructure for
exactly this kind of reusable, cross-venture tool. This gets added to that existing framework, not
built as a new standalone server. The rule going forward: project-specific logic → the venture's
own repo; reusable infrastructure → DJJTB.

**DJJTB and swdjj, and how they relate here.** DJJTB is the owner's general-purpose tooling
project — cross-venture infrastructure, not tied to any one content brand. Stories with DJJ is one
venture that consumes DJJTB's tooling where relevant (this Reddit tool being the first case of
that for growth work) while keeping its own venture-specific pipeline, brand assets, and secrets
in its own repo. Neither repo needs deep knowledge of the other's internals — DJJTB doesn't need
the growth-strategy reasoning behind this tool, only that it's a live tool currently used by swdjj
(and available to whatever needs the same kind of read-only community research next). swdjj's own
growth plan references this tool by name and points back here rather than duplicating the spec.

## Before writing any code

Inspect the existing structure first — follow the pattern that's actually there, don't assume one:

- `djjtb/mcp_server/server.py` — how are existing tools registered?
- `djjtb/mcp_server/tools/` — what's the existing file/module convention, one tool vs. another?
- `djjtb/mcp_server/mcpo_config.json` — does a new tool need an entry here too?
- `djjtb/mcp_server/server_jsons/` — check whether a matching manifest is expected here.
- `djjtb/mcp_server/openwebui_filers/` — only touch this if the Reddit tool should also be exposed
  through Open WebUI; not assumed necessary, confirm with the owner if unclear.

Use the existing `mcpvenv` — don't create a new isolated venv for this. The mcp_server already has
one; this tool belongs inside that same server as another tool module, not as a separate process.

## Credentials — live in swdjj, not DJJTB

The tool's *code* is reusable infrastructure and belongs in DJJTB. The Reddit account's
*credentials* are swdjj-specific and belong in swdjj's own secrets:

`/Users/home/Documents/Scripts/Projects/stories-with-DJJ/secrets/.env`
```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=storieswithdjj-research-tool by /u/<account-username> v1.0
```

The DJJTB tool should read these via environment variables at runtime rather than hardcoding or
duplicating them into DJJTB. That keeps the tool itself venture-agnostic — a future venture points
it at a different `.env` — and keeps venture secrets scoped to the venture's own repo, consistent
with how the portrait service and swdjj already keep separate accounts and branding.

## Reddit API app registration — now a manual approval request, not instant self-serve

**Update (2026-08-16, confirmed from the swdjj side while preparing credentials):** the flow
described in earlier versions of this doc no longer exists. Reddit's "Responsible Builder Policy"
killed self-serve OAuth app creation — `reddit.com/prefs/apps` → "create app" now silently fails
or redirects to a policy page, confirmed across multiple independent developer reports, not
specific to this account.

**What actually works now:**

1. Log into reddit.com with the storieswithDJJ@gmail.com account.
2. Submit a request via Reddit's support ticket form:
   `support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164`
3. Category: **developer**. Include a detailed use-case description, a link to this tool's source
   (this spec / the `reddit_research.py` module), and the target subreddits this will read.
4. No dashboard, no instant approval. Reports describe a multi-week wait, and sometimes a vague
   rejection even for legitimate read-only use — there's no guaranteed outcome.
5. Once (if) approved, save the `client_id` and `client_secret` as before — nothing else in this
   spec changes.

**This is not a blocking dependency for building the tool itself.** The PRAW
read-only client-credentials pattern (`client_id` + `client_secret`, no username/password) is
unaffected — the code can be built and reviewed now; only live testing waits on approval.

**Two dead ends, in case either looks like a shortcut — neither is:**

- `developers.reddit.com` (Devvit) does not bypass this. Devvit is Reddit's in-platform app
  framework (apps installed inside one subreddit's own context) — architecturally different from
  external read-only cross-subreddit access, and doesn't provide `search_subreddits`/
  `get_subreddit_info`-style general access at all.
- The old unauthenticated `.json` endpoint fallback (`reddit.com/r/<subreddit>/about.json` with no
  auth) was shut off by Reddit on 2026-05-30 — returns 403 now. No quiet workaround exists.

Registering under the storieswithDJJ account is still fine once/if a ticket is approved — it's not
community-facing activity, so the account's fresh-registration status doesn't matter here.

## No account password needed

Reddit's API supports pure application-only (read-only) access via just `client_id` +
`client_secret`. PRAW drops into read-only mode automatically when no username/password is passed
— don't store the account's actual Reddit password anywhere for this tool; it isn't needed.

## Stack

- **Python**, matching the existing `mcpvenv`.
- **PRAW** for the Reddit client — handles OAuth/rate-limiting/pagination correctly instead of
  hand-rolling raw HTTP against Reddit's API.
- Whatever MCP framework `server.py` already uses — match it, don't introduce a second pattern.

## Tools to implement — deliberately read-only, nothing else

| Tool | Purpose | Maps to |
|---|---|---|
| `get_subreddit_info(name)` | Subscriber count, active users, description, age, over18 flag | Phase 0: size + is it real |
| `search_subreddits(query)` | Discover candidates by keyword | Phase 0: finding options beyond guessing names |
| `get_subreddit_rules(name)` | Pull the actual posted rules text | Phase 0: self-promo rule check |
| `get_recent_posts(name, limit, time_filter)` | Recent post volume/dates | Phase 0: actually active vs. a stale listing |
| `search_posts_in_subreddit(name, query)` | Find existing discussion on a topic | Phase 1: judging real fit before ever commenting |
| `get_post_comments(post_id)` | Read a full thread | Phase 1: real context before a (manual) reply |

**Do not implement**: `submit_post`, `submit_comment`, `vote`, `send_message`, or anything else
that writes. Build the server so those actions are structurally absent, not just unused — that's
the actual safeguard, not a promise not to call them.

## Next step

Once it's connected, bring it back to the swdjj strategy chat — vetting the Phase 0 communities is
exactly what it's for.
