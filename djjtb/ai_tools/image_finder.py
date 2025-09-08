import os
import pathlib
import shutil
import subprocess
from datetime import datetime
import djjtb.utils as djj

SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".webp")
os.system('clear')

def safe_filename(name):
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name.strip().lower())

def get_all_images(input_path, include_sub):
    path_obj = pathlib.Path(input_path)
    if include_sub:
        return sorted([p for p in path_obj.rglob("*") if p.suffix.lower() in SUPPORTED_EXTS])
    return sorted([p for p in path_obj.glob("*") if p.suffix.lower() in SUPPORTED_EXTS])

def open_folder_mac(folder_path):
    subprocess.run(["open", str(folder_path)], check=False)

def main():
    while True:  # Outer loop for restarting with new path
        print("\n\n\033[92m==================================================\033[0m")
        print("\033[1;33mImage Finder\033[0m")
        print("Search Images with Terms")
        print("\033[92m==================================================\033[0m\n")

        input_path = input("\033[93m📁 Enter folder path:\n -> \033[0m").strip()
        input_path_obj = pathlib.Path(input_path).resolve()
        print()
        if not input_path_obj.exists():
            print(f"\033[93m❌ Error: \033[0m'{input_path}' \033[93mnot found.\033[0m\n")
            continue

        # Subfolder include prompt
        include_sub = djj.prompt_choice(
            "\033[93mInclude subfolders?\033[0m\n1. Yes, 2. No",
            ['1', '2'],
            default='2'
        ) == '1'
        print()

        while True:  # Inner loop for searching with same path
            print()
            search_term = input("\033[93m🔍 Enter search term:\n -> \033[0m").strip()
            if not search_term:
                print("\033[93m❌ No search term entered.\033[0m\n")
                continue

            all_images = get_all_images(input_path_obj, include_sub)
            total = len(all_images)
            if total == 0:
                print("\033[93m❌ No images found.\033[0m")
                break

            print(f"\n\033[93m🔎 Searching\033[0m {total} images for: '{search_term}' ...\n")

            # Dummy matching logic placeholder (replace with real OpenCLIP logic)
            results = []
            for i, img_path in enumerate(all_images, 1):
                score = 1.0  # Replace with real similarity score
                results.append((img_path, score))
                print(f"\r\033[93mProcessing images \033[0m{i}/{total} ({int(i/total*100)}%)...", end="", flush=True)
            print("\n✅ Matching complete.\n")

            results.sort(key=lambda x: x[1], reverse=True)
            top_results = [r[0] for r in results[:20]]

            if not top_results:
                print("⚠️ No results matched.")
                break

            # Subfolder results output prompt
            do_output = djj.prompt_choice(
                "\033[93mSubfolder results?\033[0m\n1. Yes, 2. No",
                ['1', '2'],
                default='2'
            ) == '1'
            print()
            if do_output:
                action = djj.prompt_choice(
                    "\033[93mCopy or Move?\033[0m\n1. Copy, 2. Move",
                    ['1', '2'],
                    default='1'
                )
                print()
                safe_term = safe_filename(search_term)

                base_output_dir = input_path_obj / "Output" / "image_finder_results"
                output_dir = base_output_dir / safe_term

                if output_dir.exists():
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    output_dir = base_output_dir / f"{safe_term}_{timestamp}"

                output_dir.mkdir(parents=True, exist_ok=True)

                for src in top_results:
                    dest = output_dir / src.name
                    try:
                        if action == '1':
                            shutil.copy2(src, dest)
                        else:
                            shutil.move(src, dest)
                    except Exception as e:
                        print(f"\033[93m⚠️ Failed to process\033[0m {src.name}: {e}")

                open_folder_mac(output_dir)

            # Local what_next handling
            again = djj.prompt_choice(
                "\033[93mWhat Next?\033[0m\n1. Again\n2. Again with New Path\n3. Return to DJJTB\n4. Exit\n> ",
                ['1', '2', '3', '4'],
                default='3'
            )

            if again == '4':
                print("👋 Exiting.")
                return
            elif again == '3':
                djj.return_to_djjtb()
                return
            elif again == '2':
                os.system('clear')
                break
            else:  # again == '1'
                os.system('clear')

if __name__ == "__main__":
    main()