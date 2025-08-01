import os
import subprocess
import sys
from pathlib import Path

from djjtb import utils as djj


def header():
    djj.print_header("PLIST ↔ JSON CONVERTER", icon="🧾")


def prompt_conversion_mode():
    return djj.prompt_choice(
        "Choose conversion mode:",
        ["1. Convert .plist → .json", "2. Convert .json → .plist"]
    )


def convert_plist_to_json(plist_path: Path, output_path: Path):
    try:
        subprocess.run([
            "plutil", "-convert", "json",
            "-o", str(output_path),
            str(plist_path)
        ], check=True)
        print(f"\033[92m✅ Converted to JSON:\033[0m {output_path}")
    except subprocess.CalledProcessError:
        print(f"\033[91m❌ Failed to convert:\033[0m {plist_path}")


def convert_json_to_plist(json_path: Path, output_path: Path):
    try:
        subprocess.run([
            "plutil", "-convert", "xml1",
            "-o", str(output_path),
            str(json_path)
        ], check=True)
        print(f"\033[92m✅ Converted to PLIST:\033[0m {output_path}")
    except subprocess.CalledProcessError:
        print(f"\033[91m❌ Failed to convert:\033[0m {json_path}")


def run_conversion(mode: str, input_paths: list[Path]):
    for file_path in input_paths:
        if mode == "1":  # .plist → .json
            if file_path.suffix != ".plist":
                print(f"\033[90mSkipping non-plist file:\033[0m {file_path.name}")
                continue
            output_file = file_path.with_suffix(".plist.json")
            convert_plist_to_json(file_path, output_file)

        elif mode == "2":  # .json → .plist
            if file_path.suffix != ".json":
                print(f"\033[90mSkipping non-json file:\033[0m {file_path.name}")
                continue
            output_file = file_path.with_name(file_path.name + ".plist")
            convert_json_to_plist(file_path, output_file)


def main():
    header()
    mode = prompt_conversion_mode()

    input_mode = djj.prompt_choice(
        "Choose input method:",
        ["1. Folder path", "2. Space-separated file paths"]
    )

    input_paths = djj.input_folder(Path) if input_mode == "1" else djj.input_paths(Path)
    input_files = djj.collect_files(input_paths, extensions=[".plist", ".json"], recursive=False)

    if not input_files:
        print("\033[91mNo matching files found. Exiting.\033[0m")
        return

    run_conversion(mode, input_files)
    djj.what_next(__file__)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\033[91m❌ Interrupted by user\033[0m")
        sys.exit(1)