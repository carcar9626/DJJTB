import os
import sys
import djjtb.utils as djj

os.system('clear')

def main():
    while True:
        print()
        print("\033[92m==================================================\033[0m")
        print("\033[1;33mFolder Prefix Tool\033[0m")
        print("Add folder name prefix to all files")
        print("\033[92m==================================================\033[0m")
        print()

        # Get input path
        root = djj.get_path_input("Enter folder path")
        print()

        # Get folder name as prefix
        prefix = os.path.basename(root) + "-"
        
        print(f"\033[33mPrefix to add:\033[0m {prefix}")
        print()
        print("-------------")

        # Process files
        files_processed = 0
        files_skipped = 0

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if filename.startswith(prefix):
                    files_skipped += 1
                    continue  # Skip already-prefixed files

                old_path = os.path.join(dirpath, filename)
                new_filename = prefix + filename
                new_path = os.path.join(dirpath, new_filename)

                try:
                    os.rename(old_path, new_path)
                    files_processed += 1
                except Exception as e:
                    print(f"\033[33mError renaming {filename}: {e}\033[0m")

        # Summary
        print()
        print("\033[33mPrefix Summary\033[0m")
        print("---------------")
        print(f"\033[33mFiles processed:\033[0m {files_processed}")
        print(f"\033[33mFiles skipped:\033[0m {files_skipped}")
        print(f"\033[33mPrefix used:\033[0m {prefix}")
        print("\n" * 3)
        djj.prompt_open_folder(root)
        action = djj.what_next()
        if action == 'exit':
            break

if __name__ == '__main__':
    main()