#!/usr/bin/env python3
"""
DJJTB - Vocabulary Extraction & Translation Engine
Category: ai_tools
Description: Upgraded 2026 Pipeline utilizing google-genai client structure
             to extract coordinates and map translations to JSON.
"""

import os
import json
import argparse
from pathlib import Path
from PIL import Image
from pydantic import BaseModel, Field
from google import genai

# --- SYSTEM ENV VERIFICATION ---
if "GEMINI_API_KEY" not in os.environ:
    raise ValueError("System Error: GEMINI_API_KEY environment variable not set.")

# Initialize the modern 2026 Google Gen AI Client
client = genai.Client()

# --- PYDANTIC SCHEMAS FOR DIRECT PARSING ---
class VocabItem(BaseModel):
    english_text: str = Field(description="The exact English word/phrase found under the icon.")
    chinese_translation: str = Field(description="The contextual, accurate Simplified Chinese translation.")
    text_bbox: list[int] = Field(description="Normalized bounding box [ymin, xmin, ymax, xmax] (0-1000) for English text.")
    icon_bbox: list[int] = Field(description="Normalized bounding box [ymin, xmin, ymax, xmax] (0-1000) for the related icon picture.")

class VocabMatrixSchema(BaseModel):
    main_title_english: str = Field(description="The primary category header of the image (e.g., 'WILD ANIMALS').")
    main_title_chinese: str = Field(description="The primary category header translated accurately into Simplified Chinese.")
    items: list[VocabItem] = Field(description="List of individual items parsed from the vocabulary grid matrix.")

# --- PROCESSING LOOP ---
def extract_matrix_data(image_path: Path) -> dict:
    if not image_path.exists():
        raise FileNotFoundError(f"Source file not found at: {image_path}")

    img = Image.open(image_path)
    
    prompt = """
    Analyze this English vocabulary grid infographic. Extract its structure completely so we can rebuild it on a custom canvas.
    1. Identify the overarching Category Title and translate it cleanly to Simplified Chinese.
    2. Go through every individual layout slot in the grid matrix.
    3. For each slot, extract the English text, provide a natural Simplified Chinese translation,
       and pinpoint normalized 0-1000 bounding boxes [ymin, xmin, ymax, xmax] for the text and the icon asset separately.
    """

    print(f"[AI ENGINE] Uploading and processing layout for: {image_path.name}...")
    
    # Utilizing gemini-2.5-flash for optimized spatial reasoning speed on the free tier
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[img, prompt],
        config={
            'response_mime_type': 'application/json',
            'response_schema': VocabMatrixSchema,
            'temperature': 0.1
        }
    )
    
    # Modern SDK allows direct model dump of parsed Pydantic objects natively
    return response.parsed.model_dump()

# --- EXECUTION ROUTE ---
def main():
    parser = argparse.ArgumentParser(description="DJJTB Vocab Matrix Processor")
    parser.add_argument("-i", "--input", required=True, help="Path to the ripped English source image")
    parser.add_argument("-o", "--output", help="Optional explicit path to save the generated JSON metadata file")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix('.json')

    try:
        data_payload = extract_matrix_data(input_path)
        
        # Chain metadata tracking directly for downstream DJJTB canvas tools
        data_payload["meta"] = {
            "source_image_path": str(input_path.resolve()),
            "original_width": Image.open(input_path).width,
            "original_height": Image.open(input_path).height
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_payload, f, ensure_ascii=False, indent=4)
            
        print(f"[SUCCESS] Spatial matrix layout data captured: {output_path.name}")

    except Exception as e:
        print(f"[CRITICAL ERROR] Execution failed: {str(e)}")

if __name__ == "__main__":
    main()