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
import struct
import random

class ModState:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.modifications = {}

def read_xpps_state(xpps_path):
    state = {}
    if not os.path.exists(xpps_path): return state
    
    with open(xpps_path, 'rb') as f:
        f.seek(24); pkg_h = struct.unpack('<I', f.read(4))[0]
        f.seek(40); data_start = struct.unpack('<I', f.read(4))[0]
        f.seek(pkg_h + 8); entry_cnt = struct.unpack('<I', f.read(4))[0]
        curr = pkg_h + 48
        
        for _ in range(entry_cnt):
            f.seek(curr); kind, size, off = struct.unpack('<III', f.read(12))
            
            if kind == 2:
                abs_start = data_start + off; f.seek(abs_start); end = abs_start + size
                
                while f.tell() < end:
                    try: magic = f.read(4)
                    except: break
                    c_sz = struct.unpack('<I', f.read(4))[0]; c_start = f.tell()
                    
                    if magic == b' DIC':
                        f.seek(c_start); cnt = struct.unpack('<I', f.read(4))[0]; f.read(4)
                        for _ in range(cnt):
                            eo, eh = struct.unpack('<QQ', f.read(16))
                            if eh in [8120115085854712779, 8121310221017043393]:
                                asset_pos = data_start + eo - 16
                                f.seek(asset_pos + 64); f.read(4*8 + 48 + 6*8)
                                meshes_off, meshes_cnt = struct.unpack('<QQ', f.read(16))
                                
                                if meshes_cnt > 0:
                                    f.seek(data_start + meshes_off)
                                    ptrs = struct.unpack(f'<{meshes_cnt}Q', f.read(8*meshes_cnt))
                                    
                                    for ptr in ptrs:
                                        mesh_addr = data_start + ptr
                                        
                                        # read properties (offset, scale)
                                        f.seek(mesh_addr + 56)
                                        off_vec = struct.unpack('<3f', f.read(12))
                                        scale = struct.unpack('<f', f.read(4))[0]
                                        f.read(8); m_hash = struct.unpack('<Q', f.read(8))[0]
                                        
                                        # read index count
                                        f.seek(mesh_addr + 152)
                                        idx_cnt = struct.unpack('<I', f.read(4))[0]
                                        
                                        # read vertex count
                                        f.seek(mesh_addr + 96); attr_arr_off = struct.unpack('<Q', f.read(8))[0]
                                        f.seek(data_start + attr_arr_off + 16)
                                        vert_cnt = struct.unpack('<I', f.read(4))[0]
                                        
                                        state[m_hash] = {
                                            'offset': off_vec,
                                            'scale': scale,
                                            'idx_count': idx_cnt,
                                            'vert_count': vert_cnt,
                                            'mesh_ptr': ptr
                                        }
                    f.seek(c_start + c_sz)
            curr += 40
    return state

def scan_for_conflicts(orig_xpps, mod_files):
    if not os.path.exists(orig_xpps): return {}, {}, ["Original XPPS missing"]
    
    orig_state = read_xpps_state(orig_xpps)
    mod_states = []
    
    for mp in mod_files:
        ms = ModState(mp)
        curr = read_xpps_state(mp)
        
        #detect differences
        for h, info in curr.items():
            if h in orig_state:
                orig = orig_state[h]
                is_changed = (
                    orig['scale'] != info['scale'] or 
                    orig['offset'] != info['offset'] or 
                    orig['idx_count'] != info['idx_count'] or
                    orig['vert_count'] != info['vert_count']
                )
                if is_changed:
                    # mark as modified
                    info['warn_verts'] = info['vert_count'] > orig['vert_count']
                    ms.modifications[h] = info
        
        mod_states.append(ms)
        
    # group modifications by hash
    map_hash_to_mods = {}
    
    for ms in mod_states:
        for h in ms.modifications:
            if h not in map_hash_to_mods: map_hash_to_mods[h] = []
            map_hash_to_mods[h].append(ms)
            
    conflicts = {}
    clean_mods = {}
    
    # identify conflicts (hash modified by > 1 mod)
    for h, modList in map_hash_to_mods.items():
        if len(modList) > 1:
            conflicts[h] = modList
        else:
            clean_mods[h] = modList[0]
            
    return conflicts, clean_mods, orig_state

def combine_with_resolution(orig_xmesh_path, output_root, resolution_map, all_mod_files_list):
    # creates a new mod folder merging selected modifications
    orig_dir = os.path.dirname(orig_xmesh_path)
    orig_basename = os.path.basename(orig_xmesh_path)
    orig_name_no_ext = os.path.splitext(orig_basename)[0]
    
    orig_xpps = os.path.join(orig_dir, orig_name_no_ext + ".xpps")
    if not os.path.exists(orig_xpps):
        candidate = os.path.join(orig_dir, "hero.xpps")
        if os.path.exists(candidate): orig_xpps = candidate
        else: return f"Error: Original XPPS not found in {orig_dir}"

    rnd_id = random.randint(10000, 99999)
    out_dir_name = f"MERGED_MOD_{rnd_id}"
    output_folder = os.path.join(output_root, out_dir_name)
    os.makedirs(output_folder, exist_ok=True)
    
    #copy xpps
    dst_xpps = os.path.join(output_folder, "hero.xpps")
    shutil.copy2(orig_xpps, dst_xpps)
    print(f"[Combiner] Created base metadata: {dst_xpps}")
    
    # copy xmesh files and textures
    copied_xmeshes = set()
    processed_tex_folders = set()
    
    print("[Combiner] Collecting files...")
    
    for mod_xpps in all_mod_files_list:
        mod_dir = os.path.dirname(mod_xpps)
        
        for f in os.listdir(mod_dir):
            if f.endswith(".xmesh"):
                src = os.path.join(mod_dir, f)
                dst = os.path.join(output_folder, f)
                if f not in copied_xmeshes:
                    shutil.copy2(src, dst)
                    copied_xmeshes.add(f)
                    print(f"  Copied XMesh: {f}")
        
        for item in os.listdir(mod_dir):
            if "gapack" in item and os.path.isdir(os.path.join(mod_dir, item)):
                if item not in processed_tex_folders:
                    src = os.path.join(mod_dir, item)
                    dst = os.path.join(output_folder, item)
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    processed_tex_folders.add(item)

    print("[Combiner] Patching hero.xpps metadata...")
    
    with open(dst_xpps, 'r+b') as f_xpps_out:
        f_xpps_out.seek(40); d_s = struct.unpack('<I', f_xpps_out.read(4))[0]
        
        for h, mod_xpps_path in resolution_map.items():
            mod_state = read_xpps_state(mod_xpps_path)
            if h not in mod_state: continue
            
            info = mod_state[h]
            print(f"  -> Applying Hash {h:X}")

            mesh_header_abs = d_s + info['mesh_ptr']
            
            f_xpps_out.seek(mesh_header_abs + 56)
            f_xpps_out.write(struct.pack('<3ff', info['offset'][0], info['offset'][1], info['offset'][2], info['scale']))
            
            f_xpps_out.seek(mesh_header_abs + 152)
            f_xpps_out.write(struct.pack('<I', info['idx_count']))
            
            f_xpps_out.seek(mesh_header_abs + 96)
            attr_arr_off = struct.unpack('<Q', f_xpps_out.read(8))[0]
            f_xpps_out.seek(mesh_header_abs + 112)
            num_attrs = struct.unpack('<Q', f_xpps_out.read(8))[0]
            
            f_xpps_out.seek(d_s + attr_arr_off)
            for _ in range(num_attrs):
                curr = f_xpps_out.tell()
                f_xpps_out.seek(curr + 16)
                f_xpps_out.write(struct.pack('<I', info['vert_count']))
                f_xpps_out.seek(curr + 24)

    return f"Success! Merged Mod created in: {output_folder}"