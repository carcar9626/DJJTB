import os
import shutil

files = [
"/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/JENK_qud_2024-10-11_1-2.heic-b01a.png",
"/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/JENK_qud_2024-10-11_2-2.heic-b01a.png",
"/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/JENK_qud_2024-10-11_2-2.heica01p04_FFa.png",
"/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/JENK_qud_2024-10-11_2-2.heica01p05_FFa.png",
"/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/JENK_qud_2024-10-11_2-2.heica01p08_FFa.png",
"/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/JENK_qud_2024-10-11_2-2.heica01p11_FFa.png",
"/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/JENK_qud_2024-10-11_2-2.heica01p14_FFa.png",
"/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/JENK_qud_2024-10-11_2-2.heica01p15_FFa.png"
]

output_dir = "/Volumes/Movies_2SSD/UD_Gens/Characters/Qwen_CN/JENK-CN/car/car_Cloths/OG/Output"
os.makedirs(output_dir, exist_ok=True)

for i in range(1, 17):  # 01 to 16
    prefix = f"{i:02d}-"
    for f in files:
        name = os.path.basename(f)
        new_name = prefix + name
        dst = os.path.join(output_dir, new_name)
        shutil.copy2(f, dst)

print("Done.")