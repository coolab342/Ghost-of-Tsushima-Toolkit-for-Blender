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
import bmesh
import mathutils
from ..utils import EXPORT_MATRIX

class ProcessedMesh:
    def __init__(self):
        self.vertices = []      # list of Vector
        self.normals = []       # list of Vector
        self.tangents = []      # list of tuple (x,y,z,w)
        self.uvs = []           # list of tuple (u,v)
        self.colors = []        # list of tuple (r,g,b,a)
        
        # skinning data
        self.bone_indices = []  # list of [i,i,i,i]
        self.bone_weights = []  # list of [w,w,w,w]
        
        self.indices = []       # flat list of triangle indices
        self.direction = []     # extra data (often unused)
        
        # bounding box info
        self.offset = mathutils.Vector((0,0,0))
        self.scale = 1.0

def process_mesh(obj):
    print(f"[Ghost] Processing Blender Mesh: {obj.name}")
    
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    
    bm = bmesh.new()
    bm.from_object(eval_obj, depsgraph)
    
    bmesh.ops.triangulate(bm, faces=bm.faces)
    
    temp_mesh = bpy.data.meshes.new("TempInject")
    bm.to_mesh(temp_mesh)
    bm.free()
    
    # calculate tangents for normal mapping
    if temp_mesh.uv_layers:
        try: temp_mesh.calc_tangents()
        except: pass
        
    data = ProcessedMesh()
    
    unique_verts = {}
    next_idx = 0
    
    uv_layer = temp_mesh.uv_layers.active.data if temp_mesh.uv_layers else None
    col_layer = temp_mesh.color_attributes.active_color.data if temp_mesh.color_attributes.active_color else None
    
    # build bone mapping (vertex group name-> bone index)
    bone_map = {}
    for g in obj.vertex_groups:
        if g.name.startswith("Bone_"):
            try: 
                b_idx = int(g.name.split("_")[1])
                bone_map[g.index] = b_idx
            except: 
                pass

    for poly in temp_mesh.polygons:
        for loop_idx in poly.loop_indices:
            loop = temp_mesh.loops[loop_idx]
            v = temp_mesh.vertices[loop.vertex_index]
            
            # transform position/normal to game space
            pos = EXPORT_MATRIX @ v.co
            norm = (EXPORT_MATRIX.to_3x3() @ loop.normal).normalized()
            
            # extract uv
            uv = (0.0, 0.0)
            if uv_layer: 
                raw_uv = uv_layer[loop_idx].uv
                uv = (raw_uv.x, raw_uv.y)
                
            # extract tangent
            tan = (1.0, 0.0, 0.0, 1.0)
            if hasattr(loop, "tangent"):
                t = (EXPORT_MATRIX.to_3x3() @ loop.tangent).normalized()
                tan = (t.x, t.y, t.z, loop.bitangent_sign)
            
            # extract weights
            w_list = []
            for g in v.groups:
                if g.group in bone_map:
                    w_list.append((bone_map[g.group], g.weight))
            
            w_list.sort(key=lambda x: x[1], reverse=True)
            w_list = w_list[:4]
            
            # normalize weights to sum to 1.0
            total = sum(w for b,w in w_list)
            if total > 0: 
                w_list = [(b, w/total) for b,w in w_list]
            
            final_bi = [-1]*4
            final_bw = [0.0]*4
            
            for i, (bid, w) in enumerate(w_list):
                final_bi[i] = bid
                final_bw[i] = w
            
            # extract color
            col = (1.0, 1.0, 1.0, 1.0)
            if col_layer and hasattr(col_layer[loop_idx], "color"): 
                col = col_layer[loop_idx].color
            
            # rounding is important to merge vertices that are geometrically identical
            key = (
                round(pos.x, 4), round(pos.y, 4), round(pos.z, 4), 
                round(norm.x, 3), round(norm.y, 3), round(norm.z, 3), 
                round(uv[0], 4), round(uv[1], 4)
            )
            
            if key in unique_verts:
                data.indices.append(unique_verts[key])
            else:
                unique_verts[key] = next_idx
                data.indices.append(next_idx)
                next_idx += 1
                
                #store attributes
                data.vertices.append(pos)
                data.normals.append(norm)
                data.tangents.append(tan)
                data.uvs.append(uv)
                data.bone_indices.append(final_bi)
                data.bone_weights.append(final_bw)
                data.colors.append(col)
                data.direction.append(0.0)

    bpy.data.meshes.remove(temp_mesh)
    
    if not data.vertices: 
        print("[Ghost] Error: No vertices extracted!")
        return None
    
    # calculate bounding box (min/max) for compression
    min_v = mathutils.Vector((999999.0, 999999.0, 999999.0))
    max_v = mathutils.Vector((-999999.0, -999999.0, -999999.0))
    
    for v in data.vertices:
        min_v.x = min(min_v.x, v.x); min_v.y = min(min_v.y, v.y); min_v.z = min(min_v.z, v.z)
        max_v.x = max(max_v.x, v.x); max_v.y = max(max_v.y, v.y); max_v.z = max(max_v.z, v.z)
        
    # calculate offset (center) and scale (extent)
    data.offset = (min_v + max_v) * 0.5
    extent = max_v - min_v
    data.scale = max(extent.x, max(extent.y, extent.z)) * 0.5
    
    if data.scale <= 0.0001: data.scale = 1.0
        
    print(f"[Ghost] BBox -> Min: {min_v} Max: {max_v}")
    print(f"[Ghost] Calc -> Offset: {data.offset} Scale: {data.scale}")
        
    return data