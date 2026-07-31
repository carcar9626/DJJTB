"""
title: DJJTB Lighting Filer
description: Files NBP lighting descriptions into the prompt assembler's "lighting" category.
"""

import requests


class Tools:
    def __init__(self):
        pass

    def file_lighting_prompt(self, raw_text: str) -> str:
        """
        Parse NBP-formatted output and file it into the "lighting" array of the prompt assembler.
        Use this for lighting mood, direction, or time-of-day descriptions only. Expects one or
        more blocks in the exact format: #<CAPITALIZED NAME># <description>. Only ever files
        into "lighting".

        :param raw_text: The raw model output containing one or more lighting blocks.
        :return: A message listing the titles that were added.
        """
        try:
            resp = requests.post(
                "http://192.168.50.67:8000/lighting/file_lighting_prompt",
                json={"raw_text": raw_text},
                timeout=30,
            )
            resp.raise_for_status()
            return str(resp.json())
        except requests.RequestException as e:
            return f"Filing failed: {e}"
