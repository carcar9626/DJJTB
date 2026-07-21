---
name: nbp-prompt-assembler-cowork
description: Files NBP pose-analysis output (the "POSE No. X / #NAME# / description" format) directly into the real, local pose/action category of the user's prompt_assembler.json — for Cowork or Claude Code sessions with a local folder attached. Use this instead of nbp-prompt-assembler whenever running with real local file access rather than a claude.ai chat upload.
---

# NBP prompt assembler — pose filing (Cowork / local file access)

Files pose-analysis output straight into the user's actual local
`prompt_assembler.json`, in place. This is the Cowork/Claude Code
counterpart to the **nbp-prompt-assembler** skill, which assumes a
claude.ai chat session with read-only uploads instead.

## When to use this

Same trigger as the chat version: the user has pose-analysis output in the
strict NBP format (see the **nbp-pose-analysis** skill) and asks to add,
file, or save it to their prompt assembler — but this time you have real
local file access (a Cowork session with a workspace folder attached, or
Claude Code), not an uploaded file in a sandbox.

## What to do

1. **Locate the real file.** Find `prompt_assembler.json` inside the
   attached/available local folder. Don't ask the user to upload it — you
   can already read it directly.

2. **Get the raw text.** The pose-analysis output the user just pasted, or
   that Claude generated earlier in the same session. Save it to a temp
   `.txt` file.

3. **Run the script directly against the real path:**
   ```
   python3 scripts/add_pose_prompts.py <real_local_path_to_json> <path_to_raw_text>
   ```
   It appends to the `pose/action` array, assigning pose numbers
   automatically (continuing from the highest existing `P<number>-` title
   already in the file — no numbers needed in the input text), and writes
   a `.bak` backup alongside the original file before changing anything.

4. **Confirm success and stop there.** Report which titles were added,
   read from the script's stdout. Do not copy the file anywhere, do not
   present it for download, and do not tell the user to replace their
   local file — the file the script just wrote *is* their local file.
   Treating it like a chat-sandbox delivery here would be actively
   confusing, not just redundant.

## If it fails

- **"No '#NAME#' pose blocks found"**: the pasted text isn't in the
  expected format. Show the user the expected format, don't guess at
  reformatting it yourself.
- **Permission or file-not-found error writing to the real path**: the
  folder likely isn't attached/accessible the way you assumed. Say so
  plainly rather than silently falling back to a download — that's what
  the plain **nbp-prompt-assembler** skill is for, not this one.

## Schema reference

`prompt_assembler.json` is one JSON object with these top-level category
arrays, each containing `{"title": ..., "prompt": ...}` objects:
`subject`, `outfit`, `composition`, `pose/action`, `spacial/add o   ns`,
`lighting`, `aesthetic`, `misc.`, `custom`. This skill only ever touches
`pose/action`.
