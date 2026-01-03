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
import struct
from . import utils

# sreader for the db format
class DBReader:
    def __init__(self, filepath):
        self.file = open(filepath, 'rb')
        self.size = os.path.getsize(filepath)
        
    def seek(self, off): 
        self.file.seek(off)

    def tell(self): 
        return self.file.tell()

    def read_bytes(self, l): 
        return self.file.read(l)
    
    def read_uint8(self): 
        return struct.unpack('<B', self.file.read(1))[0]
    
    def read_uint16(self): 
        return struct.unpack('<H', self.file.read(2))[0]
    
    def read_uint32(self): 
        return struct.unpack('<I', self.file.read(4))[0]
    
    def read_uint64(self): 
        return struct.unpack('<Q', self.file.read(8))[0]
    
    def read_uint64_array(self, count): 
        return struct.unpack(f'<{count}Q', self.file.read(8*count))
        
    def close(self): self.file.close()

class TexMeshMan:
    def __init__(self):
        self.textures = {}
        self.loaded = False
        self.loaded_path = ""

    def load(self, filepath):
        if self.loaded and self.loaded_path == filepath: 
            return True
        if not os.path.exists(filepath): 
            return False
            
        try:
            reader = DBReader(filepath)
            # check magic header
            if reader.read_bytes(4) != b'NAMS': 
                reader.close()
                return False
                
            #  skip header junk
            reader.read_uint32(); reader.read_uint64(); reader.read_uint64()
            reader.read_uint32(); reader.read_uint32()
            
            offset = reader.read_uint32(); reader.read_uint32()
            reader.seek(offset + 40)
            
            num_textures = reader.read_uint32()
            reader.read_uint32()
            
            self.textures.clear()
            
            # parse texture entries
            for _ in range(num_textures):
                length = reader.read_uint32()
                name = ""
                
                # read string
                if length != 255 and length > 0:
                    try: 
                        name = reader.read_bytes(length).decode('utf-8', errors='ignore').replace('\x00', '')
                    except: 
                        pass
                
                # skip padding and read hash
                reader.read_bytes(16)
                tex_hash = reader.read_uint64()
                
                reader.read_bytes(11)
                if reader.read_uint8() == 1: 
                    reader.read_bytes(108)
                reader.read_bytes(20)
                
                self.textures[tex_hash] = name
                
            reader.close()
            self.loaded = True
            self.loaded_path = filepath
            return True
        
        except Exception as e:
            print(f"[Ghost] Error loading DB: {e}")
            if 'reader' in locals(): 
                reader.close()
            return False

    def get_name(self, tex_hash):
        return self.textures.get(tex_hash, f"Unknown_{tex_hash:X}")

DB = TexMeshMan()


def find_materials(xpps_path, target_hash, db_path):
    
    if not os.path.exists(xpps_path): 
        return [f"XPPS not found"]
    if not DB.load(db_path): 
        return [f"DB load failed"]
    
    try:
        reader = DBReader(xpps_path)
        
        # read container headers
        reader.seek(24); pkg_h = reader.read_uint32()
        reader.seek(40); data_start = reader.read_uint32()
        reader.seek(pkg_h + 8); entry_count = reader.read_uint32()
        
        curr = pkg_h + 48
        
        # iterate chunks (in xpps)
        for _ in range(entry_count):
            reader.seek(curr)
            kind = reader.read_uint32()
            size = reader.read_uint32()
            off = reader.read_uint32()
            
            if kind == 2: # chunk list
                abs_start = data_start + off
                reader.seek(abs_start)
                end = abs_start + size
                
                #scan sub-chunks
                while reader.tell() < end:
                    try: 
                        magic = reader.read_bytes(4)
                    except: 
                        break
                        
                    c_sz = reader.read_uint32()
                    c_start = reader.tell()
                    
                    # looking for ' DIC' dictionary chunks
                    if magic == b' DIC':
                        reader.seek(c_start)
                        cnt = reader.read_uint32()
                        reader.read_uint32()
                        
                        for _ in range(cnt):
                            e_off = reader.read_uint64()
                            e_hash = reader.read_uint64()
                            
                            # check specific signature hashes
                            if e_hash in [8120115085854712779, 8121310221017043393]:
                                asset_pos = data_start + e_off - 16
                                textures = analyze_full_asset_and_find(reader, asset_pos, data_start, target_hash)
                                if textures is not None: 
                                    reader.close()
                                    return textures
                    
                    reader.seek(c_start + c_sz)
            curr += 40
        reader.close()
    except Exception as e:
        return [f"Error: {e}"]
        
    return ["No material found"]

def analyze_full_asset_and_find(reader, asset_pos, data_start, target_hash):
    #asset structure to link mesh -> material -> texture
    real_asset_start = asset_pos + 64
    reader.seek(real_asset_start)
    
    reader.read_uint64_array(4) 
    reader.read_bytes(48)       
    reader.read_uint64_array(6) 
    
    meshes_off = reader.read_uint64()
    meshes_cnt = reader.read_uint64()
    
    reader.read_uint64_array(8)
    reader.read_uint64_array(10)
    reader.read_uint64() 
    
    modelGroupOffset = reader.read_uint64()
    
    mesh_idx = -1
    
    # find which index our target mesh has
    if meshes_cnt > 0:
        reader.seek(data_start + meshes_off)
        if reader.tell() < reader.size:
            ptrs = reader.read_uint64_array(meshes_cnt)
            for i, ptr in enumerate(ptrs):
                reader.seek(data_start + ptr + 72)
                reader.read_uint64()
                if reader.read_uint64() == target_hash:
                    mesh_idx = i
                    break
    
    if mesh_idx == -1: 
        return None
    
    # resolve material pointer
    if modelGroupOffset != 0:
        reader.seek(data_start + modelGroupOffset)
        reader.read_uint64_array(5)
        mat_ptr_off = reader.read_uint64()
        mat_cnt = reader.read_uint64()
        
        if mesh_idx < mat_cnt:
            reader.seek(data_start + mat_ptr_off + (mesh_idx * 8))
            mat_addr = reader.read_uint64()
            
            if mat_addr == 0: 
                return ["Error: Null Material Pointer"]

            reader.seek(data_start + mat_addr)
            reader.read_uint64_array(6) 
            
            tex_off = reader.read_uint64()
            tex_cnt = reader.read_uint64()
            
            tex_names = []
            if tex_off != 0 and tex_cnt > 0:
                reader.seek(data_start + tex_off)
                for _ in range(tex_cnt):
                    h = reader.read_uint64()
                    reader.read_uint64_array(3) # skip params
                    
                    # use the global DB instance to resolve name
                    tex_names.append(DB.get_name(h))
            
            if not tex_names: 
                return ["Material found but no textures"]
            return tex_names
            
    return ["Material linkage missing"]