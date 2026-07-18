import os
import shutil

base_dir = "/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO"

src_dir = os.path.join(base_dir, "X01")

# loop W00 → W28
for i in range(0, 29):
    w = f"W{i:02d}"
    dst_dir = os.path.join(base_dir, "colored", w)

    for j in range(1, 13):  # 001 → 012
        src_file = os.path.join(src_dir, f"X01-JUDK-SHINY-{j:03d}.png")
        dst_file = os.path.join(dst_dir, f"{w}-JUDK-SHINY-{j:03d}a.png")

        shutil.copy2(src_file, dst_file)

print("Done.")


# /Volumes/Movies_2SSD/UD_Gen香港经典s/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-001.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-002.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-003.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-004.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-005.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-006.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-007.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-008.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-009.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-010.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-011.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W00/W00-JUDK-SHINY-012.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-001.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-002.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-003.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-004.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-005.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-006.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-007.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-008.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-009.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-010.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-011.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/colored/W01/W01-JUDK-SHINY-012.png
#
# this same pattern of folders and prefix goes on from W00 to W28, same pattern, 12 files each
#
# i wanna make of copy of these :
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-001.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-002.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-003.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-004.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-005.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-006.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-007.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-008.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-009.png
# /Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JUDK-CN/2024-11-20-shiny/PRO/X01/X01-JUDK-SHINY-010.png