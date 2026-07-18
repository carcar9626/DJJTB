import os
import shutil

base_dir = "/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/Output/Comp"

src_files = [
    os.path.join(base_dir, "X01-JUDK-SHINY-001_comp.jpg"),
    os.path.join(base_dir, "X01-JUDK-SHINY-007_comp.jpg"),
]

# loop W00 → W28
for i in range(0, 29):
    w = f"W{i:02d}"

    for src in src_files:
        name = os.path.basename(src)

        # extract the number part (001 or 007)
        num = name.split("-")[-1].replace("_comp.jpg", "")

        dst_name = f"{w}-JUDK-SHINY-{num}_compa.jpg"
        dst_path = os.path.join(base_dir, dst_name)

        shutil.copy2(src, dst_path)

print("Done.")