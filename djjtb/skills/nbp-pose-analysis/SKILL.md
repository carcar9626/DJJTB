---
name: nbp-pose-analysis
description: Analyzes NBP pose grids or single pose reference images and writes technical pose prompts in strict NBP format. Trigger whenever the user uploads a pose grid or unlabeled pose reference image together with the phrase "prompts please" (or similar), or otherwise asks for NBP-style pose prompts from an image. Produces output in the exact format the nbp-prompt-assembler skill expects to file.
---

# NBP pose analysis — "prompts please" trigger

This is based on the instruction set already running as the system prompt
for the user's Gemma4 model in Open WebUI. Reusing it verbatim keeps
Claude and Gemma4 producing identically formatted output from the same
grid — **the Gemma4 system prompt needs this same composition/pose split
applied to it directly** to stay in sync; this file doesn't update that
one automatically.

## When to use this

The user uploads a pose grid (multiple poses) or a single, unlabeled pose
reference image, together with "prompts please" or a similar phrase. Any
reference numbers visible on the grid are for the user's own tracking —
ignore them for output purposes. Identify and describe each distinct pose
shown, in left-to-right / top-to-bottom order; final numbering is assigned
automatically at filing time, not here.

## Output format (strict — do not deviate)

Pose descriptions are body-mechanics only now. Camera angle, lens feel,
and framing/crop live entirely in the user's separate `composition`
category (a small, curated preset library they select independently, not
something generated per pose) — do not describe camera perspective here
at all.

For every pose in the image, output:

```
#[CAPITALIZED_DESCRIPTIVE_NAME]#
[Extremely detailed anatomical and mechanical description covering:
 - Body Orientation & Pose Type (e.g. prone, kneeling profile, asymmetrical seated pose)
 - Limb Placement & Skeletal Tension (precise knee/elbow/wrist angles; tucked, extended, or crossed)
 - Weight & Grounding (how weight settles, how the body contacts the surface/prop)
 - Gaze & Engagement (exact nature of eye contact)]
```

No "POSE No." line — the filing skill assigns real numbers automatically.

## Constraints (strict — this is what makes output filing-ready)

- **No jargon overload**: don't include meta-labels like "Z-Depth" or
  "Texture Override" — integrate those concepts directly into the
  descriptive prose instead.
- **No camera or framing language**: no angle, lens, distance, or crop
  descriptions (e.g. "low angle," "85mm," "waist-up") — that's the
  `composition` category's job, handled separately by the user.
- **No meta-talk**: no introductory, explanatory, or concluding
  conversational text. Don't say "here are the prompts" or similar.
- **Pure content**: output is a clean, professional list of technical
  prompts only — nothing else in the response.
- Do not create images or videos unless separately requested or confirmed.

## After analysis

If the user also asks to file the results (or it's clear from context they
want them added to their prompt assembler), hand the output straight to
the **nbp-prompt-assembler** skill — the format above is exactly what it
expects as input. Don't reformat or summarize the pose text in between.
