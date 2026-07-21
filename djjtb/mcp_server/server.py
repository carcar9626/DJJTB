"""
DJJTB MCP server.

Exposes DJJTB automation scripts as tools that any MCP-compatible client
can call — Claude Desktop/Code over stdio, Open WebUI over Streamable HTTP.
Add more tools the same way as add_pose_prompts_tool: import the function
from tools/, wrap it with @mcp.tool().

Run:
    python3 server.py            # stdio transport (Claude Desktop/Code)
    python3 server.py --http     # Streamable HTTP on :8420 (Open WebUI)
"""

import sys
from mcp.server.fastmcp import FastMCP
from tools.prompt_assembler import add_pose_prompts

mcp = FastMCP("djjtb_mcp")


@mcp.tool()
def add_pose_prompts_tool(raw_text: str) -> list[str]:
    """Parse NBP-formatted pose-analysis output and file it into the prompt assembler.

    Expects one or more blocks in the exact format:
        POSE No. <number>
        #<CAPITALIZED NAME>#
        <anatomical description>

    Appends each as {"title": "P<number>-<name>", "prompt": "<description>"}
    to the "pose/action" category of prompt_assembler.json. A backup of the
    file is written before any change.

    Args:
        raw_text: The raw model output containing one or more pose blocks.

    Returns:
        List of titles that were added, e.g. ["P55-COUCH-BACK RECLINE CROSS-ANKLE"].
    """
    return add_pose_prompts(raw_text)


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="streamable_http", port=8420)
    else:
        mcp.run()
