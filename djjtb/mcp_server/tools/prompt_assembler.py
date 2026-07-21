"""
prompt_assembler.py

Parses NBP-formatted pose output (the "POSE No. X / #NAME# / description"
format your Gemma4 pose-analysis instructions produce) and appends each
pose as a {"title": "PXX-NAME", "prompt": "..."} entry to the
"pose/action" array in prompt_assembler.json.

This module is imported by server.py as an MCP tool. It's also still
runnable standalone for quick testing without the server.

Usage (standalone):
    python3 prompt_assembler.py path/to/pasted_output.txt
"""

import json
import re
import sys
from pathlib import Path

JSON_PATH = Path("/Users/home/Documents/Scripts/FLOW_TOOLS/prompt_assembler/LOCAL/prompt_assembler.json")

POSE_BLOCK = re.compile(
    r"POSE No\.\s*(\d+)\s*\n#(.+?)#\s*\n(.+?)(?=\nPOSE No\.|\Z)",
    re.DOTALL,
)


def parse_pose_output(raw_text: str) -> list[dict]:
    """Turn raw NBP pose output into a list of {"title", "prompt"} entries."""
    entries = []
    for num, name, desc in POSE_BLOCK.findall(raw_text.strip() + "\n"):
        title = f"P{int(num):02d}-{name.strip()}"
        entries.append({"title": title, "prompt": desc.strip()})
    return entries


def add_pose_prompts(
    raw_text: str,
    json_path: Path = JSON_PATH,
    category: str = "pose/action",
) -> list[str]:
    """Parse raw_text and append the resulting entries to json_path's category array.

    Returns the list of titles added.
    """
    raw_original = json_path.read_text(encoding="utf-8")
    data = json.loads(raw_original)
    if category not in data:
        raise KeyError(f"'{category}' not found in {json_path.name}")

    new_entries = parse_pose_output(raw_text)
    if not new_entries:
        raise ValueError("No 'POSE No. X / #NAME#' blocks found in the input text.")

    # one-step backup before touching the live file
    json_path.with_suffix(json_path.suffix + ".bak").write_text(raw_original, encoding="utf-8")

    data[category].extend(new_entries)
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return [e["title"] for e in new_entries]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 prompt_assembler.py <path_to_raw_output.txt>")
        sys.exit(1)

    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    added = add_pose_prompts(text)
    print(f"Added {len(added)} pose(s):")
    for title in added:
        print(f"  - {title}")
