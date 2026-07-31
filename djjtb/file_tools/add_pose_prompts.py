"""
add_pose_prompts.py

Parses NBP pose-analysis output (blocks of "#NAME#\ndescription", no
number required) and appends each entry to a chosen category array of
prompt_assembler.json. Titles get a per-category letter+number prefix
(e.g. "P01-", "S01-", "L01-", "O01-", "C01-"), continuing from the
highest existing "<prefix><number>-" title already in that category —
no manual grid labeling needed, regardless of whether the input has 1
entry or several. Pre-existing entries that don't follow the
prefix+number pattern are left untouched; numbering just continues
past whatever highest numbered title is already there.

Usage:
    python3 -m djjtb.file_tools.add_pose_prompts
"""

import json
import re
from pathlib import Path


JSON_PATH = Path("/Users/home/Documents/Scripts/FLOW_TOOLS/prompt_assembler/LOCAL/prompt_assembler.json")
TXT_FOLDER = "/Users/home/Documents/Scripts/FLOW_TOOLS/prompt_assembler/LOCAL/txt"

POSE_BLOCK = re.compile(
    r"^#\[?(.+?)\]?#\s*(.+?)(?=\n^#\[?.+?\]?#|\Z)",
    re.DOTALL | re.MULTILINE,
)

CATEGORY_PREFIX = {
    "pose/action": "P",
    "scene/setting": "S",
    "lighting": "L",
    "outfit": "O",
    "composition": "C",
}


def parse_pose_output(raw_text: str) -> list[dict]:
    """Turn raw NBP pose output into a list of {"name", "description"} pairs, in order."""
    blocks = []
    for name, desc in POSE_BLOCK.findall(raw_text.strip() + "\n"):
        blocks.append({"name": name.strip(), "description": desc.strip()})
    return blocks


def next_number(data: dict, category: str, prefix: str) -> int:
    """Highest existing <prefix><number>- title in the category, plus one. Starts at 1 if none exist."""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)-")
    max_n = 0
    for entry in data.get(category, []):
        m = pattern.match(entry.get("title", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def add_pose_prompts(raw_text: str, json_path: Path, category: str = "pose/action") -> list[str]:
    """Parse raw_text and append the resulting entries to json_path's category array.

    Title numbers are assigned automatically and sequentially, continuing
    from the category's current highest <prefix><number>-. Returns the
    list of titles added. Silently overwrites a single <stem>.bak.json
    backup beside json_path with the pre-write contents before touching
    the file.
    """
    raw_original = json_path.read_text(encoding="utf-8")
    data = json.loads(raw_original)
    if category not in data:
        raise KeyError(f"'{category}' not found in {json_path.name}")

    blocks = parse_pose_output(raw_text)
    if not blocks:
        raise ValueError("No '#NAME#' pose blocks found in the input text.")

    backup_path = json_path.parent / f"{json_path.stem}.bak{json_path.suffix}"
    backup_path.write_text(raw_original, encoding="utf-8")

    prefix = CATEGORY_PREFIX.get(category, "P")
    start = next_number(data, category, prefix)
    new_entries = []
    for i, block in enumerate(blocks):
        title = f"{prefix}{start + i:02d}-{block['name']}"
        new_entries.append({"title": title, "prompt": block["description"]})

    data[category].extend(new_entries)
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return [e["title"] for e in new_entries]


CATEGORY_MENU = {
    '1': ("pose/action", "pose"),
    '2': ("scene/setting", "scene"),
    '3': ("lighting", "lighting"),
    '4': ("outfit", "outfit"),
    '5': ("composition", "composition"),
}


def main():
    import djjtb.utils as djj
    while True:
        choice = djj.prompt_choice(
            "\033[93mCategory\033[0m\n"
            "1. Pose (default)\n"
            "2. Scene\n"
            "3. Lighting\n"
            "4. Outfit\n"
            "5. Composition\n"
            "> ",
            ['1', '2', '3', '4', '5'],
            default='1',
        )
        category, label = CATEGORY_MENU[choice]

        text_path = djj.pick_single_from_folder(TXT_FOLDER, ('.txt',), label=f"{label} text file")
        if not text_path:
            print("\033[93m❌ No text file found/selected.\033[0m")
        else:
            try:
                text = text_path.read_text(encoding="utf-8")
                added = add_pose_prompts(text, JSON_PATH, category=category)
                print(f"Added {len(added)} entr{'y' if len(added) == 1 else 'ies'}:")
                for title in added:
                    print(f"  - {title}")
            except Exception as e:
                print(f"\033[93m❌ {e}\033[0m")

        action = djj.what_next()
        if action == 'exit':
            break


if __name__ == "__main__":
    main()