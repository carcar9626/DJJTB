"""
title: DJJTB Pose Filer
description: Files NBP pose descriptions into the prompt assembler's "pose/action" category.
"""

import requests


class Tools:
    def __init__(self):
        pass

    def file_pose_prompt(self, raw_text: str, image_filename: str = "") -> str:
        """
        Parse NBP-formatted output and file it into the "pose/action" array of the prompt assembler.
        Use this for body pose or action descriptions only. Expects one or more blocks in the
        exact format: #<CAPITALIZED NAME># <description>. Only ever files into "pose/action".

        The reference image is linked automatically if it's already saved
        in pose_images/ named by the pose's assigned number -- no action
        needed for the normal case.

        :param raw_text: The raw model output containing one or more pose/action blocks.
        :param image_filename: Optional. Only set if the user explicitly stated a filename for this pose's reference image in their message. Never guess -- leave empty otherwise.
        :return: A message listing the titles that were added.
        """
        try:
            resp = requests.post(
                "http://192.168.50.67:8000/pose/file_pose_prompt",
                json={"raw_text": raw_text, "image_filename": image_filename},
                timeout=30,
            )
            resp.raise_for_status()
            return str(resp.json())
        except requests.RequestException as e:
            return f"Filing failed: {e}"
