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
from ..utils import BinaryWriter, GTVertexAttributeType, encode_pos_16_snorm, pack_10_10_10_2
from .mesh_processing import process_mesh
from ..importer.core import parse_xpps_metadata

def update_xpps_bbox(xpps_path, target_hash, new_offset, new_scale, new_idx_count, new_vert_count):
    with open(xpps_path, 'r+b') as f:
        # read headers
        f.seek(24); pkg_h = struct.unpack('<I', f.read(4))[0]
        f.seek(40); data_start = struct.unpack('<I', f.read(4))[0]
        f.seek(pkg_h + 8); entry_cnt = struct.unpack('<I', f.read(4))[0]
        curr = pkg_h + 48
        
        # traverse chunks similar to the importer
        for _ in range(entry_cnt):
            f.seek(curr); kind, size, off = struct.unpack('<III', f.read(12))
            
            if kind == 2:
                abs_start = data_start + off
                f.seek(abs_start); end = abs_start + size
                
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
                                        f.seek(mesh_addr + 72); f.read(8)
                                        mh = struct.unpack('<Q', f.read(8))[0]
                                        
                                        if mh == target_hash:
                                            print(f"[Ghost] Updating XPPS @ {mesh_addr}: Offset {new_offset}, Scale {new_scale}")
                                            
                                            # write position offset sccale
                                            f.seek(mesh_addr + 56)
                                            f.write(struct.pack('<fff', new_offset.x, new_offset.y, new_offset.z))
                                            f.write(struct.pack('<f', new_scale))
                                            
                                            # write index count
                                            f.seek(mesh_addr + 152)
                                            f.write(struct.pack('<I', new_idx_count))
                                            
                                            # write Vertex Count
                                            f.seek(mesh_addr + 96)
                                            attr_array_off = struct.unpack('<Q', f.read(8))[0]
                                            f.seek(mesh_addr + 112)
                                            num_attrs = struct.unpack('<Q', f.read(8))[0]
                                            
                                            f.seek(data_start + attr_array_off)
                                            for _ in range(num_attrs):
                                                curr_attr = f.tell()
                                                f.seek(curr_attr + 16)
                                                f.write(struct.pack('<I', new_vert_count))
                                                f.seek(curr_attr + 24)
                                            return
                    f.seek(c_start + c_sz)
            curr += 40

def inject_mesh(context, item, xmesh_path, db_path):
    # coordinates the injection process
    target_hash = int(item.original_hash, 16)
    obj = item.new_mesh
    
    print(f"\n[Ghost] START INJECTION: {item.original_hash}")
    
    # find xpps file for metadata
    folder = os.path.dirname(xmesh_path)
    fname = os.path.splitext(os.path.basename(xmesh_path))[0]
    xpps_path = os.path.join(folder, fname + ".xpps")
    if not os.path.exists(xpps_path): xpps_path = os.path.join(folder, "hero.xpps")
    
    meta_map, _ = parse_xpps_metadata(xpps_path)
    if target_hash not in meta_map: 
        return f"Hash {item.original_hash} not found in XPPS."
    
    meta = meta_map[target_hash]
    
    # convert blender mesh to raw data
    mesh_data = process_mesh(obj)
    if not mesh_data: 
        return "Mesh processing failed"
    
    print(f"[Ghost] New Geometry: {len(mesh_data.vertices)} Verts, {len(mesh_data.indices)//3} Tris")

    idx_writer = BinaryWriter()
    for idx in mesh_data.indices: 
        idx_writer.write_uint16(idx)
    new_indices = idx_writer.get_bytes()

    with open(xmesh_path, 'r+b') as f:
        f.seek(24); buffer_data_start = struct.unpack('<Q', f.read(8))[0]
        f.seek(40); num_meshes = struct.unpack('<I', f.read(4))[0]
        
        my_header_pos = -1
        idx_offset = 0
        v_offsets = []
        
        for _ in range(num_meshes):
            pos = f.tell()
            mh = struct.unpack('<Q', f.read(8))[0]
            
            if mh == target_hash:
                my_header_pos = pos
                idx_offset = struct.unpack('<I', f.read(4))[0]
                f.read(2)
                num_v_buffers = struct.unpack('<B', f.read(1))[0]
                v_offsets = struct.unpack(f'<{num_v_buffers}I', f.read(4*num_v_buffers))
                break
            else:
                f.read(4) # skip idx offset
                f.read(2) # skip lod
                nv = struct.unpack('<B', f.read(1))[0]
                f.read(4*nv) # skip v offsets
        
        if my_header_pos == -1: 
            return "Hash not found in XMesh"
        
        # write indecies
        abs_idx_off = buffer_data_start + idx_offset
        orig_idx_count = meta.get('face_count', 0)
        available_idx_size = orig_idx_count * 2 # 2 bytes per index
        
        if len(new_indices) > available_idx_size: 
            return f"Index Buffer too large! New: {len(new_indices)} > Max: {available_idx_size}"
        
        f.seek(abs_idx_off)
        f.write(new_indices)
        # pad remainder with zeros
        f.write(b'\x00' * (available_idx_size - len(new_indices)))
        
        # write vertices
        vert_count = len(mesh_data.vertices)
        orig_vert_count = meta.get('vertex_count', 0)
        
        if vert_count > orig_vert_count:
             return f"Vertex count too high! New: {vert_count} > Max: {orig_vert_count}"
        
        
        for i in range(vert_count):
            written_ranges = set()

            for ai, attr in enumerate(meta['attributes']):
                fmt = attr['format']
                stride = attr['stride']
                
                abs_pos = buffer_data_start + v_offsets[ai] + (i * stride)
                
                # check for overlap
                is_overlap = False
                for r in range(stride):
                    if (abs_pos + r) in written_ranges:
                        is_overlap = True
                        break
                
                if is_overlap:
                    continue

                f.seek(abs_pos)
                
                if ai == 0:
                    if stride == 8:
                        x, y, z = encode_pos_16_snorm(mesh_data.vertices[i], mesh_data.offset, mesh_data.scale)
                        f.write(struct.pack('<hhhH', x, y, z, 0x3C00))
                    else:
                        v = mesh_data.vertices[i]
                        f.write(struct.pack('<ffff', v.x, v.y, v.z, 1.0))
                    
                    for r in range(stride): written_ranges.add(abs_pos + r)
                    continue

                bytes_to_write = b''
                
                if fmt == GTVertexAttributeType.Format_32_32_32_Float:
                    v = mesh_data.vertices[i]
                    bytes_to_write = struct.pack('<ffff', v.x, v.y, v.z, 1.0)

                elif fmt == GTVertexAttributeType.Format_10_10_10_Snorm:
                    # normals/tangents
                    is_tangent = False
                    prev_snorms = sum(1 for sub_a in meta['attributes'][:ai] if sub_a['format'] == GTVertexAttributeType.Format_10_10_10_Snorm)
                    if prev_snorms > 0: is_tangent = True
                    
                    val = 0
                    if not is_tangent:
                        n = mesh_data.normals[i]
                        val = pack_10_10_10_2(n.x, n.y, n.z, 0)
                    else:
                        t = mesh_data.tangents[i]
                        val = pack_10_10_10_2(t[0], t[1], t[2], 1.0 if t[3] > 0 else 0.0)
                    bytes_to_write = struct.pack('<I', val)
                
                elif fmt == GTVertexAttributeType.Format_16_16_Float:
                    # UV
                    u, v = mesh_data.uvs[i]
                    bytes_to_write = struct.pack('<ee', u, v)
                
                elif fmt == GTVertexAttributeType.Format_8_8_8_8_Unorm:
                    # weights or colors
                    has_bone_idx = any(a['format'] == GTVertexAttributeType.Format_16_16_16_16_Unit for a in meta['attributes'])
                    is_weight = has_bone_idx and attr['format'] == GTVertexAttributeType.Format_8_8_8_8_Unorm
                    
                    if is_weight:
                        w = mesh_data.bone_weights[i]
                        b1 = int(w[1] * 255); b2 = int(w[2] * 255); b3 = int(w[3] * 255)
                        bytes_to_write = struct.pack('<BBBB', b1, b2, b3, 0)
                    else:
                        c = mesh_data.colors[i]
                        bytes_to_write = struct.pack('<BBBB', int(c[0]*255), int(c[1]*255), int(c[2]*255), int(c[3]*255))

                elif fmt == GTVertexAttributeType.Format_16_16_16_16_Unit:
                    #bone indices
                    bi = mesh_data.bone_indices[i]
                    bytes_to_write = struct.pack('<hhhh', bi[0], bi[1], bi[2], bi[3])

                if bytes_to_write:
                    # align length
                    if len(bytes_to_write) < stride:
                        bytes_to_write += b'\x00' * (stride - len(bytes_to_write))
                    elif len(bytes_to_write) > stride:
                        bytes_to_write = bytes_to_write[:stride]
                    
                    f.write(bytes_to_write)
                    for r in range(stride): written_ranges.add(abs_pos + r)

        # pad unused vertices at the end to avoid graphical glitches
        remaining_verts = orig_vert_count - vert_count
        if remaining_verts > 0:
            tail_pattern = b'\x74\xFC\x0F\xFF\x01\x80\x00\x00'
            
            for ai, attr in enumerate(meta['attributes']):
                if ai == 0 and attr['stride'] == 8:
                    fill_block = tail_pattern * remaining_verts
                    start_tail_pos = buffer_data_start + v_offsets[ai] + (vert_count * 8)
                    f.seek(start_tail_pos)
                    f.write(fill_block)
                
    # update metadata (BBox, Counts)
    update_xpps_bbox(xpps_path, target_hash, mesh_data.offset, mesh_data.scale, len(mesh_data.indices), len(mesh_data.vertices))
    
    return "SUCCESS"