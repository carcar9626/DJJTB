"""
add_pose_prompts.py

Parses NBP pose-analysis output (blocks of "#NAME#\ndescription", no
number required) and appends each pose to the "pose/action" array of a
prompt_assembler.json file. Pose numbers are assigned automatically,
continuing from the highest existing "P<number>-" title already in the
file — no manual grid labeling needed, regardless of whether the input
has 1 pose or several.

Usage:
    python3 add_pose_prompts.py <json_path> <raw_text_path>
"""

import json
import re
import sys
from pathlib import Path

POSE_BLOCK = re.compile(
    r"^#(.+?)#\s*\n(.+?)(?=\n^#.+?#\s*\n|\Z)",
    re.DOTALL | re.MULTILINE,
)
TITLE_NUMBER = re.compile(r"^P(\d+)-")


def parse_pose_output(raw_text: str) -> list[dict]:
    """Turn raw NBP pose output into a list of {"name", "description"} pairs, in order."""
    blocks = []
    for name, desc in POSE_BLOCK.findall(raw_text.strip() + "\n"):
        blocks.append({"name": name.strip(), "description": desc.strip()})
    return blocks


def next_pose_number(data: dict, category: str) -> int:
    """Highest existing P<number>- in the category, plus one. Starts at 1 if none exist."""
    max_n = 0
    for entry in data.get(category, []):
        m = TITLE_NUMBER.match(entry.get("title", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def add_pose_prompts(raw_text: str, json_path: Path, category: str = "pose/action") -> list[str]:
    """Parse raw_text and append the resulting entries to json_path's category array.

    Pose numbers are assigned automatically and sequentially, continuing
    from the file's current highest P-number. Returns the list of titles
    added. Writes a <name>.json.bak backup before touching the file.
    """
    raw_original = json_path.read_text(encoding="utf-8")
    data = json.loads(raw_original)
    if category not in data:
        raise KeyError(f"'{category}' not found in {json_path.name}")

    blocks = parse_pose_output(raw_text)
    if not blocks:
        raise ValueError("No '#NAME#' pose blocks found in the input text.")

    json_path.with_suffix(json_path.suffix + ".bak").write_text(raw_original, encoding="utf-8")

    start = next_pose_number(data, category)
    new_entries = []
    for i, block in enumerate(blocks):
        title = f"P{start + i:02d}-{block['name']}"
        new_entries.append({"title": title, "prompt": block["description"]})

    data[category].extend(new_entries)
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return [e["title"] for e in new_entries]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 add_pose_prompts.py <json_path> <raw_text_path>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    text = Path(sys.argv[2]).read_text(encoding="utf-8")
    added = add_pose_prompts(text, json_path)
    print(f"Added {len(added)} pose(s):")
    for title in added:
        print(f"  - {title}")