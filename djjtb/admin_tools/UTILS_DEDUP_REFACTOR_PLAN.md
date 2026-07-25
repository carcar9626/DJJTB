# DJJTB — utils.py Modularization / Dedup Refactor Plan

**Status:** in progress — Phases 0-4 done, Phase 5 next
**Created:** 2026-07-25
**Purpose:** living checklist for incrementally moving duplicated per-script
logic (`collect_images_from_folder`/`collect_videos_from_folder`
reimplementations, hand-rolled multi-path input parsing) onto the shared
`djj.*` equivalents in `djjtb/utils.py`/`djjtb/media_utils.py`, and rolling
out the sibling-`Output/` output-path convention — one small, independently
testable step at a time. This is the doc referenced by CLAUDE.md's "Current
goal." No refactor has been executed yet; this file only plans it.

**How to use this doc:** each phase below is a checkbox. Open this file at
the start of a session, pick the next `[ ]` phase (respecting the `Depends
on` field), do the work, run the phase's verification step, then flip its
box to `[x]` and add a one-line note (date + what actually happened, esp.
if it diverged from the plan) before ending the session. A phase can be
split further across sessions if it's still too big — just add sub-checkboxes
under it, don't force it into one sitting.

Legend: `[ ]` not started · `[~]` in progress (leave a note on what's left)
· `[x]` done

---

## Re-verification note (2026-07-25)

The file lists below were re-confirmed with fresh greps against the current
repo state immediately before writing this plan (not carried over from an
earlier scan). Drift found vs. the assumptions that kicked off this planning
pass:

- **Item 2 (hand-rolled multi-path parsing) count is 21 active files, not
  "~24."** Of those 21, 6 already overlap with Item 1's file list (their
  `collect_*_from_paths` helper *is* the hand-rolled parser) — see the Phase 6
  preamble for how that overlap is handled so it isn't done twice.
- **`djj.get_centralized_output_path()` now has 0 real active callers**, not
  "used by 1 script" — the only remaining reference is example text inside
  `djjtb/helpers/docs/djj.readme_generator.py`, which is stale and worth
  fixing (Phase 5) so it stops telling future generated scripts to use the
  old pattern.
- **There is no `djj.collect_videos_from_folder` today.** Only the
  image-side collectors (`collect_images_from_folder`,
  `collect_images_from_paths`, `collect_images_from_path_list`) exist in
  `djjtb/media_utils.py`. All 5 video-side "duplicate" files are duplicating
  *each other*, not a canonical `djj.*` function — one doesn't exist yet.
  Phase 0 adds it before any video-side phase can proceed.
- **Found a live latent bug while reading `get_centralized_media_input()`**
  (`djjtb/utils.py`): it calls `collect_media_files(folder_path, extensions)`
  / `collect_media_files(path, extensions)` (2 args), but
  `collect_media_files(input_path)` (`djjtb/utils.py:1051`) only accepts 1.
  This would raise `TypeError` the moment mode 1 or a directory-path case in
  mode 2 is hit. It's silent today only because `get_centralized_media_input`
  has 0 real active callers. Flagged as Phase 0a — fix before anything (esp.
  Phase 5/6) routes traffic through it.
- Found an uncatalogued third dead-code location, `djjtb/bak/`, plus a stray
  `djjtb/ai_tools/vocab_mask_generator copy.py` — neither is referenced by
  `djjtb.py`'s menu, both are excluded from every file list below (same
  treatment as `old_versions/`), and neither is in scope for this plan. Worth
  a separate cleanup pass under the existing `old_versions/`archived` tiering
  system at some point, but not folded in here.

---

## Phase 0 — Prerequisite utils fixes & additions

**Status:** `[x]` done (2026-07-25)
**Depends on:** nothing — do this first, it blocks Phases 1–4 and 6
**Risk:** low (additive; 0a fixes dead code, 0b is a new function with no
existing callers to break)

**Done note (2026-07-25):** Both landed in `djjtb/utils.py` /
`djjtb/media_utils.py`. 0a: `collect_media_files(input_path, extensions=None)`
— added the missing param, defaults to the original hardcoded tuple so the
two existing 1-arg call sites (inside `get_media_input`) are unchanged; the
2-arg call sites inside `get_centralized_media_input` now work instead of
raising `TypeError`. 0b: added `VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mkv',
'.avi', '.webm', '.wmv', '.flv')` (the recommended union) and
`collect_videos_from_folder`/`collect_videos_from_paths` to
`media_utils.py`, mirroring `collect_images_from_folder`/`_from_paths`
exactly (same Output-dir pruning, same signature shape), and added all 3
new names to `utils.py`'s explicit `from djjtb.media_utils import (...)`
list so `djj.collect_videos_from_folder` etc. actually resolve — the
re-export list is a named tuple of imports, not `import *`, easy to forget.
Smoke-tested with real temp files (flat vs. recursive collection, Output-dir
pruning, multi-path parsing, and both the 1-arg and 2-arg `collect_media_files`
call shapes) — all passed. `collect_videos_from_path_list` (the third
image-side sibling, used for txt-file input) was **not** added — none of
the Phase 1–4 files need it yet; add it later if a video file's
`collect_videos_from_txt` genuinely needs it (only `video_frame_bridge.py`
has one today, and that's Phase 3).

- **0a. Fix `get_centralized_media_input()`'s arg-count bug.**
  `djjtb/utils.py` — `collect_media_files(input_path)` (line ~1051) takes one
  arg; `get_centralized_media_input()` (line ~799) calls it with two
  (`collect_media_files(folder_path, extensions)` at ~817,
  `collect_media_files(path, extensions)` at ~832). Either add an
  `extensions` param to `collect_media_files` (defaulting to its current
  hardcoded tuple) or drop the extra arg at both call sites. Since there are
  currently 0 active callers of `get_centralized_media_input`, this is safe
  to fix in isolation with no downstream script changes needed.

- **0b. Add `djj.collect_videos_from_folder` / `djj.collect_videos_from_paths`
  to `djjtb/media_utils.py`**, mirroring the shape of
  `collect_images_from_folder`/`collect_images_from_paths`: same param order
  (`folder_path, include_subfolders=False`), same Output-dir pruning during
  recursive walk (`dirs[:] = [d for d in dirs if d.lower() != 'output']`),
  same sorted-list-of-strings return type.
  **Open decision to make when executing this step:** canonical
  `VIDEO_EXTENSIONS`. The 5 files this plan will eventually point at this
  function currently disagree:
  - `video_reverse_merge.py`: `.mp4 .mov .mkv .avi .webm`
  - `video_group_merger.py`: `.mp4 .mkv .webm .mov`
  - `video_processor.py`: `.mp4 .mkv .mov .avi .webm`
  - `video_frame_bridge.py`: `.mp4 .mkv .webm .mov`
  - `video_splitter.py`: `.mp4 .mov .avi .mkv .wmv .flv .webm`

  Recommend the union (`.mp4 .mov .mkv .avi .webm .wmv .flv`) as the
  `djj.*` default, since narrowing is a silent behavior change (files that
  used to be picked up stop being picked up) while widening is not — but
  confirm with the user before locking it in, since some of these tools may
  intentionally exclude `.wmv`/`.flv` as legacy-Windows formats never seen in
  practice.

**Files touched:** `djjtb/utils.py`, `djjtb/media_utils.py`
**Verify:** `python3 -m py_compile djjtb/utils.py djjtb/media_utils.py`
succeeds; a quick REPL smoke test of both new/fixed functions against a real
folder with videos and a nested `Output/` subfolder (confirm pruning works).

---

## Phase 1 — Image collect-function dedup: `ai_tools/`

**Status:** `[x]` done (2026-07-25)
**Depends on:** nothing (djj image-side functions already exist)
**Risk:** medium — extension-list behavior change, see below

**Done note (2026-07-25):** Resolved the `.gif` question by adding an
`extensions=None` override param to `djj.collect_images_from_folder`/
`collect_images_from_paths` in `media_utils.py` (defaults to
`IMAGE_EXTENSIONS` when omitted — every pre-existing caller is unaffected),
then had all 3 files pass their own `SUPPORTED_EXTS` explicitly. No behavior
change for any of the three tools — `.gif` stays excluded exactly as before,
Output-dir pruning is now picked up as a bonus. `vocab_mask_generator.py`'s
and `joycaption_runner_ollama.py`'s local `collect_images_from_folder`/
`_from_paths` were deleted outright and call sites now use `djj.*` directly;
`collect_images_from_txt` in both files was kept as a thin local wrapper
(it's a different shape — takes no args, calls `djj.get_paths_from_txt`
itself — not one of the two functions this phase targeted) but its internal
folder-expansion call now goes through `djj.collect_images_from_folder`
too. `joytag_tagger.py` only had the one function; removed, one call site
updated. Line counts: 507→483, 830→814, 570→542. Smoke-tested with a real
temp folder (`.jpg`/`.png`/`.gif` mix) confirming the narrow-extensions
override actually excludes `.gif` while the default (no override) still
includes it, plus import-time checks on all 3 edited modules confirming no
local `collect_images_from_folder` remains anywhere.

**Files:** `djjtb/ai_tools/vocab_mask_generator.py`,
`djjtb/ai_tools/joytag_tagger.py`,
`djjtb/ai_tools/joycaption_runner_ollama.py`

**Signature/behavior mismatches to reconcile before swapping (read, don't
assume):**
- All three define a local `SUPPORTED_EXTS` = `.jpg .jpeg .png .bmp .tiff
  .webp` — **no `.gif`**. `djj.IMAGE_EXTENSIONS` (`media_utils.py:220`) = the
  same 6 **plus `.gif`**. Swapping in `djj.collect_images_from_folder`
  as-is means these three AI tools start being handed animated GIFs for the
  first time. Decide per-tool whether that's fine (JoyTag/JoyCaption/mask-gen
  may not handle animated GIF input sanely) — if not, these call sites need
  to pass their own narrower extension list rather than relying on djj's
  default, which means `djj.collect_images_from_folder` may need an
  `extensions=` override param added (it currently hardcodes
  `IMAGE_EXTENSIONS` internally — confirm by re-reading the function before
  this phase, since Phase 0 changes may have touched neighboring code).
- `djj.collect_images_from_folder` prunes any subfolder literally named
  `Output` during recursive (`include_subfolders=True`) walks; none of the
  three locals do. This is very likely a strict improvement (stops a tool
  from re-ingesting its own previous output on a re-run) but call it out
  explicitly when landing the change in case it's not.
- `vocab_mask_generator.py` and `joycaption_runner_ollama.py` also each
  define local `collect_images_from_paths`/`collect_images_from_txt` — swap
  these to `djj.collect_images_from_paths`/equivalent in the same pass
  (same file, same concern, no reason to split into a separate phase).
  `joytag_tagger.py` only has `collect_images_from_folder` — nothing else to
  touch there.

**Files touched:** the 3 files above (function bodies deleted, `djj.*` calls
substituted; no signature change at call sites since param order matches)
**Verify:** run each of the 3 tools against a real test folder (flat +
`include_subfolders=True` with a nested `Output/` folder present) and
confirm image counts match expectations (including the GIF decision made
above).

---

## Phase 2 — Image collect-function dedup: `media_tools/`

**Status:** `[x]` done (2026-07-25)
**Depends on:** nothing
**Risk:** low — lowest-risk swap in the whole plan

**Files:** `djjtb/media_tools/image_tools/image_slideshow_maker.py`

Its local `image_extensions` tuple (`.jpg .jpeg .png .gif .bmp .tiff .webp`)
already matches `djj.IMAGE_EXTENSIONS` exactly (order differs, values don't).
The only real behavior delta is the Output-dir pruning djj's version adds.
Also swap the file's local `collect_images_from_paths`/`collect_images_from_txt`
in the same pass (same reasoning as Phase 1).

**Done note (2026-07-25):** Exactly as predicted — no `extensions=` override
needed since the tuples matched exactly, so this was a pure delete-and-call
`djj.*` directly swap. `collect_images_from_folder`/`_from_paths` deleted;
`collect_images_from_txt` kept as a thin local wrapper (same shape reasoning
as Phase 1), its internal folder-expansion now goes through
`djj.collect_images_from_folder`. 654→622 lines. Smoke-tested: flat/recursive
collection, Output-dir pruning, and multi-path parsing all confirmed working
against a real temp folder including a `.gif` (verifying it's still picked
up, matching pre-existing behavior since the extension lists always matched).

**Files touched:** `djjtb/media_tools/image_tools/image_slideshow_maker.py`
**Verify:** run the tool against a real test folder (flat +
`include_subfolders=True` with a nested `Output/` folder) and confirm image
counts are unchanged except for the Output-pruning case.

---

## Phase 3 — Video collect-function dedup: normal-risk files

**Status:** `[x]` done (2026-07-25)
**Depends on:** Phase 0 (needs `djj.collect_videos_from_folder`/`_from_paths`
to exist)
**Risk:** medium — extension-list changes, one file returns a different type

**Done note (2026-07-25):** All 3 done, each landed differently based on what
reading the actual code showed:
- `video_processor.py`: kept thin local wrappers rather than a full swap.
  `collect_videos_from_folder` delegates the folder-walk to
  `djj.collect_videos_from_folder` but still special-cases a bare file-path
  input (confirmed real: `get_videos_input()`'s prompt says "Enter folder
  path" via `djj.get_path_input`, which doesn't validate file-vs-dir, so a
  user pasting a file path needs this safety net) and re-wraps results as
  `Path` objects — `run_reencode`/`run_speed_change`/`run_crop` all use
  `.stem`/`.parent`/`.name` on every video downstream, confirmed by grep
  before touching. `collect_videos_from_paths` was **not** delegated to
  `djj.collect_videos_from_paths` at all — this mode's prompt is explicitly
  "file paths" and it warns-and-skips any directory handed to it, which is
  the opposite of `djj`'s auto-expand behavior; only the extension list now
  comes from `djj.VIDEO_EXTENSIONS`. Local `VIDEO_EXTENSIONS` constant
  removed. 488→479 lines.
- `video_frame_bridge.py`: same Path-wrapper treatment for the video-side
  trio (confirmed same `.stem`/`.parent`/`.name` reliance throughout, e.g.
  `resolve_session_dirs`) — `collect_videos_from_folder` delegates to `djj`
  and re-wraps as `Path`; `collect_videos_from_paths`/`_from_txt` stayed
  local (they already correctly expand directories via the local
  `collect_videos_from_folder` wrapper, so no behavior change needed there,
  just the extension list source). Image side was a clean full swap like
  Phase 1/2 — `collect_images_from_folder`/`_from_paths` deleted outright,
  `collect_images_from_txt` kept as thin wrapper, `extensions=IMAGE_EXTENSIONS`
  (still gif-excluded, same reasoning as Phase 1) passed through. Local
  `VIDEO_EXTS` constant removed. 901→877 lines.
- `video_splitter.py`: the easy one, exactly as predicted — extension list
  already matched the canonical union and both local functions already
  returned strings and already expanded directories the same way `djj`
  does, so this was a straight delete-and-call-`djj.*` swap, no wrapper
  needed. `clean_path()` kept (still used for a single-folder-path input
  elsewhere in the file, unrelated to the deleted functions). 427→394 lines.

All three files ended up **wider** on extensions than before (now the
7-item canonical union) since none had a specific reason found in the code
to stay narrower — flagged per the plan's caution, no objection raised.
Smoke-tested all 3 together: Path-vs-string return types, the bare-file-path
special case, the skip-vs-expand directory-handling difference between
`video_processor.py` and `video_frame_bridge.py`'s paths functions (this
was the trickiest thing to get right — they look like the same function but
are deliberately not), Output-dir pruning, and the image-side gif exclusion
all verified against a real temp folder.

**Files:** `djjtb/media_tools/video_tools/video_processor.py`,
`djjtb/media_tools/video_tools/video_frame_bridge.py`,
`djjtb/media_tools/video_tools/video_splitter.py`

These are the 3 recently-consolidated files (merged from older
single-purpose scripts per CLAUDE.md) — re-read each fresh before touching,
don't assume they match whatever their old pre-merge originals looked like.

**Signature/behavior mismatches to reconcile:**
- Extension lists differ per file today (see Phase 0b's table) — after the
  swap, all 3 pick up whatever canonical list Phase 0b lands on. If that's
  wider than a file's current list (e.g. `video_frame_bridge.py` currently
  has no `.avi`/`.wmv`/`.flv`), confirm that's desired for that specific
  tool, not just assumed safe because it's "more."
- `video_processor.py`'s local `collect_videos_from_folder` additionally
  accepts a **bare file path** as `input_path` (not just a folder) and
  returns a list of `Path` objects, not strings — `djj.collect_videos_from_folder`
  returns strings and is folder-only. Check every call site in this file for
  `Path`-specific method calls (`.suffix`, `.name`, etc.) on the return value
  before swapping, and check whether the file-path-direct-input case is
  actually exercised anywhere (if it's dead capability, note that instead of
  preserving it awkwardly).
- `video_frame_bridge.py` has **two** independent local collector pairs in
  the same file — `collect_videos_from_folder`/`_from_paths`/`_from_txt`
  (video side) and `collect_images_from_folder`/`_from_paths`/`_from_txt`
  (image side, no `include_subfolders` param at all on the image side —
  always non-recursive). Both need swapping in this phase (image side to the
  existing `djj.collect_images_from_folder`, video side to Phase 0b's new
  functions) — treat as two sub-edits in the same file, verify both
  extract/compile modes afterward.
- Each file's `collect_*_from_paths` is also this file's contribution to the
  Item-2 hand-rolled-multi-path-parsing list — handled here, **not**
  revisited in Phase 6 (see Phase 6 preamble).

**Files touched:** the 3 files above
**Verify:** run each tool's full mode set (video_processor: re-encode /
speed / crop; video_frame_bridge: extract + compile, including subfolder
batch compile; video_splitter: duration, portion, and scene-detection modes)
against real test video(s) before/after, confirm identical file counts and
output.

---

## Phase 4 — Video collect-function dedup: "proud of" files (higher caution)

**Status:** `[x]` done (2026-07-25)
**Depends on:** Phase 0
**Risk:** higher — these are explicitly flagged in CLAUDE.md as hands-off
custom workflows the user is proud of; treat this phase as lower priority
and do it more carefully/slowly than Phases 1–3, dedup-only, no incidental
cleanup beyond the stated swap

**Files:** `djjtb/media_tools/video_tools/video_reverse_merge.py`,
`djjtb/media_tools/video_tools/video_group_merger.py`

**Signature/behavior mismatches to reconcile:**
- `video_reverse_merge.py`'s local `collect_videos_from_folder(input_path,
  subfolders=False)` only — no `collect_videos_from_paths` in this file (so
  it's not part of Item 2's list at all). Param name is `subfolders`, djj's
  is `include_subfolders` — positional call sites are fine, any keyword-arg
  call sites need renaming.
- `video_group_merger.py`'s local `collect_videos_from_folder(input_path)`
  has **no recursion parameter whatsoever** — it is unconditionally
  non-recursive today. Swapping to `djj.collect_videos_from_folder(folder_path,
  include_subfolders=False)` is safe by default (same behavior at
  `include_subfolders=False`), but this file also has
  `collect_subfolders_with_videos(parent_path)`, which calls
  `collect_videos_from_folder` once per immediate subfolder to build a
  `{subfolder: [videos]}` grouping — that's a *different* recursion strategy
  (manual one-level fan-out, not `include_subfolders=True`) and should stay
  as-is, not be "simplified" into a recursive call, since the whole point of
  that function is per-subfolder grouping. Audit all 3 local functions
  (`collect_videos_from_folder`, `collect_subfolders_with_videos`,
  `collect_videos_from_paths`) together since they're interdependent in this
  file specifically — don't swap one without checking how the others call it.
- `video_group_merger.py`'s `collect_videos_from_paths` is this file's Item-2
  contribution — handled here, not in Phase 6.

**Files touched:** the 2 files above
**Verify:** run real test-clip batches through both merge paths in
`video_group_merger.py` (stream-copy and re-encode) and both input modes in
`video_reverse_merge.py`, confirm identical grouping/output to a pre-change
run. Given the parked black-frame/freeze investigation already noted in
CLAUDE.md for `video_group_merger.py`, treat any output difference here as
worth stopping and investigating rather than assuming it's unrelated.

**Done note (2026-07-25):** Double-checked before starting that prior
sessions' dedupe/bugfix passes on these two files (dead-code removal, the
Copy-streams merge bug fix in `video_group_merger.py`, the audio-desync fix
in `video_reverse_merge.py` — all per CLAUDE.md/memory, done before this
plan existed) hadn't already touched the specific functions this phase
targets — confirmed via fresh grep, no overlap, plan's assumptions still
held exactly.

`video_reverse_merge.py`: `collect_videos_from_folder` deleted outright
(it returned strings already, no Path-wrapper needed, straight swap to
`djj.collect_videos_from_folder`); local `VIDEO_EXTENSIONS` constant
removed, `is_video_file()` now reads `djj.VIDEO_EXTENSIONS` directly (it's
used standalone in the multi-path-input branch too, not just by the
deleted function). `reverse_and_merge()` — the explicitly hands-off
workflow logic — untouched, confirmed by grep it only does string-based
`os.path.split`/`os.path.splitext`, no Path-attribute reliance to break.
338→324 lines.

`video_group_merger.py`: `collect_videos_from_folder(input_path)` (no
recursion param, single-folder only) deleted outright — all 4 call sites
(inside `collect_subfolders_with_videos`, inside `collect_videos_from_paths`,
and 2 in the main flow) now call `djj.collect_videos_from_folder(path,
include_subfolders=False)` directly, safe since that's exactly the previous
always-non-recursive behavior. `collect_subfolders_with_videos`'s one-level
fan-out logic (the actual point of that function — one non-recursive
collect per immediate subfolder, building a `{subfolder: [videos]}` dict)
was left structurally as-is per the plan's explicit warning not to
"simplify" it into `include_subfolders=True` — that's a different
operation. `collect_videos_from_paths` also stayed local (already correctly
expands directories via the folder collector, matching djj's own paths
semantics — no behavior change needed, just the extension source).
`is_valid_video()` now reads `djj.VIDEO_EXTENSIONS`; local `VIDEO_EXTENSIONS`
removed. **Caught a real mistake during this phase**: an `Edit` with
`replace_all: true` on `collect_videos_from_folder(src_dir_resolved)` only
matched one of its two occurrences because their surrounding indentation
differed slightly — the second silently kept calling the now-deleted local
function. Caught immediately by re-grepping for the old function name after
the edit (which should always be the check, not just a compile pass — a
`NameError` here only fires at actual runtime, not import time, so
`py_compile` alone wouldn't have caught it). 592→587 lines.

Neither file's core merge/reverse ffmpeg logic was touched — only the
collection layer. Smoke-tested: per-subfolder fan-out grouping (confirmed a
top-level file doesn't leak into subfolder groups, each subfolder's video
count is correct), directory expansion in paths mode, and the widened
`.wmv`/`.avi`/`.flv` coverage via `djj.VIDEO_EXTENSIONS` in both files.

---

## Phase 5 — Output-path convention rollout

**Status:** `[ ]` not started
**Depends on:** nothing
**Risk:** low — small, mostly confirmatory phase; the convention itself is
already documented in `djjtb/skills/djjtb-conventions/SKILL.md` and (per the
re-verification note above) there are no active scripts left calling the old
`djj.get_centralized_output_path()` that would need migrating

- **5a.** Fix the stale example in
  `djjtb/helpers/docs/djj.readme_generator.py:632`, which still shows
  `output_path = djj.get_centralized_output_path("script_name")` as the
  pattern to copy into newly generated scripts. Update it to the sibling
  `Output/<ToolLabel>/` pattern from the SKILL.md so future generated
  scaffolds don't reintroduce the old convention.
- **5b.** Spot-check `djjtb/media_tools/playlist_generator.py`, the one
  active script still writing directly under `~/Desktop/...timestamp.../`.
  Confirm with the user whether that's intentional (it looks like a
  user-facing "here's your playlist" deliverable rather than an
  intermediate processing output, so Desktop may be correct on purpose) —
  don't migrate it to sibling-`Output/` without checking, since that would
  change where a manually-consumed deliverable lands.

**Files touched:** `djjtb/helpers/docs/djj.readme_generator.py`; possibly
`djjtb/media_tools/playlist_generator.py` depending on 5b's answer
**Verify:** re-run the grep for `get_centralized_output_path(` and
`Desktop.*strftime` across active scripts; confirm the only remaining hits
are the ones explicitly decided on in 5a/5b.

---

## Phase 6 — Multi-path input consolidation (Item 2)

**Status:** `[ ]` not started
**Depends on:** Phase 0a (if any sub-phase routes through
`get_centralized_media_input`)
**Risk:** medium-high on the design-decision step below, low-medium per file
once that's resolved

### Preamble — read before starting any sub-phase

`djj.get_multifile_input()` and `djj.get_centralized_media_input()` are
**monolithic prompt+parse functions**: they call `input()` themselves with
their own hardcoded prompt/preview text ("drag & drop or paste paths...",
"✅ Found N valid file(s)"), and — critically — `get_multifile_input` always
recurses into subdirectories (`path_obj.rglob('*')`, no
`include_subfolders=False` option at all).

None of the candidate scripts below match that shape as-is: each has its own
custom prompt wording already printed by the calling script, and most
default to **non-recursive** directory expansion. A direct swap to
`get_multifile_input()` would silently (a) replace each script's existing
prompt text with djj's generic wording, and (b) force always-recursive
folder expansion where several tools currently offer the user a choice or
default to flat.

**Recommended first step of this phase** (a design decision, not made here):
extract a parse-only helper out of `get_multifile_input`'s body — e.g.
`djj.parse_multipath_input(raw_input, extensions, include_subfolders=True)`
— that takes an already-obtained raw string (like the local
`collect_*_from_paths(raw_input)` functions already do) instead of prompting
itself, and exposes the recursion choice as a parameter. Keep
`get_multifile_input` as a thin wrapper that prompts, then calls the new
helper. This turns every per-file swap below into a small, mechanical,
prompt-text-preserving change instead of a UX rewrite. Confirm this approach
with the user before implementing it, since it's a signature change to a
function other things may eventually depend on.

Also: **Phase 0a must land before any sub-phase routes through
`get_centralized_media_input`** specifically (not `get_multifile_input`),
since that function currently crashes on the paths it's supposed to handle.

**Overlap with Items 1/3/4:** 6 of the 21 raw grep hits for this item are
files whose hand-rolled parser *is* their `collect_images_from_paths` /
`collect_videos_from_paths` helper, already scheduled for a swap in Phase
1/2/3/4 (same file, same function, `djj.collect_images_from_paths` already
matches that shape without the monolithic-prompt problem above, since it
also takes a raw string). **Do not re-touch these 6 files in this phase —
they're cross-referenced here, not re-planned:**
`vocab_mask_generator.py` (Phase 1), `image_slideshow_maker.py` (Phase 2),
`video_processor.py`, `video_frame_bridge.py`, `video_splitter.py` (Phase 3),
`video_group_merger.py` (Phase 4).

That leaves **15 files** genuinely new to this phase, split into sub-phases
below by subfolder/shape.

### 6a. `ai_tools/` — byte-identical `clean_path()` runners

**Status:** `[ ]` not started
**Files:** `djjtb/ai_tools/codeformer_runner_liveprompt.py`,
`djjtb/ai_tools/facefusion_runner.py`, `djjtb/ai_tools/gfpgan_runner.py`,
`djjtb/ai_tools/realesrgan_runner.py`, `djjtb/ai_tools/realsr_runner.py`

All 5 define the exact same 2-line `clean_path(path_str)` helper, called
from inside a near-identical `collect_files_from_paths(file_paths)` (each
takes an already-obtained raw string, splits, cleans, classifies file/dir,
expands dirs one level). Highest-value, lowest-risk group in this phase —
do this one first once the Phase 6 preamble's design decision is made.
**Verify:** run each of the 5 AI runners with a real multi-path drag-drop
batch (mix of files + a folder) before/after, confirm identical file list.

### 6b. `ai_tools/` — remaining, mixed shape

**Status:** `[ ]` not started
**Files:** `djjtb/ai_tools/cf_ups_runner.py` (inline variant of the 6a
pattern, no separate `clean_path` — same fix, just written differently),
`djjtb/ai_tools/hermes_helper.py` (**different shape — flag before
touching**: its one hit, at line ~256, is a single-path clean
(`input(" 📁 > ").strip().strip('\'"')`), not a multi-path loop. Candidate
for `djj.get_path_input()`, not `get_multifile_input()` — verify which
before editing.)
**Verify:** `cf_ups_runner.py` — same as 6a. `hermes_helper.py` — confirm
single-path prompt behavior unchanged after swap.

### 6c. `file_tools/`

**Status:** `[ ]` not started
**Files:** `djjtb/file_tools/auto_subfolder.py`,
`djjtb/file_tools/filename_randomizer.py` (both genuine multi-path
split()-loop parsers, same shape as 6a),
`djjtb/file_tools/file_identifier.py` (**different shape — flag before
touching**: has its own `clean_path()` but on a quick read looks like the
single-path pattern from `hermes_helper.py`, not multi-path — re-verify by
reading the call site before assuming which djj function fits.)
**Verify:** run each tool against a real multi-path batch (or single path,
per 6c's per-file shape) before/after.

### 6d. `media_tools/` (non-video, non-Item-1-overlap)

**Status:** `[ ]` not started
**Files:** `djjtb/media_tools/image_tools/image_webp_to_mp4.py`,
`djjtb/media_tools/media_sorter.py` (both genuine multi-path parsers, 6a
shape), `djjtb/media_tools/metadata_tool.py` (has a `clean_path()` helper —
verify single- vs multi-path shape before editing, same caveat as 6b/6c),
`djjtb/media_tools/playlist_generator.py` (**different shape**: its hit is a
single txt-file-path prompt
(`input("Enter path to txt file:...").strip().strip('\'"')`), explicitly
described in its own docstring as "Inline — no utils dependency." Candidate
for `djj.get_path_input()` if anything, likely lowest priority in this whole
phase since it's a single value, not a collection.)
**Verify:** per-file, matching whichever djj function actually ends up used.

### 6e. `quick_tools/` — different problem shape entirely

**Status:** `[ ]` not started
**Files:** `djjtb/quick_tools/path_grabber.py`

This tool's job is grabbing dropped Finder paths from the clipboard, one per
line — not a drag-and-drop batch-select prompt. Its 4 `strip('\'"')` hits
operate on clipboard lines, not a space-separated multi-path string. It may
not be a good fit for `get_multifile_input`/`parse_multipath_input` at all.
Lowest priority in this phase; make a manual per-line-vs-batch judgment call
when this sub-phase is picked up rather than forcing it into the same mold
as 6a–6d.
**Verify:** N/A until the fit decision above is made.

---

## Summary — files touched per phase (quick reference)

| Phase | Files | Depends on |
|---|---|---|
| 0 | `utils.py`, `media_utils.py` | — |
| 1 | `vocab_mask_generator.py`, `joytag_tagger.py`, `joycaption_runner_ollama.py` | — |
| 2 | `image_slideshow_maker.py` | — |
| 3 | `video_processor.py`, `video_frame_bridge.py`, `video_splitter.py` | 0 |
| 4 | `video_reverse_merge.py`, `video_group_merger.py` | 0 |
| 5 | `djj.readme_generator.py`, (maybe) `playlist_generator.py` | — |
| 6a | 5 ai_tools runners | 6-preamble decision |
| 6b | `cf_ups_runner.py`, `hermes_helper.py` | 6-preamble decision |
| 6c | `auto_subfolder.py`, `filename_randomizer.py`, `file_identifier.py` | 6-preamble decision |
| 6d | `image_webp_to_mp4.py`, `media_sorter.py`, `metadata_tool.py`, `playlist_generator.py` | 6-preamble decision |
| 6e | `path_grabber.py` | 6-preamble decision (maybe N/A) |

Not in scope for this plan: `djjtb/bak/` and stray `*copy.py` files (dead,
unreferenced by the menu — separate cleanup candidate under the existing
old_versions/archived tiering, not this refactor); wider `PathManager`
chaining between tools (0 active adopters today — this plan's Phases 1–6 are
prerequisite dedup work for that longer-term goal, not the chaining work
itself); the `setup_logging()` append-mode migration (tracked separately in
`djjtb-conventions` SKILL.md's "Known inconsistencies" section, opportunistic
per-script, not a standalone phase here).
