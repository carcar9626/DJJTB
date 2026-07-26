# DJJTB — Centralized I/O / Cross-Tool Chaining Plan

**Status:** in progress — Phase A done, Phase B (wiring the 2 pilot pairs) not started
**Created:** 2026-07-25
**Branch:** `worktree-centralized-io-chaining` in
`.claude/worktrees/centralized-io-chaining` — fully isolated from `main`,
per user's explicit request given how workflow-critical/fragile this
feature could become. Nothing here reaches `main` until thoroughly tested
and the user says so.

**User's long-term reference point (2026-07-25, not being built now):**
eventual 3-hop chain — `video_frame_bridge.py` (extract) →
`image_processor.py` (trim/resize) → `facefusion_runner.py`. Confirmed
explicitly as "not immediate," just context for what the finished feature
should eventually support. The single-most-recent-output-slot design
(Phase A, Q2) naturally supports chains like this already — each hop's
output becomes the next hop's "previous output" in sequence — so this
doesn't require different plumbing, just more pairs wired later (Phase C).
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

**Status:** `[x]` done (2026-07-25)
**Depends on:** nothing
**Risk:** this is the one decision that reshapes every later phase — don't
skip straight to wiring individual tools before this is settled

**Decisions (confirmed with user, 2026-07-25):**

1. **Storage shape**: extend `PathManager`'s existing JSON file, not a
   separate file. Confirmed.
2. **One slot, not a history.** Only the single most-recent output is ever
   remembered, overwritten every time any tool finishes. User confirmed
   this explicitly. Note: this still supports the multi-hop reference
   workflow above fine — each hop just overwrites the slot with its own
   output before the next hop reads it.
3. **Staleness cutoff: 1 hour.** After that, `load_last_output()` returns
   `None` (falls through to the normal prompts silently) rather than
   offering something stale. User confirmed the record is only ever
   replaced when a tool *finishes and produces new output* — declining the
   offer and picking input manually does **not** clear or affect the slot;
   it only changes when something new is actually produced.
4. **Type/extension matching**: reuse the existing `extensions=` convention
   from `djj.collect_images_from_folder`/`collect_videos_from_folder`/
   `parse_multipath_input` — no new convention.
5. **What counts as "output"**: confirmed per-pilot in Phase B rather than
   generalized up front — `image_processor.py`'s simple modes already
   return a single canonical `output_dir` (via `djj.get_output_directory`),
   re-scanned by the consumer; that's the shape being used for both pilot
   pairs, not a raw file-path list. Known edge case, not fixed now: if
   input spans multiple subfolders, `image_processor.py`'s own in-tool
   chain loop already only tracks the first canonical folder, not all of
   them — the new cross-tool recording inherits the same limitation
   consistently rather than fixing an unrelated pre-existing gap while
   building something new.

**Finalized function signatures (implementing next):**

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

**Done note (2026-07-25):** `save_last_output(script_name, output_paths)`
and `load_last_output(extensions=None, max_age_seconds=3600)` added right
after `path_manager = PathManager()` in `djjtb/utils.py`, storing under a
reserved `_last_output` key in the same JSON file (leading underscore, safe
since no real script is ever named that). Smoke-tested in isolation (6
checks): empty-state returns `None`; save/load round-trips correctly;
extension filtering both matches and correctly excludes non-matching
paths; staleness cutoff correctly returns `None` for a simulated 2-hour-old
record against the 1-hour default, and correctly ignores staleness when
`max_age_seconds=None`; a second `save_last_output()` call overwrites the
first (single slot, confirmed, not a history); `path_manager.cleanup()`
clears it along with everything else it manages. No script wiring yet —
that's Phase B, not started.

**Session ended here (context-limited) — for whoever picks this up next:**
Phase A is fully done and tested. Phase B (wiring the 2 confirmed pilot
pairs into `image_processor.py`/`facefusion_runner.py` and
`video_processor.py`/`video_splitter.py`) has **not been started** — no
changes to any of those 4 files yet. This is a clean, safe stopping point:
the new functions exist and work, but nothing calls them yet, so no
existing tool's behavior has changed at all. Read Phase B's section above
in full before starting — it already has the exact scope, the known
`run_reencode`/`run_speed_change`/`run_crop` return-value gap, and the
"simple modes only" boundary worked out. Don't re-derive any of that from
scratch.

---

## Phase B — Two confirmed pilot pairs

**Status:** `[ ]` not started
**Depends on:** Phase A
**Risk:** medium — first real proof this actually feels good to use, not
just correct in isolation

Two pairs confirmed with user (2026-07-25), chosen to exercise the
mechanism across two different tool categories (image tool → AI tool, and
video tool → video tool), not just prove it once and assume it generalizes:

**Pair 1: `image_processor.py` → `facefusion_runner.py` (target images).**
The real workflow the user described: trim+resize in image_processor, use
that output as FaceFusion's target images. Scoped to image_processor's
*simple* modes only (Pad, Crop, Crop+Resize, Resize-only, Rotate/Flip,
Convert, Strip padding) — Pairing/Join/Collage (mode 6) explicitly
excluded, reusing the exact same boundary the script's own existing
in-tool "run another operation?" chain loop already draws, for the same
reason (non-uniform/possibly-multiple output shape). Only FaceFusion's
*target*-image input gets the new offer, not its *source*-image slot —
that's not the workflow described.

**Pair 2: `video_processor.py` → `video_splitter.py`.** Needs one small
prerequisite change discovered while scoping this: `run_reencode`/
`run_speed_change`/`run_crop` currently don't `return` anything at all
(unlike `image_processor.py`'s `run_*` functions, which already return
`output_dir`) — add that return first, mirroring the existing
image_processor.py convention, before wiring the save call.

For each pair: producer calls `djj.save_last_output(...)` right after it
finishes producing files (not at input-collection time — this is the part
that's actually new, existing code has never done this). Consumer's
input-mode prompt gains a new leading option — "0. Use previous output (N
files from <tool>, <time> ago)" — only shown when `load_last_output()`
returns something extension-matched and fresh enough within the 1-hour
window.

**Files touched:** `djjtb/media_tools/image_tools/image_processor.py`,
`djjtb/ai_tools/facefusion_runner.py`,
`djjtb/media_tools/video_tools/video_processor.py`,
`djjtb/media_tools/video_tools/video_splitter.py`
**Verify:** real end-to-end run exactly like the dedup plan's Combo 1/Combo
2 tests — run producer, then consumer, confirm the offer appears with the
right count/age, confirm selecting it collects exactly the producer's
output files, confirm declining it still falls through to the normal
prompts unchanged, confirm the offer disappears after the 1-hour window
(or is absent for a fresh `PathManager` state).

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

## Decision log (all resolved 2026-07-25, before any code was written)

- Single most-recent-output slot, not a history — confirmed.
- Staleness cutoff: 1 hour — confirmed.
- Pilot pairs: image_processor.py → facefusion_runner.py (target images),
  video_processor.py → video_splitter.py — confirmed, chosen specifically
  to span two tool categories rather than prove the mechanism once.
