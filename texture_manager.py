# -------------------------------------------------------------------
# Ghost of Tsushima Blender Tool
# Copyright (c) 2025 Dave349234
#
# This code is licensed under the MIT License with attribution requirements.
# See the LICENSE file in the root directory or the main __init__.py
# for full details.
#
# Profile: https://www.nexusmods.com/profile/Dave349234
# Support: https://ko-fi.com/dave349234
# -------------------------------------------------------------------

import os
import shutil
from . import tex_db

def find_texture_in_root(root_path, tex_name):   
    candidates = [
        tex_name,
        tex_name + ".sps", 
    ]
    
    try:
        subdirs = [d for d in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, d)) and "gapack" in d]
    except OSError:
        return None, None

    first_char = tex_name[0].lower() if tex_name else ""
    priority_dirs = [d for d in subdirs if f"_{first_char}" in d]
    other_dirs = [d for d in subdirs if d not in priority_dirs]
    
    all_dirs_sorted = priority_dirs + other_dirs
    
    for gapack_folder in all_dirs_sorted:
        bitmaps_path = os.path.join(root_path, gapack_folder, "bitmaps")
        
        if not os.path.exists(bitmaps_path):
            continue
            
        for cand in candidates:
            full_path = os.path.join(bitmaps_path, cand)
            if os.path.exists(full_path):
                return full_path, gapack_folder
                
    return None, None

def collect_textures_for_mod(xpps_path, db_path, replacements, texture_root_path, output_mod_dir):
    if not texture_root_path or not os.path.exists(texture_root_path):
        print("[TextureManager] Texture root path invalid or empty. Skipping.")
        return 0

    total_copied = 0
    print(f"[TextureManager] Scanning folders in: {texture_root_path}")

    for item in replacements:
        target_hash_str = item.original_hash
        try:
            target_hash = int(target_hash_str, 16)
        except:
            continue
            
        tex_names = tex_db.find_materials(xpps_path, target_hash, db_path)
        
        if not tex_names or (len(tex_names) == 1 and "Error" in tex_names[0]):
            continue

        for tex_name in tex_names:
            found_file, src_folder_name = find_texture_in_root(texture_root_path, tex_name)
            
            if found_file:
                dest_folder_name = f"{src_folder_name}_{target_hash_str}"
                dest_folder_path = os.path.join(output_mod_dir, dest_folder_name)
                os.makedirs(dest_folder_path, exist_ok=True)
                
                fname = os.path.basename(found_file)
                dest_file_path = os.path.join(dest_folder_path, fname)
                
                if not os.path.exists(dest_file_path):
                    try:
                        shutil.copy2(found_file, dest_file_path)
                        print(f"  [+] Found in {src_folder_name}: {fname}")
                        total_copied += 1
                    except Exception as e:
                        print(f"  [!] Failed to copy {fname}: {e}")
            else:
                print(f"  [-] Texture not found in ANY folder: {tex_name}")

    return total_copied