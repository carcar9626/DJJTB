from pathlib import Path

# ===== SETTINGS (edit these) =====
folder_path = "/Volumes/Movies_2SSD/UD_Gens/Characters/UD/JENK-UD/"
num_chars = 5
base_url = ""
output_file = "urls.txt"
# =================================

folder = Path(folder_path)
output_path = folder / output_file

urls = []

for file in folder.iterdir():
    if file.is_file():
        name_part = file.stem[:num_chars]  # first N characters of filename (no extension)
        url = base_url + name_part
        urls.append(url)

# sort optional (keeps it clean)
urls.sort()

with open(output_path, "w") as f:
    f.write("\n".join(urls))

print(f"Saved {len(urls)} URLs to {output_path}")