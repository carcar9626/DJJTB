import os

input_folder = "/Users/home/Documents/Lora_Training/Datasets/TA-2026-04-04-22-45-59-983898958562654699"
output_file = os.path.join(input_folder, "merged_with_filenames.txt")

txt_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".txt")])

with open(output_file, "w", encoding="utf-8") as outfile:
    for i, filename in enumerate(txt_files):
        file_path = os.path.join(input_folder, filename)
        name_without_ext = os.path.splitext(filename)[0]
        
        with open(file_path, "r", encoding="utf-8") as infile:
            content = infile.read().strip()
        
        outfile.write(f"{name_without_ext}\n{content}")
        
        if i < len(txt_files) - 1:
            outfile.write("\n\n")

print(f"Done: {output_file}")