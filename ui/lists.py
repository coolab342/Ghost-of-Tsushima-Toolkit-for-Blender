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

class GHOST_UL_ModFileList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        filename = os.path.basename(item.filepath)
        folder_name = os.path.basename(os.path.dirname(item.filepath))
        
        layout.label(text=f"{filename} ({folder_name})", icon='FILE')

class GHOST_UL_ConflictList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        col = layout.column()
        
        row = col.row()
        row.label(text=f"{item.mesh_name} ({item.hash_str})", icon='MESH_DATA')
        
        if len(item.variants) > 0 and item.selected_variant_index < len(item.variants):
            sel = item.variants[item.selected_variant_index]
            
            split = col.split(factor=0.6)
            sub = split.column()
            row = sub.row()
            if sel.warn_verts:
                row.alert = True
                row.label(text=f"Verts: {sel.vert_count} (Too High!)", icon='ERROR')
            else:
                row.label(text=f"Verts: {sel.vert_count}")
            sub.label(text=f"Scale: {sel.scale:.2f}")
            
            split.label(text=f"Using: {sel.name}", icon='CHECKMARK')

class GHOST_UL_MeshInfoList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.prop(item, "is_selected", text="")
            row.label(text=f"{item.mesh_hash}")
            row.label(text=f"LOD {item.lod}")
            row.label(text=f"V: {item.vertex_count}")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.mesh_hash)

    def filter_items(self, context, data, propname):
        props = context.scene.ghost_tool
        items = getattr(data, propname)
        flt_flags = []
        flt_neworder = []
        
        if not props.search_filter:
            flt_flags = [self.bitflag_filter_item] * len(items)
        else:
            search = props.search_filter.upper()
            flt_flags = [
                self.bitflag_filter_item if (
                    search in item.mesh_hash or 
                    search in str(item.lod) or 
                    search in str(item.vertex_count)
                ) else 0 
                for item in items
            ]
            
        return flt_flags, flt_neworder

class GHOST_UL_ReplacementList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.35)
        split.label(text=item.original_hash)
        split.prop(item, "new_mesh", text="")