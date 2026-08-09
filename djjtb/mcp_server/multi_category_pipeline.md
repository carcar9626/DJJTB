# NBP Multi-Category Prompt Pipeline — Build Log & Reference

Documents the expansion of the NBP prompt-assembler pipeline from pose-only to five
categories (Pose, Scene/Setting, Lighting, Outfit, Composition), built in one session.
Written for handoff to Claude Code, another chat, or future-you re-reading this cold.

## What this pipeline does

Reference images/grids go into a category-specific Gemma4 model in Open WebUI, which
extracts a structured description and can file it directly into
`prompt_assembler.json` — the same tool your original pose workflow already used,
now generalized across five categories instead of one.

## Architecture overview

```
Reference image
      ↓
Open WebUI custom model (one of 5, each = gemma4:26b + a category-specific
system prompt)
      ↓
"prompts please" → strict extraction → model calls its dedicated Workspace Tool
      ↓
Workspace Tool (native Python, runs inside Open WebUI) → HTTP POST →
      ↓
mcpo sub-server for that category (path-isolated, one port, five paths)
      ↓
add_pose_prompts.py (generalized, category-aware) → prompt_assembler.json
```

## The five models (Open WebUI, Workspace → Models)

| Model | Base | System prompt covers |
|---|---|---|
| POSE-GEMMA | gemma4:26b | Body pose/action only |
| SCENE-GEMMA | gemma4:26b | Environment/setting only |
| LIGHTING-GEMMA | gemma4:26b | Lighting only |
| OUTFIT-GEMMA | gemma4:26b | Clothing/wardrobe only |
| COMPOSITION-GEMMA | gemma4:26b | Camera framing/lens only |

Each system prompt follows the same structure as the original pose one (Role &
Context / Core Values / Analysis Protocol), with two trigger phrases:

- **`"prompts please"`** → strict extraction mode. Output is `#NAME#\n<description>`
  blocks, filing-ready. This is the only mode that should ever reach the assembler.
- **`"full prompts"` / `"complete prompts"`** → standalone, generation-ready prose
  mode. Deliberately uses a *different* heading style (`## Name — Complete X
  Prompt`, not the bare `#NAME#` tag) so it can never be mistaken for filing-ready
  output — if accidentally run through the filing script, it fails loudly rather
  than silently polluting an entry.
- If neither phrase is present, the model is instructed to ask which mode is wanted.

**Lead-in phrasing** (added late in the build, subject-anchoring for the generation
stage):
- Outfit: every description starts with `"Subject's wearing a "`
- Scene/Setting: every description starts with `"Subject is in "`
- Composition, Lighting: no forced lead-in — left as-is
- Pose: already subject-anchored from the original template, unchanged

Full system prompt text lives in the earlier artifact from this project:
`nbp_system_prompts_scene_lighting_outfit_composition.md`, plus the original pose
prompt the user supplied directly (not separately filed anywhere yet — worth adding
to project knowledge if it isn't already).

## prompt_assembler.json schema

9 top-level arrays: `subject`, `outfit`, `scene/setting`, `composition`,
`pose/action`, `spacial/add ons`, `lighting`, `aesthetic`, `misc.`, `custom`.

`scene/setting` is new this session — didn't exist in the original schema (built
originally for flow.google/Nano Banana i2i work, where scene wasn't needed). Added
between `outfit` and `composition` in both the JSON and `prompt_assembler.html`,
optional like every other category.

Each filing-eligible category uses a letter-prefixed, auto-incrementing title:
`P<n>-`, `S<n>-`, `L<n>-`, `O<n>-`, `C<n>-`. Pre-existing entries that don't follow
this convention (hand-curated ones, e.g. composition's original camera-angle
presets) are left untouched — numbering just continues past whatever the highest
existing number is.

## Scripts (DJJTB repo)

**`djjtb/file_tools/add_pose_prompts.py`**
Generalized from pose-only to all five categories. `add_pose_prompts(raw_text,
json_path, category=...)` takes any of the five array keys. CLI `main()` now
prompts interactively (`prompt_choice()`, options 1–5, default Pose) instead of
hardcoding pose. `CATEGORY_MENU` and `CATEGORY_PREFIX` dicts are the source of
truth for category → array key → title prefix.

**Pose image linking (added 2026-08-01).** The pose workflow dropped
multi-pose grids in favor of one reference image per pose, uploaded and
saved separately into `prompt_assembler/LOCAL/pose_images/`. `pose/action`
entries only (no other category) now get an `image` field filed
automatically, via a new `resolve_pose_image(number, explicit_filename="")`
function:
- **Default path:** after the new entry's number is assigned,
  `add_pose_prompts()` checks `prompt_assembler/LOCAL/pose_images/` for a
  file already named `p<number>.<ext>` (jpg/jpeg/png/webp). If found,
  it's linked. If not (the reference image hasn't been placed there yet),
  `image` is left as `""` — same as any other unlinked preset; it can be
  linked later through the prompt_assembler app's pose-reference pane (a
  path input right there in the UI) once the file exists.
- **Override path:** `add_pose_prompts()` takes a new optional
  `image_filename` argument, only meaningful when filing exactly one pose
  per call (with more than one, which entry it'd apply to is ambiguous,
  so it's ignored and every entry falls back to the default path
  instead). This flows end to end: POSE-GEMMA's system prompt → the
  model's `file_pose_prompt` tool call → `server.py`'s `file_pose_prompt()`
  → the Open WebUI Workspace Tool (`openwebui_filers/djjtb_pose_filer.py`)
  → `add_pose_prompts()`. The model is instructed to pass this through
  **only** when the user's own message explicitly states a filename —
  never to guess or invent one, and never to use a pose number for it,
  since the model has no way to know what number the pipeline will
  assign before filing happens.
- This only applies to pose/action right now. Scene/lighting/outfit/
  composition entries don't have an `image` concept at all.
- See `prompt_assembler/LOCAL/README.md` § 10 for the naming convention
  (`pose_images/p<number>.<ext>`, lowercase) and for a real example of
  why this needs to stay conservative: a batch of ~72 poses linked
  retroactively by reading numbers off old reference grids turned up a
  handful of numbers (54–58) that were ambiguous/duplicated across
  multiple source files — those were deliberately left unlinked rather
  than guessed. The auto-detect-by-number default here has the same
  failure mode in principle (if two different images both happened to be
  named the same number), so it's worth a periodic sanity check that
  `pose_images/` doesn't accumulate stray duplicate-numbered files.

**`djjtb/mcp_server/server.py`**
Runs with a `--category <name>` argument. Each invocation registers **only** its
one corresponding tool function (`file_pose_prompt`, `file_scene_prompt`, etc.) —
not all five. The FastMCP instance name is also category-derived
(`djjtb_mcp_<category>`), so each sub-server correctly self-reports its own
identity rather than all five showing identically.

## Infra: mcpo, ports, and Open WebUI wiring

**Why one shared tool didn't work:** the original single MCP server exposed all
five filing functions through one Open WebUI connection. Open WebUI can only
enable/disable a whole tool-server connection per model, not individual functions
inside it — so every model had access to every category's filing function
regardless of its system prompt. This caused two real bugs mid-build:
1. **Category leakage** — a single "outfit" test run filed into pose, scene, and
   lighting too, because the shared tool's docstring literally enumerated all five
   categories as valid options.
2. **Triplication** — the same run created 3 near-duplicate entries per category,
   from the model (thinking-enabled) re-calling the tool multiple times per turn
   while refining its own wording.

**The fix — path-isolated sub-servers, one per category, one shared port:**
`mcpo` runs in multi-server config mode (`mcpo --port 8000 --config
mcpo_config.json`), where each named server is mounted at its own sub-path:

```
http://192.168.50.67:8000/pose
http://192.168.50.67:8000/scene
http://192.168.50.67:8000/lighting
http://192.168.50.67:8000/outfit
http://192.168.50.67:8000/composition
```

Each path serves exactly one tool function — genuine isolation, not just a naming
convention. `mcpo` itself runs as a macOS LaunchAgent for persistence across
reboots (launches `python3 -m djjtb.mcp_server.server --category <name>` per entry
in the config).

**Note on the IP:** `host.docker.internal` (the usual Docker→Mac-native-process
pattern, per the port registry's existing rule of thumb) didn't work for this
Open WebUI setup — had to switch the Tool Server URL to the Mac's actual LAN IP
(`192.168.50.67:8000`) instead. Worth a registry update if this pattern recurs
elsewhere in the stack.

**The real per-model isolation mechanism turned out to be different than
expected:** Open WebUI's "Tool Servers" (external OpenAPI/MCP connections, added
under Settings → Integrations → Manage Tool Servers) **never appear in a model's
own Tools checklist** — that section only ever lists native **Workspace → Tools**
(Python code running inside Open WebUI itself). The fix was five thin Workspace
Tools, one per category, each just forwarding an HTTP POST to its own mcpo
sub-path:

```python
class Tools:
    def file_outfit_prompt(self, raw_text: str) -> str:
        """... docstring becomes the function schema the model sees ..."""
        resp = requests.post(
            "http://192.168.50.67:8000/outfit/file_outfit_prompt",
            json={"raw_text": raw_text}, timeout=30,
        )
        resp.raise_for_status()
        return str(resp.json())
```

These five wrappers are pasted directly into Open WebUI's Workspace → Tools editor
(not part of the DJJTB repo) and attached one-per-model via Workspace → Models →
edit → Tools.

## Known gotchas / things to re-check if this breaks again

- **mcpo doesn't hot-reload.** Editing `server.py` requires restarting mcpo itself
  (it launches the MCP server as its own subprocess at startup) — not just saving
  the file. **Confirmed as a real live failure, 2026-08-01, not just a theoretical
  one:** the pose image-linking feature was added, but `com.djjtb.mcpserver`
  (the LaunchAgent running mcpo) had been up since the day before. First live
  test filed the pose correctly but with no `image` field, because mcpo was
  still serving the old code — confirmed via `launchctl list` (stale start
  time) and the live `/pose/openapi.json` schema (missing the new
  `image_filename` field). Fixed with
  `launchctl kickstart -k gui/<uid>/com.djjtb.mcpserver`; identical retry then
  worked correctly. **After any change to `server.py` or
  `add_pose_prompts.py`, restart this LaunchAgent before testing** — don't
  assume a fresh test reflects fresh code.
- **All five `*-GEMMA` models occasionally answer in a chatty, non-strict
  format** (e.g. a multi-option "Option 1/2/3" style response) instead of
  the `#NAME#`-only format the "prompts please" override protocol
  specifies, even when the tool call itself is still correct. Confirmed by
  the user as a longstanding, harmless quirk that's never affected actual
  filing — it changes what's shown in chat, not what gets written to
  `prompt_assembler.json`. Not investigated further since it's never
  broken anything; worth knowing so it isn't mistaken for a new bug.
- **Tool Servers vs. Workspace Tools are genuinely separate systems** in Open
  WebUI. Only the latter attaches per-model. This cost significant debugging time
  before the tooltip ("add them to the Tools workspace first") gave it away.
- **The model-editor "Tools" checkbox may only set a default-on state, not a hard
  restriction**, per Open WebUI's own community discussions on this exact feature.
  Worth a quick spot-check per model/chat rather than trusting it blindly,
  especially after any Open WebUI update.
- **A container restart without a persisted `WEBUI_SECRET_KEY`** can silently
  break decryption of stored tool-server credentials — if a connection
  "disappears" again, check this before assuming the tool server itself is down.
- Model instructions matter here: each system prompt now explicitly says "call
  the filing tool exactly once" and "never touch another category's tool" — both
  added specifically because the model didn't do either by default.
- **The pose image auto-link depends on file-placement timing.** If the
  reference image isn't already sitting in `pose_images/` (named by the
  number that's *about to* be assigned) at the moment `file_pose_prompt`
  runs, the new entry's `image` just comes back blank — not an error,
  and not retried later. Nothing re-scans `pose_images/` after the fact.
  Fine to fix up manually afterward via the prompt_assembler app's pane,
  but worth knowing this isn't a retroactive/watching process.

## Open items / things not done tonight

- **Composition tension, unresolved:** early in this build, the plan was to treat
  image-derived composition output as *candidates* to manually review and fold
  into the existing curated composition list — not auto-file it — since
  composition was originally kept deliberately hand-curated. In practice, the
  final pipeline auto-files composition the same as every other category. Worth
  a deliberate decision either way rather than leaving it as an accidental
  default.
- Entries filed during testing before the lead-in phrasing was added (e.g. the
  early `O01`–`O03` outfit test batch) don't have `"Subject's wearing a"` etc. —
  not retroactively fixed.
- `ai_stack_port_registry.md` hasn't been updated yet with tonight's lessons
  (mcpo multi-server/path-mounting pattern, the Tool Servers vs. Workspace Tools
  distinction, the LAN-IP-over-host.docker.internal requirement). Worth doing
  next time this project's chat is open.
- Alternatives to `gemma4:26b` were researched (`gemma4:31b`, the `-mlx` builds,
  `qwen3-vl:8b`) but not adopted — still running `gemma4:26b` across all five
  models as of tonight.

## Update 2026-08-01: pose image linking + grid-workflow retired

- POSE-GEMMA's system prompt was revised: reference images are now
  expected to be a single pose per image (grids are no longer the normal
  case, though the model still tolerates one if given). Added an
  `image_filename` passthrough instruction — see "Pose image linking"
  under Scripts above. The model-facing behavior otherwise (mandatory
  blocks, `#NAME#` extraction format, "prompts please" trigger, "call the
  filing tool exactly once") is unchanged.
- Code changes: `add_pose_prompts.py` (new `resolve_pose_image()` +
  `image_filename` param), `server.py`'s `file_pose_prompt()` (new
  `image_filename` param, passthrough only), `openwebui_filers/djjtb_pose_filer.py`
  (same param, still needs to be manually copied into Open WebUI's
  Workspace → Tools editor to take effect there — editing the local copy
  in this repo doesn't update Open WebUI by itself).
- Scene/lighting/outfit/composition are untouched by this update — still
  no `image` concept for those categories.
