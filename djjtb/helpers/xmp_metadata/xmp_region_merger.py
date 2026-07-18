#!/usr/bin/env python3
"""
XMP Region Data Merger
Merges face/region data from original XMP files into tagged XMP files
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil
import stat

# Universal file permissions monkey patch
def make_writable(filepath):
    """Make any file writable"""
    os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

# Patch ET.ElementTree.write for XML files
original_et_write = ET.ElementTree.write
def patched_et_write(self, file_or_filename, *args, **kwargs):
    result = original_et_write(self, file_or_filename, *args, **kwargs)
    if isinstance(file_or_filename, (str, Path)):
        make_writable(file_or_filename)
    return result
ET.ElementTree.write = patched_et_write

# Patch shutil operations
original_copy2 = shutil.copy2
def patched_copy2(src, dst, *args, **kwargs):
    result = original_copy2(src, dst, *args, **kwargs)
    make_writable(dst)
    return result
shutil.copy2 = patched_copy2

original_move = shutil.move
def patched_move(src, dst, *args, **kwargs):
    result = original_move(src, dst, *args, **kwargs)
    make_writable(result)
    return result
shutil.move = patched_move

# Patch built-in open() for direct file writes
original_open = open
def patched_open(file, mode='r', *args, **kwargs):
    f = original_open(file, mode, *args, **kwargs)
    # If writing, make writable when closed
    if 'w' in mode or 'a' in mode:
        original_close = f.close
        def patched_close():
            result = original_close()
            make_writable(file)
            return result
        f.close = patched_close
    return f
__builtins__['open'] = patched_open

def parse_xmp_file(file_path):
    """Parse XMP file and return the root element"""
    try:
        tree = ET.parse(file_path)
        return tree, tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing {file_path}: {e}")
        return None, None

def find_regions_data(root):
    """Extract all region-related data from XMP"""
    regions_data = {}
    
    # Define namespaces
    namespaces = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'MP': 'http://ns.microsoft.com/photo/1.2/',
        'MPRI': 'http://ns.microsoft.com/photo/1.2/t/RegionInfo#',
        'MPReg': 'http://ns.microsoft.com/photo/1.2/t/Region#',
        'mwg-rs': 'http://www.metadataworkinggroup.com/schemas/regions/',
        'stDim': 'http://ns.adobe.com/xap/1.0/sType/Dimensions#',
        'stArea': 'http://ns.adobe.com/xmp/sType/Area#'
    }
    
    # Register namespaces
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)
    
    # Find RDF Description element
    description = root.find('.//rdf:Description', namespaces)
    if description is None:
        return None
    
    # Extract MP:RegionInfo
    mp_region_info = description.find('.//MP:RegionInfo', namespaces)
    if mp_region_info is not None:
        regions_data['MP:RegionInfo'] = mp_region_info
    
    # Extract mwg-rs:Regions
    mwg_regions = description.find('.//mwg-rs:Regions', namespaces)
    if mwg_regions is not None:
        regions_data['mwg-rs:Regions'] = mwg_regions
    
    return regions_data if regions_data else None

def remove_existing_regions(root):
    """Remove existing region data from the target XMP"""
    namespaces = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'MP': 'http://ns.microsoft.com/photo/1.2/',
        'mwg-rs': 'http://www.metadataworkinggroup.com/schemas/regions/'
    }
    
    description = root.find('.//rdf:Description', namespaces)
    if description is None:
        return
    
    # Remove existing MP:RegionInfo
    mp_region_info = description.find('.//MP:RegionInfo', namespaces)
    if mp_region_info is not None:
        description.remove(mp_region_info)
    
    # Remove existing mwg-rs:Regions
    mwg_regions = description.find('.//mwg-rs:Regions', namespaces)
    if mwg_regions is not None:
        description.remove(mwg_regions)

def add_regions_data(target_root, regions_data):
    """Add region data to target XMP"""
    namespaces = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    }
    
    description = target_root.find('.//rdf:Description', namespaces)
    if description is None:
        print("Warning: No Description element found in target")
        return False
    
    # Add region data
    for region_type, region_element in regions_data.items():
        description.append(region_element)
    
    return True

def merge_xmp_regions(face_xmp_path, tagged_xmp_path, output_path):
    """Merge region data from face XMP into tagged XMP"""
    
    # Parse both files
    face_tree, face_root = parse_xmp_file(face_xmp_path)
    if face_tree is None:
        return False
    
    tagged_tree, tagged_root = parse_xmp_file(tagged_xmp_path)
    if tagged_tree is None:
        return False
    
    # Extract region data from face XMP
    regions_data = find_regions_data(face_root)
    if regions_data is None:
        print(f"No region data found in {face_xmp_path}")
        # Just copy the tagged file if no regions to merge
        shutil.copy2(tagged_xmp_path, output_path)
        return True
    
    # Remove existing region data from tagged XMP
    remove_existing_regions(tagged_root)
    
    # Add region data from face XMP
    success = add_regions_data(tagged_root, regions_data)
    
    if success:
        # Write merged result
        tagged_tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"Successfully merged: {output_path}")
        return True
    else:
        print(f"Failed to merge: {output_path}")
        return False

def batch_merge_regions(face_dir, tagged_dir, output_dir):
    """Batch merge region data for all XMP files, preserving folder structure"""
    
    face_path = Path(face_dir)
    tagged_path = Path(tagged_dir)
    output_path = Path(output_dir)
    
    # Debug: Check if paths exist and are readable
    print(f"Checking paths:")
    print(f"  Face path exists: {face_path.exists()}")
    print(f"  Face path is dir: {face_path.is_dir()}")
    print(f"  Tagged path exists: {tagged_path.exists()}")
    print(f"  Tagged path is dir: {tagged_path.is_dir()}")
    print()
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all XMP files recursively in face directory (including .jpg.xmp, .cr2.xmp, etc.)
    print("Scanning for XMP files...")
    xmp_files = list(face_path.rglob("*.xmp"))
    
    # Debug: Show first few files found
    print(f"First 3 files found: {[str(f) for f in xmp_files[:3]]}")
    
    success_count = 0
    total_count = len(xmp_files)
    
    print(f"Found {total_count} XMP files to process across all subdirectories")
    
    if total_count == 0:
        print("No files found! Checking directory contents...")
        try:
            all_files = list(face_path.rglob("*"))
            print(f"Total files/dirs in face directory: {len(all_files)}")
            file_extensions = set()
            for f in all_files[:50]:  # Check first 50 files
                if f.is_file():
                    file_extensions.add(f.suffix.lower())
            print(f"File extensions found: {sorted(file_extensions)}")
        except Exception as e:
            print(f"Error checking directory: {e}")
        return
    
    for i, face_xmp in enumerate(xmp_files, 1):
        # Calculate relative path from face_dir
        relative_path = face_xmp.relative_to(face_path)
        
        # Find corresponding tagged file
        tagged_xmp = tagged_path / relative_path
        
        # Create output path maintaining folder structure
        output_xmp = output_path / relative_path
        
        # Create output subdirectory if it doesn't exist
        output_xmp.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Processing {i}/{total_count}: {relative_path}")
        
        if not tagged_xmp.exists():
            print(f"  Warning: Tagged version not found for {relative_path}")
            continue
        
        if merge_xmp_regions(face_xmp, tagged_xmp, output_xmp):
            success_count += 1
        
        # Progress indicator
        if i % 100 == 0:
            print(f"  Progress: {i}/{total_count} ({success_count} successful)")
    
    print(f"\nCompleted: {success_count}/{total_count} files merged successfully")

if __name__ == "__main__":
    print(f"Script started with {len(sys.argv)} arguments")
    print(f"Arguments: {sys.argv}")
    
    if len(sys.argv) != 4:
        print("Usage: python xmp_region_merger.py <face_xmp_dir> <tagged_xmp_dir> <output_dir>")
        print("  face_xmp_dir: Directory with original XMP files containing face/region data")
        print("  tagged_xmp_dir: Directory with XMP files containing generated tags")
        print("  output_dir: Directory where merged XMP files will be saved")
        sys.exit(1)
    
    face_dir = sys.argv[1]
    tagged_dir = sys.argv[2]
    output_dir = sys.argv[3]
    
    print(f"Processing arguments:")
    print(f"  face_dir: {face_dir}")
    print(f"  tagged_dir: {tagged_dir}")
    print(f"  output_dir: {output_dir}")
    
    # Validate directories
    if not os.path.isdir(face_dir):
        print(f"Error: Face XMP directory does not exist: {face_dir}")
        sys.exit(1)
    
    if not os.path.isdir(tagged_dir):
        print(f"Error: Tagged XMP directory does not exist: {tagged_dir}")
        sys.exit(1)
    
    print(f"Face XMP directory: {face_dir}")
    print(f"Tagged XMP directory: {tagged_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    print("Calling batch_merge_regions...")
    batch_merge_regions(face_dir, tagged_dir, output_dir)