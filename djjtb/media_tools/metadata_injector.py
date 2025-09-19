import os
from PIL import Image, PngImagePlugin

# Change these to suit your fake prompt
FAKE_METADATA = {
    "parameters": (
        "prompt: a hyper-detailed futuristic city at sunset, ultra HD, trending on artstation\n"
        "negative_prompt: blurry, low quality, bad anatomy\n"
        "Steps: 30, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 12345678, Size: 768x768,\n"
        "Model hash: 5c1fd5e0, Model: deliberate_v2"
    )
}

def inject_metadata(image_path, output_path):
    img = Image.open(image_path)
    pnginfo = PngImagePlugin.PngInfo()
    for key, val in FAKE_METADATA.items():
        pnginfo.add_text(key, val)
    img.save(output_path, pnginfo=pnginfo)

def process_folder(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(".png"):
                input_path = os.path.join(root, file)
                rel_path = os.path.relpath(input_path, input_folder)
                output_path = os.path.join(output_folder, rel_path)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                try:
                    inject_metadata(input_path, output_path)
                    print(f"✅ Injected: {rel_path}")
                except Exception as e:
                    print(f"❌ Failed: {rel_path} → {e}")

# === Edit below ===
input_folder = "/Volumes/Desmond_SSD_2TB/UD_Gens/Characters/metadata_test/Output/CF/final_results"
output_folder = "/Volumes/Desmond_SSD_2TB/UD_Gens/Characters/metadata_test/Output/CF/final_results"
process_folder(input_folder, output_folder)