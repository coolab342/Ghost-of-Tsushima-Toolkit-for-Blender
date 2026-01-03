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
import mathutils
from ..utils import GLOBAL_MATRIX, BinaryReader

def parse_skeleton_data(reader, info_offset, data_start):
    # reads the skeleton hierarchy from the xpps chunk
    reader.seek(info_offset)
    reader.read_uint64()
    reader.read_uint64() 
    skel_offset = reader.read_uint64()
    reader.read_uint64()
    parent_indices_off = reader.read_uint64()
    unk3_off = reader.read_uint64()
    
    abs_skel_off = data_start + skel_offset
    reader.seek(abs_skel_off)
    
    # signature check 60SE
    if reader.read_string(4) != "60SE": return None
    
    reader.read_uint32(); reader.read_uint32(); reader.read_uint32()
    num_bones = reader.read_uint16()
    reader.read_uint16(); reader.read_uint16(); reader.read_uint16()
    
    bone_offset = reader.read_relative_offset_32()
    
    # read parent indices array
    reader.seek(data_start + parent_indices_off)
    count_indices = (unk3_off - parent_indices_off) // 4
    parent_indices = [-1] * num_bones
    
    for _ in range(count_indices):
        idx = reader.read_uint16()
        flag = reader.read_int16()
        parent_idx = flag & 0x7FFF
        if parent_idx == 0x7FFF: parent_idx = -1
        
        if idx < num_bones: 
            parent_indices[idx] = parent_idx

    # read bone transform data
    reader.seek(bone_offset)
    bones = []
    for i in range(num_bones):
        bones.append({
            'index': i, 
            'rot': reader.read_vec4(), 
            'pos': reader.read_vec4(), 
            'scl': reader.read_vec4(), 
            'parent': parent_indices[i]
        })
    return bones

def build_skeleton(bones, collection):
    # blender armature creation
    armature_data = bpy.data.armatures.new("GhostArmature")
    armature_obj = bpy.data.objects.new("GhostArmature", armature_data)
    collection.objects.link(armature_obj)
    
    armature_obj.display_type = 'WIRE'
    armature_data.display_type = 'OCTAHEDRAL'
    armature_obj.show_in_front = True
    
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    edit_bones = []

    for b in bones: 
        edit_bones.append(armature_data.edit_bones.new(f"Bone_{b['index']}"))
    
    bone_matrices = [None] * len(bones)
    
    def get_matrix(idx):
        if bone_matrices[idx]: return bone_matrices[idx]
        b = bones[idx]
        
        #game stores Quats as X,Y,Z,W  blender is W,X,Y,Z
        loc = mathutils.Vector(b['pos'][:3])
        rot = mathutils.Quaternion((b['rot'][3], b['rot'][0], b['rot'][1], b['rot'][2]))
        scl = mathutils.Vector(b['scl'][:3])
        
        mat = mathutils.Matrix.LocRotScale(loc, rot, scl)
        
        if b['parent'] != -1: 
            mat = get_matrix(b['parent']) @ mat
            
        bone_matrices[idx] = mat
        return mat

    # apply matrices to edit bones
    for i, b in enumerate(bones):
        eb = edit_bones[i]
        final_mat = GLOBAL_MATRIX @ get_matrix(i)
        
        eb.head = final_mat.to_translation()
        
        if b['parent'] != -1:
            eb.parent = edit_bones[b['parent']]
            eb.use_connect = False
        
        # calculate tail (arbitrary length along Y axis)
        local_y = final_mat.to_3x3() @ mathutils.Vector((0, 1, 0))
        eb.tail = eb.head + (local_y * 6) 

    bpy.ops.object.mode_set(mode='OBJECT')
    return armature_obj