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

import bpy
import os
import struct
import math
import mathutils
from ..utils import BinaryReader, GTVertexAttributeType, GLOBAL_MATRIX, decode_pos, unpack_10_10_10_2
from .skeleton import parse_skeleton_data, build_skeleton

def parse_xpps_metadata(filepath):
    if not os.path.exists(filepath): 
        return {}, None
    
    with open(filepath, 'rb') as f: 
        data = f.read()

    reader = BinaryReader(data)
    
    if len(data) < 64: return {}, None
    
    reader.seek(24); pkg_h = reader.read_uint32()
    reader.seek(40); data_start = reader.read_uint32()
    
    metadata_map = {}
    skeleton_data = None
    
    reader.seek(pkg_h + 8); entry_cnt = reader.read_uint32()
    curr_pkg = pkg_h + 48
    
    for _ in range(entry_cnt):
        reader.seek(curr_pkg); kind = reader.read_uint32(); sz = reader.read_uint32(); off = reader.read_uint32()
        
        if kind == 2: # ChunkList
            chunk_list_abs = data_start + off
            reader.seek(chunk_list_abs)
            end_pos = chunk_list_abs + sz
            
            while reader.pos < end_pos:
                try: magic = reader.read_bytes(4).decode('ascii')
                except: magic="????"
                c_sz = reader.read_uint32(); c_start = reader.pos
                
                if magic == " DIC":
                    reader.seek(c_start); dic_cnt = reader.read_uint32(); reader.read_uint32()
                    for _ in range(dic_cnt):
                        e_off = reader.read_uint64(); e_hash = reader.read_uint64()
                        
                        # known hashes for mesh asset containers
                        if e_hash in [8120115085854712779, 8121310221017043393]:
                            head_pos = data_start + e_off - 16
                            
                            # try parsing skeleton info
                            reader.seek(head_pos + 64 + 336)
                            skel_info_offset = reader.read_uint64()
                            if skel_info_offset != 0 and skeleton_data is None:
                                skeleton_data = parse_skeleton_data(reader, data_start + skel_info_offset, data_start)
                            
                            #parse meshes info
                            reader.seek(head_pos + 192)
                            m_off_rel = reader.read_uint64(); m_cnt = reader.read_uint64()
                            
                            if m_cnt > 0:
                                reader.seek(data_start + m_off_rel)
                                ptrs = reader.read_uint64_array(m_cnt)
                                
                                for ptr in ptrs:
                                    reader.seek(data_start + ptr + 56)
                                    v_off = reader.read_vec3(); v_scl = reader.read_float()
                                    reader.read_uint64(); m_hash_val = reader.read_uint64()
                                    
                                    reader.read_uint64(); attr_off = reader.read_uint64()
                                    reader.read_uint64(); num_attrs = reader.read_uint64()
                                    
                                    reader.read_bytes(32)
                                    face_count = reader.read_uint32()
                                    
                                    attrs = []
                                    reader.seek(data_start + attr_off)
                                    vertex_count = 0
                                    
                                    for _ in range(num_attrs):
                                        reader.read_uint64(); fmt = reader.read_uint32()
                                        stride = reader.read_uint32(); cnt = reader.read_uint32()
                                        reader.read_uint32()
                                        attrs.append({'format': fmt, 'stride': stride, 'count': cnt})
                                        if vertex_count == 0: vertex_count = cnt
                                        
                                    metadata_map[m_hash_val] = {
                                        'scale': v_scl, 
                                        'offset': v_off, 
                                        'attributes': attrs, 
                                        'face_count': face_count, 
                                        'vertex_count': vertex_count
                                    }
                reader.seek(c_start + c_sz)
        curr_pkg += 40
    return metadata_map, skeleton_data

def scan_xmesh(filepath):
    # scan of xmesh headers for the ui list
    infos = []
    dir_path = os.path.dirname(filepath)
    fname = os.path.splitext(os.path.basename(filepath))[0]
    
    xpps_path = os.path.join(dir_path, fname + ".xpps")

    if not os.path.exists(xpps_path): 
        xpps_path = os.path.join(dir_path, "hero.xpps")
    
    meta_map, _ = parse_xpps_metadata(xpps_path)
    
    with open(filepath, 'rb') as f: 
        data = f.read()

    reader = BinaryReader(data)
    
    if reader.read_string(4) != "SMBS": 
        return []
    
    reader.seek(40); num_meshes = reader.read_uint32()
    
    for _ in range(num_meshes):
        header_start = reader.tell()
        m_hash = reader.read_uint64(); reader.read_uint32() 
        lod = reader.read_uint16(); num_v = reader.read_uint8()
        
        reader.read_uint32_array(num_v)
        
        v_count = 0; f_count = 0
        if m_hash in meta_map:
            v_count = meta_map[m_hash].get('vertex_count', 0)
            f_count = meta_map[m_hash].get('face_count', 0)
            
        infos.append({
            "hash": f"{m_hash:X}", 
            "lod": lod, 
            "verts": v_count, 
            "faces": f_count // 3
        })
        
        reader.seek(header_start + 15 + (4 * num_v))
    return infos

def import_selected(context, filepath, selected_hashes=None, use_skeleton=True, db_path=""):
    dir_path = os.path.dirname(filepath)
    fname = os.path.splitext(os.path.basename(filepath))[0]
    xpps_path = os.path.join(dir_path, fname + ".xpps")
    if not os.path.exists(xpps_path): xpps_path = os.path.join(dir_path, "hero.xpps")
    
    metadata, skeleton_data = parse_xpps_metadata(xpps_path)
    if not metadata: return "ERROR: No XPPS metadata found."

    col_name = fname
    col = bpy.data.collections.new(col_name)
    context.scene.collection.children.link(col)
    
    arm_obj = None
    if use_skeleton and skeleton_data:
        arm_obj = build_skeleton(skeleton_data, col)

    with open(filepath, 'rb') as f: data = f.read()
    reader = BinaryReader(data)
    
    reader.seek(24); buffer_offset = reader.read_uint64()
    reader.seek(40); num_meshes = reader.read_uint32()
    
    imported_count = 0
    
    for _ in range(num_meshes):
        header_start = reader.tell()
        m_hash = reader.read_uint64(); idx_off = reader.read_uint32()
        lod = reader.read_uint16(); num_v = reader.read_uint8()
        v_offs = reader.read_uint32_array(num_v)
        
        hex_hash = f"{m_hash:X}"
        
        # filter logic
        should_import = True
        if selected_hashes and len(selected_hashes) > 0:
            if hex_hash not in selected_hashes: should_import = False

        if should_import and m_hash in metadata:
            meta = metadata[m_hash]
            
            # indecies
            reader.seek(buffer_offset + idx_off)
            fc = meta.get('face_count', 0); faces = []
            if fc > 0:
                raw = struct.unpack(f'<{fc}H', reader.read_bytes(fc*2))
                faces = [raw[j:j+3] for j in range(0, len(raw), 3)]

            # vertecies
            verts = []; normals = []; tangents = []; uvs_layers = []; colors = []
            extra_layers = []
            cnt_snorm10 = 0 
            
            for ai, at in enumerate(meta['attributes']):
                fmt = at['format']; count = at['count']
                reader.seek(buffer_offset + v_offs[ai])
                
                if fmt == GTVertexAttributeType.Format_16_16_16_Snorm:
                    # postion (compressed)
                    for _ in range(count):
                        p = decode_pos(reader, at, meta)
                        verts.append(GLOBAL_MATRIX @ mathutils.Vector(p))
                        
                elif fmt == GTVertexAttributeType.Format_32_32_32_Float:
                    # position (full float)
                    for _ in range(count):
                        p = reader.read_vec3()
                        verts.append(GLOBAL_MATRIX @ mathutils.Vector(p))

                elif fmt == GTVertexAttributeType.Format_10_10_10_Snorm:
                    # normals/tangents
                    raw_data = reader.read_uint32_array(count)
                    curr_vecs = []
                    for val in raw_data:
                        x, y, z, w = unpack_10_10_10_2(val)
                        vec = (mathutils.Vector((x, y, z)) * 2.0) - mathutils.Vector((1.0, 1.0, 1.0))
                        rot_vec = GLOBAL_MATRIX.to_3x3() @ vec
                        curr_vecs.append(rot_vec)
                    
                    if cnt_snorm10 == 0: 
                        normals = curr_vecs
                    elif cnt_snorm10 == 1: 
                        tangents = curr_vecs

                    cnt_snorm10 += 1

                elif fmt == GTVertexAttributeType.Format_16_16_Float:
                    # UVs
                    curr_uvs = []
                    for _ in range(count):
                        u = reader.read_half() # half float
                        v = reader.read_half()
                        curr_uvs.append((u, v)) 
                    uvs_layers.append(curr_uvs)

                elif fmt == GTVertexAttributeType.Format_8_8_8_8_Unorm:
                    # Colors
                    raw_bytes = reader.read_bytes(count * 4)
                    curr_cols = []
                    for k in range(count):
                        r, g, b, a = raw_bytes[k*4]/255.0, raw_bytes[k*4+1]/255.0, raw_bytes[k*4+2]/255.0, raw_bytes[k*4+3]/255.0
                        curr_cols.append((r, g, b, a))
                    colors.append(curr_cols)

                elif fmt == GTVertexAttributeType.Format_Unk1: #UInt16
                    curr_unk = []
                    for _ in range(count):
                        val = reader.read_uint16()
                        if at['stride'] > 2: reader.read_bytes(at['stride'] - 2)
                        
                        norm = val / 65535.0
                        curr_unk.append((norm, norm, norm, 1.0))
                    extra_layers.append({"name": f"UNK1_{fmt}", "data": curr_unk})

                elif fmt == GTVertexAttributeType.Format_Unk2: # float, float
                    curr_unk = []
                    for _ in range(count):
                        v1 = reader.read_float()
                        v2 = reader.read_float()
                        curr_unk.append((v1, v2, 0.0, 1.0))
                    extra_layers.append({"name": f"UNK2_{fmt}", "data": curr_unk})
                
                elif fmt == GTVertexAttributeType.Format_Unk3: # float
                    curr_unk = []
                    for _ in range(count):
                        v1 = reader.read_float()
                        curr_unk.append((v1, v1, v1, 1.0))
                    extra_layers.append({"name": f"UNK3_{fmt}", "data": curr_unk})
                
                elif fmt == GTVertexAttributeType.Format_Unk4: # Int16
                    curr_unk = []
                    for _ in range(count):
                        val = reader.read_int16()
                        if at['stride'] > 2: reader.read_bytes(at['stride'] - 2)
                        norm = (val + 32768) / 65535.0 
                        curr_unk.append((norm, norm, norm, 1.0))
                    extra_layers.append({"name": f"UNK4_{fmt}", "data": curr_unk})
                
                elif fmt == GTVertexAttributeType.Format_Unk5: # Int32
                    curr_unk = []
                    for _ in range(count):
                        val = reader.read_int32()
                        norm = abs(val) / 2147483647.0
                        curr_unk.append((norm, norm, norm, 1.0))
                    extra_layers.append({"name": f"UNK5_{fmt}", "data": curr_unk})

            if verts:
                imported_count += 1
                mname = f"LOD{lod}_{hex_hash}"
                mesh = bpy.data.meshes.new(mname)
                obj = bpy.data.objects.new(mname, mesh)
                col.objects.link(obj)
                
                mesh.from_pydata(verts, [], faces)
                
                # apply normals
                if normals and len(normals) == len(verts):
                    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
                    loop_normals = [normals[loop.vertex_index] for loop in mesh.loops]
                    try: 
                        mesh.normals_split_custom_set(loop_normals)
                    except AttributeError:
                        mesh.create_normals_split()
                        mesh.normals_split_custom_set(loop_normals)
                    except: pass

                # apply UV
                for i, layer in enumerate(uvs_layers):
                    uv_l = mesh.uv_layers.new(name=f"UVMap_{i}")
                    for loop in mesh.loops: 
                        uv_l.data[loop.index].uv = layer[loop.vertex_index]

                # apply colors
                for i, col_data in enumerate(colors):
                    vcol = mesh.color_attributes.new(name=f"Color_{i}", type='BYTE_COLOR', domain='CORNER')
                    for loop in mesh.loops: 
                        vcol.data[loop.index].color = col_data[loop.vertex_index]

                # apply weights
                idx_attr = next((at for at in meta['attributes'] if at['format'] == GTVertexAttributeType.Format_16_16_16_16_Unit), None)
                wgt_attr = next((at for at in meta['attributes'] if at['format'] == GTVertexAttributeType.Format_8_8_8_8_Unorm), None)
                
                if idx_attr and wgt_attr and arm_obj:
                    idx_idx = meta['attributes'].index(idx_attr)
                    wgt_idx = meta['attributes'].index(wgt_attr)
                    idx_stride = idx_attr['stride']
                    wgt_stride = wgt_attr['stride']
                    
                    # create vertex groups
                    for bone in arm_obj.data.bones:
                        if bone.name not in obj.vertex_groups:
                            obj.vertex_groups.new(name=bone.name)

                    obj.parent = arm_obj
                    mod = obj.modifiers.new("Armature", 'ARMATURE')
                    mod.object = arm_obj
                    
                    # read raw buffers for weights
                    reader.seek(buffer_offset + v_offs[idx_idx])
                    raw_idx_buffer = reader.read_bytes(idx_attr['count'] * idx_stride)
                    reader.seek(buffer_offset + v_offs[wgt_idx])
                    raw_wgt_buffer = reader.read_bytes(wgt_attr['count'] * wgt_stride)

                    # weights per vertex
                    for k in range(len(verts)):
                        curr_idx_pos = k * idx_stride
                        raw_ids = struct.unpack('<4h', raw_idx_buffer[curr_idx_pos : curr_idx_pos + 8])
                        
                        curr_wgt_pos = k * wgt_stride
                        ws = struct.unpack('<4B', raw_wgt_buffer[curr_wgt_pos : curr_wgt_pos + 4])
                        
                        w_explicit_1 = ws[0] if raw_ids[1] != -1 else 0
                        w_explicit_2 = ws[1] if raw_ids[2] != -1 else 0
                        w_explicit_3 = ws[2] if raw_ids[3] != -1 else 0
                        
                        sum_explicit = w_explicit_1 + w_explicit_2 + w_explicit_3
                        w_implicit_0 = max(0, 255 - sum_explicit)
                        
                        id_0 = raw_ids[0] if raw_ids[0] >= 0 else 0
                        id_1 = raw_ids[1]
                        id_2 = raw_ids[2]
                        id_3 = raw_ids[3]
                        
                        assignments = []
                        total_sum = 0.0
                        
                        def push_w(bid, val):
                            nonlocal total_sum
                            if bid >= 0 and val > 0:
                                w_float = val / 255.0
                                assignments.append((bid, w_float))
                                total_sum += w_float

                        push_w(id_0, w_implicit_0)
                        push_w(id_1, w_explicit_1)
                        push_w(id_2, w_explicit_2)
                        push_w(id_3, w_explicit_3)
                        
                        # assign to groups
                        for b_id, w in assignments:
                            final_w = w / total_sum if total_sum > 0 else w
                            if final_w > 0.001:
                                g_name = f"Bone_{b_id}"
                                g = obj.vertex_groups.get(g_name)
                                if g: g.add([k], final_w, 'REPLACE')

        # advance to next mesh header
        reader.seek(header_start + 15 + (4 * num_v))
    
    return f"SUCCESS: Imported {imported_count} meshes"