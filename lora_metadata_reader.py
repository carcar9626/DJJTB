#!/usr/bin/env python3
"""
LoRA Metadata Reader
Extracts training parameters from safetensors LoRA files
"""

import json
import sys
from pathlib import Path

def read_lora_metadata(file_path):
    """Read metadata from safetensors file"""
    try:
        with open(file_path, 'rb') as f:
            # Read header length (first 8 bytes)
            header_size = int.from_bytes(f.read(8), byteorder='little')
            
            # Read header JSON
            header_bytes = f.read(header_size)
            header = json.loads(header_bytes.decode('utf-8'))
            
            # Extract metadata
            metadata = header.get('__metadata__', {})
            
            return metadata, header
            
    except Exception as e:
        return None, str(e)

def format_metadata(metadata):
    """Format metadata for display"""
    if not metadata:
        return "No metadata found in this file."
    
    output = []
    output.append("=" * 60)
    output.append("LoRA Training Parameters")
    output.append("=" * 60)
    
    # Common training parameters
    important_params = [
        'ss_network_module',
        'ss_network_dim',
        'ss_network_alpha',
        'ss_learning_rate',
        'ss_optimizer',
        'ss_max_train_steps',
        'ss_num_epochs',
        'ss_batch_size',
        'ss_resolution',
        'ss_base_model_version',
        'ss_training_started_at',
        'ss_training_finished_at',
        'ss_output_name',
        'ss_dataset_dirs',
        'ss_num_train_images',
        'ss_num_reg_images',
        'ss_lr_scheduler',
        'ss_mixed_precision',
        'ss_cache_latents',
    ]
    
    # Display important params first
    output.append("\n📊 Key Training Parameters:")
    output.append("-" * 60)
    for key in important_params:
        if key in metadata:
            value = metadata[key]
            # Clean up the key name
            clean_key = key.replace('ss_', '').replace('_', ' ').title()
            output.append(f"{clean_key:.<40} {value}")
    
    # Display remaining metadata
    other_params = {k: v for k, v in metadata.items() if k not in important_params}
    if other_params:
        output.append("\n📋 Additional Parameters:")
        output.append("-" * 60)
        for key, value in sorted(other_params.items()):
            clean_key = key.replace('ss_', '').replace('_', ' ').title()
            # Truncate long values
            if isinstance(value, str) and len(str(value)) > 80:
                value = str(value)[:77] + "..."
            output.append(f"{clean_key:.<40} {value}")
    
    output.append("=" * 60)
    return "\n".join(output)

def main():
    if len(sys.argv) < 2:
        print("Usage: python lora_metadata_reader.py <path_to_lora.safetensors>")
        print("\nExample:")
        print("  python lora_metadata_reader.py my_lora.safetensors")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    
    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    
    if not file_path.suffix == '.safetensors':
        print(f"⚠️  Warning: File doesn't have .safetensors extension")
    
    print(f"\n📂 Reading: {file_path.name}")
    print(f"📏 File size: {file_path.stat().st_size / (1024*1024):.2f} MB\n")
    
    metadata, header = read_lora_metadata(file_path)
    
    if metadata is None:
        print(f"❌ Error reading file: {header}")
        sys.exit(1)
    
    # Display formatted metadata
    print(format_metadata(metadata))
    
    # Optionally save to JSON
    if metadata:
        json_path = file_path.with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full metadata saved to: {json_path.name}")

if __name__ == "__main__":
    main()
