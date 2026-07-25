---
name: djjtb-conventions
description: Repeated conventions for DJJTB's interactive CLI scripts — ANSI color meanings, header banner format, input/output path handling, and the exit/return-to-menu loop. Use whenever writing a new script under djjtb/media_tools, djjtb/ai_tools, djjtb/file_tools, or djjtb/quick_tools, or editing an existing one, so it matches the rest of the toolbox without re-deriving the pattern from scratch.
---

# DJJTB script conventions

DJJTB scripts are interactive CLIs launched in their own Terminal tab from
`djjtb.py`'s menu (see project `CLAUDE.md` for the launcher mechanics). This
skill documents the conventions that repeat across the ~85 real tool
scripts (not `old_versions/`, `bak/`, or per-tool venvs) so new scripts read
as part of the same toolbox. Everything already enforced by
`djjtb/utils.py` is referenced by function name here, not restated — read
the function's docstring in `djjtb/utils.py` for exact behavior.

## Script skeleton

```python
import os
import sys
import pathlib
import djjtb.utils as djj
# ... other stdlib/third-party imports

os.system('clear')

# ─── Helpers ─────────────────────────────────────────────────────────────────
# (module-level helper functions)

def main():
    while True:
        print()
        print("\033[92m" + "="*50 + "\033[0m")
        print("\033[1;93mScript Title\033[0m")
        print("Optional one-line description")
        print("\033[92m" + "="*50 + "\033[0m")
        print()

        # ... prompt for input, do the work ...

        djj.prompt_open_folder(output_dir)

        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == "__main__":
    main()
```

`os.system('clear')` runs once at import time (module level), not inside the
loop — the loop only clears implicitly via `djj.what_next()`'s "Go Again"
path (see below).

## ANSI color legend

`\033[<code>m ... \033[0m` — always paired with a reset. Colors carry
meaning; don't pick one decoratively.

| Code | Meaning | Example |
|---|---|---|
| `\033[93m` | Default prompt/label/info text — the workhorse color | `\033[93mEnter folder path:\033[0m` |
| `\033[92m` | Success, and decorative `====`/`----` rule lines | `\033[92m✅ Found 5 file(s)\033[0m` |
| `\033[91m` | Error / failure | `\033[91m❌ Path does not exist\033[0m` |
| `\033[1;93m` (or `\033[1;33m`) | Bold — section/script titles only | `\033[1;93mVideo Group Merger\033[0m` |
| `\033[96m` | Secondary info / timing notes (used sparingly) | `\033[96m⏱️ completed in 4.2s\033[0m` |

Emoji vocabulary follows the same split: ✅ success, ❌ error, ⚠️ warning,
📁/📂 folder selection, 🎯 target/goal, 🔄 in-progress, 🏁 completion banner.
Reuse these rather than introducing new ones.

## Terminal width

DJJTB always runs in a Terminal.app window resized and profiled by
`djj.setup_terminal()` — bounds `100, 200, 728, 1066`, profile `"djjtb"`
(SF Mono Medium 18pt). Measured directly via AppleScript, this is a fixed
**50 columns × 33 rows**, independent of the host screen's actual
resolution. Every printed line — menu entries, headers, prompts — needs to
fit within 50 visible columns or it wraps and throws off the whole
screen's alignment.

When counting width: ANSI escape codes (`\033[...m`) are zero-width, and
most emoji render as **2 columns wide**, not 1. The `"="*50` /
`"-"*50` decorative rule lines in the header skeleton above are already
sized to exactly this budget — treat that as the reference width for
everything else on the same screen.

This isn't enforced by tooling — there's no linter for it — so check by
eye (or count) before adding a new menu line or long print statement,
especially ones with multiple trailing emoji (easy to go over one emoji
at a time without noticing).

## Input handling

- **A single required path** (folder or file): `djj.get_path_input(prompt)`.
  Validates existence, retries up to `max_attempts`, exits on repeated
  failure. This is the standard — don't hand-roll path validation.
- **Multiple files/folders (drag-and-drop or space-separated paths)**: use
  `djj.get_multifile_input(prompt_text, extensions)`. It strips quotes,
  resolves each path, expands folders recursively, filters by extension,
  and prints a preview + warning summary. Older scripts (the majority, in
  practice) hand-roll this inline with `raw.split()` + manual
  `.strip('\'"')` — that's legacy duplication, not a pattern to copy into
  new code. Prefer `get_multifile_input` (or `get_centralized_media_input`
  if you also want the paths persisted via `PathManager` for chaining into
  a later script).

## Output path handling

Default convention — a sibling `Output/` folder next to the input, not a
Desktop/timestamp folder:

```python
output_dir = os.path.join(<resolved input folder>, "Output", "<ToolLabel>")
os.makedirs(output_dir, exist_ok=True)
```

`<ToolLabel>` is a short PascalCase/Title label for the tool (e.g.
`"VideoMerger"`, `"JoyTag"`, `"Collages"`) — check sibling scripts in the
same category for the label already in use if one exists.

Only fall back to `djj.get_centralized_output_path()` (Desktop, timestamped
subfolder) when there's a specific reason the sibling-folder default
doesn't fit — e.g. input isn't a single resolvable folder, or the user
explicitly wants Desktop output. It exists and is fully functional; it's
just not the default.

## Logging

Target convention (mid-migration — see "Known inconsistencies" below):

- **Location**: `djjtb/logs/<name>_log.txt` — lowercase `logs`, never beside
  the output folder. This is a flat directory shared by every tool, so keep
  the script-name prefix on the filename to avoid two tools' logs
  colliding (e.g. `image_processor_pad_log.txt`, not `pad_log.txt`).
- **Granularity**: one log file per meaningfully distinct operation, not
  one per script. `image_processor.py` already does this right —
  `image_processor_pad_log.txt`, `image_processor_convert_log.txt`,
  `image_processor_strip_log.txt`, etc. — match that pattern for any
  multi-mode script.
- **Continuous, not overwritten**: open in append mode, not `mode='w'`.
  The point is a running history you can scroll back through, not a
  scratch file that resets every run.
- **Write enough to debug from later, not just errors**: a run should
  leave a trace even when nothing failed — e.g. a start marker
  (`===== RUN START: <name> =====`) and one summary line at the end with
  the same counts already printed to screen (files in, files out,
  succeeded/failed, output folder). This is what actually catches the
  annoying case of "I batched 30 images and got 31 out" — the log should
  make that discrepancy visible after the fact, not just print-and-forget
  to the terminal.
- **When to add it**: not every script needs logging, and this is not a
  bulk retrofit — add or migrate logging only when you're already
  creating or substantively revising that script. Prioritize scripts that
  do real batch/file-count work over simple one-shot utilities.
- **Exception — `comfyui_batch`**: `djjtb/logs/comfyui_batch_logs/` keeps
  its own subfolder with one file per day (`YYYY-MM-DD.log`) plus
  `job_counter.txt`, set by `LOG_FOLDER` in
  `djjtb/ai_tools/comfyui/comfyui_batch.py`. Already migrated (not
  deferred like the rest) because these logs are actually read
  regularly — don't flatten this into the one-file-per-operation default
  above, and don't "fix" it to match the pattern.

### Known inconsistencies (don't copy these into new code)

`djj.setup_logging(output_path, script_name)` in `djjtb/utils.py` still
reflects the *old* behavior — writes to `<output_path>/<script_name>_log.txt`
(beside the output, not `djjtb/logs/`) in `mode='w'` (overwritten per run,
not continuous). About a dozen scripts call it this way today
(`image_processor.py`, `image_converter.py`, `video_cropper.py`,
`video_splitter.py`, `joytag_tagger.py`, and others). Don't extend that
old signature in new code — when you're already touching one of those
scripts, migrate its call site(s) to the target convention above instead
of adding more calls to the old form. `djj.utils.setup_logging()` itself
still needs updating to match (drop `output_path`, switch to append mode,
auto-emit the run-start line) — do that as part of the first script you
touch that uses it, then subsequent scripts just call the corrected
version.

## Exit / return-to-menu

`djj.what_next()` is the standard end-of-run prompt (used in the large
majority of scripts with a loop). Exact behavior:

```
What Next? 🤷🏻‍♂️
1. Go Again 🔁       -> clears screen, returns 'continue' (loop restarts)
2. Return to DJJTB ⏮️  -> switches Terminal to tab 1, returns 'exit'
3. Exit ✋🏼           -> returns 'exit'
```

Pair it with `djj.prompt_open_folder(output_dir)` immediately before it, if
the script produced output — that's the standard "want to see the
results?" step. Both go inside the `while True:` loop in `main()`, right
before the loop's `if action == 'exit': break`.

## Already-centralized — point here, don't restate

These are solved problems in `djj.utils` / `djj.media_utils` (re-exported
as `djj.*`). If you're about to write logic that matches one of these,
call the function instead:

- `djj.prompt_choice(prompt, choices, default=)` — validated menu input
- `djj.get_path_input(prompt)` — single required existing path
- `djj.get_multifile_input(...)` / `djj.get_centralized_media_input(...)` — multi-path drag-and-drop input
- `djj.prompt_open_folder(path)` — end-of-run "open output folder?" prompt
- `djj.what_next()` — end-of-run menu (see above)
- `djj.setup_logging(output_path, script_name)` — file logger, used by
  heavier batch/AI tools; not expected on every script
- `djj.apply_skip_list(file_list, root=)` — filters paths against the global skip list
- `djj.collect_images_from_folder` / `collect_images_from_paths` (from
  `media_utils`, re-exported) — image collection with extension filtering.
  A number of image/video scripts still define their own local
  `collect_images_from_folder`/`collect_videos_from_folder` instead of
  using this — that's pre-existing duplication, not something to
  replicate in a new script.
- `djj.run_script_in_tab(...)` / `djj.setup_terminal(...)` — only relevant
  if you're touching `djjtb.py`'s launcher itself, not a leaf tool script.

When in doubt, grep `djjtb/utils.py` for a matching function before writing
new path/prompt/logging plumbing.
