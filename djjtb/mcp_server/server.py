"""
DJJTB MCP server.

Exposes DJJTB automation scripts as tools any MCP-compatible client can
call — Claude Desktop/Code over stdio, Open WebUI over Streamable HTTP
(via mcpo). Imports directly from the real djjtb package rather than
keeping its own copy — one source of truth, no drift between them.

Each of the five file_*_prompt tools can be run as its own isolated
process via --category, so mcpo can expose each one on its own path
(see mcpo_config.json) and Open WebUI can scope tool access per model
instead of getting all five bundled behind one connection. Omit
--category to register all five on one process, for direct stdio use
(e.g. Claude Desktop) where that scoping doesn't matter.

IMPORTANT: run this from the DJJTB repo root (not from inside
mcp_server/), so the djjtb package resolves correctly:

    python3 -m djjtb.mcp_server.server                    # stdio, all 5 tools
    python3 -m djjtb.mcp_server.server --category pose    # stdio, pose tool only
    python3 -m djjtb.mcp_server.server --http              # Streamable HTTP on :8420, all 5 tools
"""

import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from djjtb.file_tools.add_pose_prompts import add_pose_prompts

JSON_PATH = Path("/Users/home/Documents/Scripts/FLOW_TOOLS/prompt_assembler/LOCAL/prompt_assembler.json")


def _parse_category_arg():
    """Return the --category value from sys.argv, or None if not given."""
    if "--category" not in sys.argv:
        return None
    idx = sys.argv.index("--category")
    try:
        return sys.argv[idx + 1]
    except IndexError:
        sys.exit("--category requires a value: pose, scene, lighting, outfit, composition")


# Parsed once, up front, so it can name the FastMCP instance below *and*
# drive tool registration in _register_tools() further down — each
# --category subprocess reports itself as "djjtb_mcp_<category>" instead
# of every one of the five identically as "djjtb_mcp", since mcpo/Open
# WebUI display this name (not the admin-panel connection nickname) in
# the model tool list and chat tool picker.
_category = _parse_category_arg()

mcp = FastMCP(f"djjtb_mcp_{_category}" if _category else "djjtb_mcp")


# Each tool below is locked to exactly one prompt_assembler.json category —
# the category is a hardcoded literal in the add_pose_prompts() call, never
# a parameter, so no model can steer a call into a category other than the
# one its tool name promises. None of them carry the @mcp.tool() decorator
# directly; which ones actually get registered on `mcp` is decided by
# _register_tools() below, based on --category.


def file_pose_prompt(raw_text: str) -> list[str]:
    """Parse NBP-formatted output and file it into the "pose/action" array of the prompt assembler.

    Use this for body pose or action descriptions only.

    Expects one or more blocks in the exact format:
        #<CAPITALIZED NAME>#
        <description>

    Only ever files into "pose/action". Numbers new entries automatically
    from "pose/action"'s highest existing "P<number>-" title. Writes a
    backup before any change.

    Args:
        raw_text: The raw model output containing one or more pose/action blocks.

    Returns:
        List of titles that were added, e.g. ["P65-RECLINED ASYMMETRIC LEGS EXTENDED"].
    """
    return add_pose_prompts(raw_text, JSON_PATH, category="pose/action")


def file_scene_prompt(raw_text: str) -> list[str]:
    """Parse NBP-formatted output and file it into the "scene/setting" array of the prompt assembler.

    Use this for environment / location descriptions only.

    Expects one or more blocks in the exact format:
        #<CAPITALIZED NAME>#
        <description>

    Only ever files into "scene/setting". Numbers new entries automatically
    from "scene/setting"'s highest existing "S<number>-" title. Writes a
    backup before any change.

    Args:
        raw_text: The raw model output containing one or more scene/setting blocks.

    Returns:
        List of titles that were added, e.g. ["S03-GOLDEN HOUR ROOFTOP"].
    """
    return add_pose_prompts(raw_text, JSON_PATH, category="scene/setting")


def file_lighting_prompt(raw_text: str) -> list[str]:
    """Parse NBP-formatted output and file it into the "lighting" array of the prompt assembler.

    Use this for lighting mood, direction, or time-of-day descriptions only.

    Expects one or more blocks in the exact format:
        #<CAPITALIZED NAME>#
        <description>

    Only ever files into "lighting". Numbers new entries automatically
    from "lighting"'s highest existing "L<number>-" title. Writes a
    backup before any change.

    Args:
        raw_text: The raw model output containing one or more lighting blocks.

    Returns:
        List of titles that were added, e.g. ["L03-STUDIO VOLUMETRIC WRAP"].
    """
    return add_pose_prompts(raw_text, JSON_PATH, category="lighting")


def file_outfit_prompt(raw_text: str) -> list[str]:
    """Parse NBP-formatted output and file it into the "outfit" array of the prompt assembler.

    Use this for clothing / wardrobe descriptions only.

    Expects one or more blocks in the exact format:
        #<CAPITALIZED NAME>#
        <description>

    Only ever files into "outfit". Numbers new entries automatically
    from "outfit"'s highest existing "O<number>-" title. Writes a
    backup before any change.

    Args:
        raw_text: The raw model output containing one or more outfit blocks.

    Returns:
        List of titles that were added, e.g. ["O03-MINIMALIST CASUAL SET"].
    """
    return add_pose_prompts(raw_text, JSON_PATH, category="outfit")


def file_composition_prompt(raw_text: str) -> list[str]:
    """Parse NBP-formatted output and file it into the "composition" array of the prompt assembler.

    Use this for camera framing, lens, or angle descriptions only.

    Expects one or more blocks in the exact format:
        #<CAPITALIZED NAME>#
        <description>

    Only ever files into "composition". Numbers new entries automatically
    from "composition"'s highest existing "C<number>-" title. Writes a
    backup before any change.

    Args:
        raw_text: The raw model output containing one or more composition blocks.

    Returns:
        List of titles that were added, e.g. ["C03-WIDE CINEMATIC ANGLE"].
    """
    return add_pose_prompts(raw_text, JSON_PATH, category="composition")


CATEGORY_TOOLS = {
    "pose": file_pose_prompt,
    "scene": file_scene_prompt,
    "lighting": file_lighting_prompt,
    "outfit": file_outfit_prompt,
    "composition": file_composition_prompt,
}


def _register_tools(category):
    """Register category's single tool, or all five if category is None."""
    if category is None:
        for fn in CATEGORY_TOOLS.values():
            mcp.add_tool(fn)
        return
    if category not in CATEGORY_TOOLS:
        sys.exit(f"Unknown category '{category}'. Must be one of: {', '.join(CATEGORY_TOOLS)}")
    mcp.add_tool(CATEGORY_TOOLS[category])


_register_tools(_category)


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="streamable_http", port=8420)
    else:
        mcp.run()
