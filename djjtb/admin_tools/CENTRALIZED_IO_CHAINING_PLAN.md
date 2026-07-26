# DJJTB — Centralized I/O / Cross-Tool Chaining Plan

**Status:** planning only, execution not started
**Created:** 2026-07-25
**Purpose:** the actual next step CLAUDE.md's "Current goal" describes — letting
a tool's output flow into the next tool through the launcher — now that
`UTILS_DEDUP_REFACTOR_PLAN.md`'s prerequisite dedup work (all 7 phases) is
done. This doc is lighter than that one: it hasn't had a full per-file
investigation pass yet, and says so explicitly wherever that matters. Treat
Phase A below as required reading/verification before touching any other
phase, and expect it to reshape later phases once done.

**How to use this doc:** same convention as `UTILS_DEDUP_REFACTOR_PLAN.md`
— check boxes, done-notes, one phase at a time, update in place.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## What's actually true today (verified 2026-07-25, not assumed)

- **`PathManager` (`djjtb/utils.py:777`) is single-script session memory,
  not cross-tool chaining.** `save_paths(script_name, paths, extra)` /
  `load_paths(script_name)` are both keyed by *the calling script's own
  name*. The only two real call sites — `get_centralized_media_input()`
  and `get_centralized_output_path()` — use it so a script can remember
  its *own* last input paths (e.g. for a "same folder as input" output
  option), not so a *different* script can discover what it produced.
  There is currently no code path anywhere that lets Tool B ask "what did
  Tool A just produce?" — this has to be built from scratch, not just
  wired up.
- **What gets saved today is the *input* a script collected, not its
  *output*.** `get_centralized_media_input()` saves `media_files` (what
  the user pointed the tool at) under the tool's own name. For real
  chaining, what matters is a tool's *output* (its final rendered/produced
  file(s)) — nothing currently saves that anywhere.
- **`get_centralized_media_input()`/`get_centralized_output_path()` have 0
  real active callers** (confirmed during the dedup plan's Phase 0/5 —
  `get_centralized_media_input` had a live arg-count bug, since fixed,
  that had gone unnoticed for exactly this reason). Building chaining on
  top of these two specifically means also giving them their first real
  adopters, not just extending already-proven infrastructure.
- **Architectural constraint, not a design choice**: every djjtb tool runs
  as its own subprocess in a fresh Terminal.app tab (`djj.run_script_in_tab`/
  `open_terminal_with_settings`), a separate OS process with no shared
  memory with `djjtb.py` or with each other. The *only* way Tool A's output
  can reach Tool B is through **persisted state on disk** — there is no
  in-memory handoff possible, ever, regardless of design. `PathManager`'s
  JSON-file-in-/tmp approach is the right *shape* for this reason; it's
  the *content* (input vs. output, single-script-keyed vs. discoverable)
  that needs to change.

---

## Phase A — Design the actual state format (do this first, changes everything after)

**Status:** `[ ]` not started
**Depends on:** nothing
**Risk:** this is the one decision that reshapes every later phase — don't
skip straight to wiring individual tools before this is settled

Open questions this phase needs to resolve (propose an answer, confirm with
user, don't just pick one silently — this is a new feature, not a refactor
with an obviously-correct preserve-existing-behavior answer):

1. **Storage shape.** Extend `PathManager`'s existing JSON file
   (`/tmp/djjtb_paths.json`) with a new top-level key like `_last_output`
   (script name, output paths, output dir, timestamp, file kind) alongside
   the existing per-script keys — or a wholly separate small state file?
   Reusing the existing file is probably right (one less thing to clean
   up, `path_manager.cleanup()` already exists) but confirm before building
   on it.
2. **One slot or a short history?** Simplest: only ever remember the *one*
   most recent output, overwritten each run. Richer: keep the last N (3-5)
   so a user who ran two tools since could still pick either. Recommend
   starting with one slot — matches "let's hope nothing breaks" caution,
   easy to extend to a history list later without a breaking format change
   if the single slot is itself stored as `{"history": [...]}`.
3. **Staleness rule.** Should a 3-day-old "previous output" still be
   offered as a one-tap option, or does it need a cutoff (e.g. only offer
   if produced within the last N hours, else silently fall through to the
   normal input prompt)? Affects whether users get a surprising stale
   suggestion.
4. **Type/extension matching.** If Tool A produced videos and Tool B only
   accepts images, the offer needs to not appear (or say why it's greyed
   out) rather than let the user select it and hit an empty/wrong result.
   Needs the same `extensions=` concept already threaded through
   `djj.collect_images_from_folder`/`collect_videos_from_folder`/
   `parse_multipath_input` from the dedup plan — reuse that, don't
   reinvent a second extension-matching convention.
5. **What counts as "output."** A tool like `video_processor.py`'s
   re-encode mode produces one output file per input video, scattered
   across possibly multiple `Output/Reencoded/` subfolders (one per input
   video's parent, per the per-source-folder output convention). "The
   output" for chaining purposes is probably the flat list of all produced
   file paths, not a single directory — confirm this reads true across a
   few real tools before assuming it's universal (see Phase B).

**Proposed new function (draft, not final — refine after Phase A's
questions are answered):**

```python
def save_last_output(script_name, output_paths, output_kind=None):
    """Record what a tool just produced, for the next tool to discover."""
    ...

def load_last_output(extensions=None, max_age_seconds=None):
    """
    Return the most recent recorded output (as a dict with paths/script_name/
    timestamp), or None if nothing recorded, too stale, or none of its
    paths match `extensions`. This is what a consuming tool's input-selection
    prompt calls to decide whether to offer a "use previous output" choice.
    """
    ...
```

**Files touched:** `djjtb/utils.py` only
**Verify:** unit-test both functions directly (no script changes yet) —
save a fake output, load it back, confirm staleness cutoff and extension
filtering both work, confirm `PathManager.cleanup()` still clears
everything including the new key.

---

## Phase B — Pick 2-3 real producer→consumer pairs, wire those first

**Status:** `[ ]` not started
**Depends on:** Phase A
**Risk:** medium — first real proof this actually feels good to use, not
just correct in isolation

Don't wire all ~40 tools at once — same phased caution as the dedup plan.
Pick a small number of *actually-common* real workflows first, confirm the
UX is right, then expand. Candidates to evaluate (not yet verified against
actual code — read each tool's real end-of-run output-producing code before
committing to the pairing, the way every phase of the dedup plan did):

- `image_processor.py` (crop/pad/resize output) → `image_slideshow_maker.py`
  (the workflow implied by the user's own question this session: "I just
  ran image_processor... shouldn't slideshow maker ask if I want to use
  previous output?")
- `video_processor.py` (re-encode/crop output) → `video_splitter.py` or
  `video_frame_bridge.py`'s extract mode
- One AI-tool pairing, e.g. `cf_ups_runner.py`'s upscaled output →
  `video_slideshow_watermark.py` or similar, if that's a workflow the user
  actually uses (ask before assuming)

For each pair: producer calls `djj.save_last_output(...)` right after it
finishes producing files (not at input-collection time — this is the part
that's actually new, existing code has never done this). Consumer's
input-mode prompt gains a new leading option — "0. Use previous output (N
files from <tool>, <time> ago)" — only shown when `load_last_output()`
returns something extension-matched and fresh enough.

**Files touched:** TBD once pairs are confirmed with user
**Verify:** real end-to-end run exactly like this session's Combo 1/Combo
2 tests — run producer, then consumer, confirm the offer appears with the
right count/age, confirm selecting it collects exactly the producer's
output files, confirm declining it still falls through to the normal
prompts unchanged.

---

## Phase C — Decide the expansion path

**Status:** `[ ]` not started
**Depends on:** Phase B proving out
**Risk:** low — by this point the mechanism is proven, this is just
breadth

Once Phase B's pilot pairs feel right in real use, decide (with the user,
not unilaterally): expand to more tool pairs one at a time following the
same phased pattern as the dedup plan, or fold the "offer previous output"
check directly into the shared `djj.collect_images_from_folder`-adjacent
input helpers so *every* tool gets it for free going forward without
per-tool wiring. The latter is more elegant but is a bigger, riskier change
to touch that many call sites at once — probably still wants to happen
file-by-file/phase-by-phase rather than in one sweep, matching everything
this session has done.

---

## Explicitly not decided yet (surface to user before Phase A starts for real)

- Single most-recent-output slot vs. short history (Phase A, Q2)
- Staleness cutoff value, if any (Phase A, Q3)
- Which producer→consumer pairs actually match how the user works, vs.
  which just seem plausible from reading code (Phase B)
