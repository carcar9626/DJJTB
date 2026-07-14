import os

input_folder = "/Users/home/Documents/Lora_Training/Datasets/JUDK/TA-2026-04-04-21-45-55-983893473889393171"
output_file = os.path.join(input_folder, "merged_captions.txt")

txt_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".txt")])

with open(output_file, "w", encoding="utf-8") as outfile:
    for i, filename in enumerate(txt_files):
        file_path = os.path.join(input_folder, filename)
        
        with open(file_path, "r", encoding="utf-8") as infile:
            content = infile.read().strip()
            outfile.write(content)
        
        if i < len(txt_files) - 1:
            outfile.write("\n\n")  # blank line between captions

print(f"Done: {output_file}")