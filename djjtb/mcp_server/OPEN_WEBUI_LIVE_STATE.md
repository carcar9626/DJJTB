# Open WebUI — Live State Audit

A snapshot of what's actually configured inside the running Open WebUI
instance (`http://localhost:3000`), captured 2026-08-01 by driving the
admin UI directly (not inferred from files on disk). The doc files
elsewhere in this repo (`multi_category_pipeline.md`, `HERMES_SETUP.md`)
describe the *design*; this one is the *verified current reality*,
including a couple of things that had drifted from the design and weren't
written down anywhere. Re-verify against the live UI before trusting this
for anything beyond orientation — it's a point-in-time snapshot, not a
synced view.

## Connections (Admin Settings → Connections)

| Type | URL | What it actually is |
|---|---|---|
| OpenAI API | `https://api.openai.com/v1` | Real OpenAI API |
| OpenAI API | `http://host.docker.internal:8643/v1` | **Hermes Agent's gateway** — matches the port in `HERMES_SETUP.md` exactly |
| OpenAI API | `https://integrate.api.nvidia.com/v1` | NVIDIA's hosted inference API — backs the now-inactive `DJJTB-MiniMax-M3_nvidia` model (see below), not documented anywhere before this audit |
| Ollama API | `http://host.docker.internal:11434` | Matches `ai_stack_port_registry.md` |

All API keys are configured but masked in the UI — not recorded here, and
shouldn't be pasted into any doc.

## Integrations → External Tool Servers

**Removed 2026-08-01.** A vestigial `djjtb_mcp` → `http://host.docker.internal:8000`
connection (leftover from before Open WebUI's per-model Tool Server
scoping limitation forced the switch to five separate Workspace Tools —
see `multi_category_pipeline.md`) used to sit here. Deleted via the admin
UI at the user's request, as part of establishing a clean baseline before
adding new mcpo integrations/pipes. Verified afterward that POSE-GEMMA's
actual tool (the "DJJTB Pose Filer" Workspace Tool) and its "POSES"
Knowledge collection were both untouched — this connection was never
wired to anything real. No Open Terminal connections, no External
Knowledge Sources configured either.

## Workspace → Models (7 total)

**The five NBP category models** — POSE-GEMMA, SCENE-GEMMA,
LIGHTING-GEMMA, OUTFIT-GEMMA, COMPOSITION-GEMMA. All on base `gemma4:26b`.
Each has exactly one Workspace Tool attached (its own filer, matching
`multi_category_pipeline.md`'s design). All five have **every capability
toggle enabled** (Vision, File Upload, File Context, Web Search, Image
Generation, Code Interpreter, Terminal, Citations, Status Updates, Builtin
Tools — only "Usage" is off) and every Builtin Tool sub-toggle on. That's
broader than what any of these models actually need (a pure vision-to-text
extractor doesn't need Terminal or Code Interpreter access) — not
necessarily a problem, but worth knowing it's default-everything-on rather
than deliberately scoped.

**POSE-GEMMA specifically** also has a Knowledge collection attached:
**"POSES"** (description "PROMPT POSES AND REFERENCE"), containing one
file — `NBP_POSE_PROMPTS-20260707.pdf` (32.7 MB). This is the exact
knowledge base POSE-GEMMA's own system prompt refers to ("adopt the dense,
mechanical descriptive style found in the NBP_POSE_PROMPTS knowledge
base") — confirmed live and attached, not just a phrase in the prompt
text. POSE-GEMMA's live system prompt was verified 2026-08-01 to match the
update made this session (single-pose-image workflow language, the
`image_filename` passthrough instruction) — see `multi_category_pipeline.md`'s
"Update 2026-08-01" section for what changed and why.

**Two more models — inactive/legacy, kept intentionally:**
- `DJJTB-MiniMax-M3_nvidia` — base `minimaxai/minimax-m3` via the NVIDIA
  connection above.
- `DJJTB Refactor Engine` — base `qwen3-coder:30b` via local Ollama.

Both carry the identical system prompt: a "local software refactoring
engine" instructed to output modified Python files in full, never
truncate/placeholder, and explain changes briefly at the end. Same persona
on a cloud backend and a local one. **Built before the user adopted Claude
Code for this kind of work — no longer the primary tool for that job, but
deliberately kept around** as a fallback for quick one-off script edits
when Claude Code isn't available. Don't delete these. The `DJJTB Local
REPO` Knowledge collection that used to back them **was removed
2026-08-01** (stale month-old snapshot, and removing it doesn't affect
whether these two models still work standalone) — see Knowledge section
below.

## Workspace → Tools (8 total)

- **DJJTB Pose Filer, DJJTB Scene Filer, DJJTB Lighting Filer, DJJTB
  Outfit Filer, DJJTB Composition Filer** — the five real per-category
  filers. DJJTB Pose Filer's live code was verified 2026-08-01 to exactly
  match the updated local copy in
  `DJJTB/djjtb/mcp_server/openwebui_filers/djjtb_pose_filer.py`
  (`image_filename` parameter present and wired through).
- **Memory** (v0.0.1), **DuckDuckGo Web Search** (v0.9.5), **Google
  Search Tool** (v1.0.0) — generic/community tools, unrelated to the NBP
  pipeline.

## Admin → Functions (4 total)

- **Z-Image Turbo (ComfyUI)** (type: Pipe) — enabled. Matches
  `open-webui-functions/z_image_turbo_character_pipe.py` exactly
  (description: "generate images with ZIT via Comfyui API").
- **Auto Memory** (type: Filter, v1.1.0-alpha1) — enabled. Automatically
  stores relevant chat info as Memories; pairs with the "Memory" Tool above.
- **Smart Mind Map** (type: Action, v1.0.1) — enabled. Generic community
  function, unrelated to this stack's own pipelines.
- **Generate Image** (type: Action, v0.2.2) — **disabled**.

## Workspace → Knowledge (1 collection)

- **POSES** — see POSE-GEMMA above.
- ~~DJJTB Local REPO~~ — **removed 2026-08-01.** Was a month-old,
  one-time snapshot of parts of the DJJTB repo backing the two inactive
  refactor-engine models above; removed as stale cruft since it wasn't a
  live sync and could only drift further. The two refactor-engine models
  themselves were kept (see above) — this was Knowledge-only cleanup.

## Live end-to-end pipeline test (2026-08-01)

First real, live test of the pose-image-linking feature added earlier
this session — not just unit-tested in isolation. Method: attached a real
single-pose reference photo (`pose_images/p67.jpg`) to POSE-GEMMA in Open
WebUI directly and sent "Prompts please and file to prompt assembler."

**First attempt failed silently on the image field, mechanically correct
otherwise.** A new entry (`P67-...`) was filed with the right
auto-incremented title and a sensible prompt, but `image` came back empty
instead of `pose_images/p67.jpg`. Root cause: **`com.djjtb.mcpserver` (the
LaunchAgent running mcpo) had been running since the day before, so it was
still serving the pre-update `add_pose_prompts.py`** — confirmed via
`launchctl list` (start time predated the code change) and via the live
`/pose/openapi.json` schema (no `image_filename` field). This is the
"mcpo doesn't hot-reload" gotcha already documented in
`multi_category_pipeline.md`, now confirmed as a real live failure mode,
not just a theoretical one.

**Fix:** `launchctl kickstart -k gui/<uid>/com.djjtb.mcpserver`, then
re-verified `image_filename` appeared in the live OpenAPI schema before
retrying. The test pose entry was removed from `prompt_assembler.json`
first (to avoid a confusing duplicate) and the test image file was
restored after being accidentally deleted mid-cleanup — both corrected
before the retest.

**Second attempt, identical prompt, after the mcpo restart: fully
correct.** `P67-ASYMMETRICAL_RECLINE_KNIT` filed with `image:
"pose_images/p67.jpg"` auto-linked, confirmed rendering correctly in
`prompt_assembler.html`'s pose-reference pane.

**Also observed, confirmed pre-existing and not a regression:** on the
first attempt, POSE-GEMMA answered with a long, chatty "Option 1/2/3"
multi-style response instead of the strict `#NAME#`-only format the
"prompts please" override protocol specifies — but still called the
filing tool correctly regardless. The second attempt (identical prompt)
gave a clean one-line confirmation instead. **The user confirmed all five
`*-GEMMA` models do this occasionally** and it's never affected the actual
JSON filing, which is why it had gone unnoticed/uninvestigated before now.
Treat it as a known, harmless quirk in the chat-visible response, not
something to chase — the thing that matters (the tool call and its
arguments) has been reliable across both attempts here.

## Standing gotcha for future audits

Everything in this file was confirmed by actually opening the admin UI —
several real discrepancies from the written design docs turned up this way
(the vestigial `djjtb_mcp` Tool Server chief among them) that no file on
disk would have revealed. When "document the pipeline" comes up again,
prefer re-driving the UI over trusting `multi_category_pipeline.md` or
this file to still be accurate — both describe a point in time, not a live
view.
