"""
title: DJJTB Scene Filer
description: Files NBP scene/setting descriptions into the prompt assembler's "scene/setting" category.
"""

import requests


class Tools:
    def __init__(self):
        pass

    def file_scene_prompt(self, raw_text: str) -> str:
        """
        Parse NBP-formatted output and file it into the "scene/setting" array of the prompt assembler.
        Use this for environment / location descriptions only. Expects one or more blocks in the
        exact format: #<CAPITALIZED NAME># <description>. Only ever files into "scene/setting".

        :param raw_text: The raw model output containing one or more scene/setting blocks.
        :return: A message listing the titles that were added.
        """
        try:
            resp = requests.post(
                "http://192.168.50.67:8000/scene/file_scene_prompt",
                json={"raw_text": raw_text},
                timeout=30,
            )
            resp.raise_for_status()
            return str(resp.json())
        except requests.RequestException as e:
            return f"Filing failed: {e}"