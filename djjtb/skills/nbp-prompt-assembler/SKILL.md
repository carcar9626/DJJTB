---
name: nbp-prompt-assembler
description: Files NBP pose-analysis output (the "POSE No. X / #NAME# / description" format) into the pose/action category of a prompt_assembler.json file. Use this whenever the user pastes pose-grid analysis output and asks to add, file, save, or update their prompt assembler with it, or mentions "prompt assembler," "pose/action," or filing NBP poses.
---

# NBP prompt assembler — pose filing

Files pose-analysis output into the user's `prompt_assembler.json`, matching
the exact schema and naming convention already used in that file.

## When to use this

The user has run a pose grid through their NBP/FLOW instructions (Claude,
Gemini, or Gemma4 in Open WebUI) and has output in this exact format:

```
#COUCH-BACK RECLINE CROSS-ANKLE#
<anatomical description...>
```

One or more blocks may appear back to back. No pose number is included —
the script assigns numbers automatically, continuing from the highest
existing `P<number>-` title already in the file. They'll ask to "add
these," "file these poses," "save this to my prompt assembler," or
similar.

## What to do

1. **Get the JSON.** Check this conversation for an uploaded
   `prompt_assembler.json`. If it's not there, ask the user to upload it —
   this only has to happen once per conversation. (If they're working in a
   Project, tell them adding it to Project knowledge means they won't have
   to re-upload it in future chats.)

2. **Get the raw text.** This is either the pose-analysis output the user
   just pasted, or output Claude itself just generated earlier in the same
   conversation. Save it to a temp `.txt` file.

3. **Run the script:**
   ```
   python3 scripts/add_pose_prompts.py <path_to_json> <path_to_raw_text>
   ```
   It appends to the `pose/action` array, following the existing
   `P<number>-<NAME>` title convention (e.g. `P55-COUCH-BACK RECLINE
   CROSS-ANKLE`), and writes a `.bak` backup of the original file before
   changing anything.

4. **Report back plainly** which titles were added — read them from the
   script's stdout, don't re-derive them yourself.

5. **Deliver the file.** Copy the updated JSON to the outputs directory and
   present it for download. Tell the user directly: this is a new file, not
   an edit to their local one — they need to replace their local
   `prompt_assembler.json` with this downloaded copy for the change to show
   up in their actual prompt assembler tool.

   This skill assumes a claude.ai chat session, where uploads are
   read-only. If you're running in Cowork or Claude Code with a real local
   file attached, use the **nbp-prompt-assembler-cowork** skill instead —
   it writes directly to the file in place.

## If it fails

If the script raises "No '#NAME#' pose blocks found," the pasted text
isn't in the expected format — don't try to reformat it yourself or guess
at names. Show the user the expected format above and ask them to paste
the actual model output, not a paraphrase.

## Schema reference

`prompt_assembler.json` is one JSON object with these top-level category
arrays, each containing `{"title": ..., "prompt": ...}` objects:
`subject`, `outfit`, `composition`, `pose/action`, `spacial/add ons`,
`lighting`, `aesthetic`, `misc.`, `custom`. This skill only ever touches
`pose/action`.
