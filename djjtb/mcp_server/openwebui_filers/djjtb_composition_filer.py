"""
title: DJJTB Composition Filer
description: Files NBP composition descriptions into the prompt assembler's "composition" category.
"""

import requests


class Tools:
    def __init__(self):
        pass

    def file_composition_prompt(self, raw_text: str) -> str:
        """
        Parse NBP-formatted output and file it into the "composition" array of the prompt assembler.
        Use this for camera framing, lens, or angle descriptions only. Expects one or more blocks
        in the exact format: #<CAPITALIZED NAME># <description>. Only ever files into "composition".

        :param raw_text: The raw model output containing one or more composition blocks.
        :return: A message listing the titles that were added.
        """
        try:
            resp = requests.post(
                "http://192.168.50.67:8000/composition/file_composition_prompt",
                json={"raw_text": raw_text},
                timeout=30,
            )
            resp.raise_for_status()
            return str(resp.json())
        except requests.RequestException as e:
            return f"Filing failed: {e}"