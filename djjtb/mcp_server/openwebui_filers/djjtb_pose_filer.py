"""
title: DJJTB Pose Filer
description: Files NBP pose descriptions into the prompt assembler's "pose/action" category.
"""

import requests


class Tools:
    def __init__(self):
        pass

    def file_pose_prompt(self, raw_text: str) -> str:
        """
        Parse NBP-formatted output and file it into the "pose/action" array of the prompt assembler.
        Use this for body pose or action descriptions only. Expects one or more blocks in the
        exact format: #<CAPITALIZED NAME># <description>. Only ever files into "pose/action".

        :param raw_text: The raw model output containing one or more pose/action blocks.
        :return: A message listing the titles that were added.
        """
        try:
            resp = requests.post(
                "http://192.168.50.67:8000/pose/file_pose_prompt",
                json={"raw_text": raw_text},
                timeout=30,
            )
            resp.raise_for_status()
            return str(resp.json())
        except requests.RequestException as e:
            return f"Filing failed: {e}"
