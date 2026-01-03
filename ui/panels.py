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
from .. import properties 

class VIEW3D_PT_GhostPanel(bpy.types.Panel):
    bl_label = "Ghost of Tsushima Model Worker"
    bl_idname = "VIEW3D_PT_ghost_tool"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Ghost Tool"

    def draw(self, context):
        layout = self.layout
        props = context.scene.ghost_tool
        
        box = layout.box()
        col = box.column(align=True)
        
        row = col.row()
        row.label(text="Created by Dave349234", icon='USER')
        
        row = col.row(align=True)
        row.scale_y = 1.4 
        
        op_nexus = row.operator("wm.url_open", text="Nexus Mods", icon='WORLD')
        op_nexus.url = "https://www.nexusmods.com/profile/Dave349234"
        
        op_kofi = row.operator("wm.url_open", text="Support / Donate", icon='FUND')
        op_kofi.url = "https://ko-fi.com/dave349234"
        
        layout.separator()

        # import section
        layout.label(text="Import / Inspect", icon='IMPORT')
        box = layout.box()
        
        box.prop(props, "filepath", text="Model (.xmesh)")
        
        # auto-check for DB file existence
        if props.filepath:
            folder = os.path.dirname(bpy.path.abspath(props.filepath))
            db_path = os.path.join(folder, "game.sprig.texmeshman")
            if os.path.exists(db_path):
                box.label(text="DB found (Auto)", icon='CHECKMARK')
            else:
                box.label(text="DB missing! (Put in same folder)", icon='ERROR')

        row = box.row()
        row.scale_y = 1.2
        row.operator("ghost.analyze_file", icon='FILE_REFRESH', text="Scan Model")
        
        if len(props.found_meshes) > 0:
            row = box.row()
            row.label(text=f"Meshes: {len(props.found_meshes)}")
            
            r = row.row(align=True)
            r.operator("ghost.select_all", text="All").action = True
            r.operator("ghost.select_all", text="None").action = False
            
            box.prop(props, "search_filter", icon='VIEWZOOM')
            
            row = box.row()
            row.template_list("GHOST_UL_MeshInfoList", "", props, "found_meshes", props, "found_meshes_index")
            
            if len(props.found_meshes) > 0:
                if props.found_meshes_index >= len(props.found_meshes):
                    props.found_meshes_index = len(props.found_meshes) - 1
                    
                if props.found_meshes_index >= 0:
                    item = props.found_meshes[props.found_meshes_index]
                    
                    col = box.column(align=True)
                    row = col.row(align=True)
                    
                    op = row.operator("ghost.show_textures", text="Show Textures", icon='TEXTURE')
                    op.mesh_hash = item.mesh_hash
                    op.mesh_xmesh_path = props.filepath 
                    
                    op_copy = row.operator("ghost.copy_hash", text="", icon='COPY_ID')
                    op_copy.hash_to_copy = item.mesh_hash
                    
                    col.separator()
                    col.operator("ghost.add_replacement", text="Add to Inject List", icon='ADD')

            box.separator()
            
            box.prop(props, "import_skeleton")
            
            row = box.row(align=True)
            row.scale_y = 1.2
            row.operator("ghost.import_selected", text="Import Checked", icon='IMPORT')
            row.operator("ghost.import_all", text="Import All", icon='IMPORT')

        layout.separator()
        
        # export
        layout.label(text="Injector / Modding", icon='EXPORT')
        box = layout.box()
        
        # auto match
        col = box.column(align=True)
        col.label(text="Auto-Inject (Batch):")
        row = col.row(align=True)
        row.prop(props, "auto_match_lod", text="LOD ID")
        row.operator("ghost.auto_match", text="Auto Match Selected", icon='SHADERFX')
        
        box.separator()
        
        col = box.column(align=True)
        col.label(text="Texture Assets (Optional):")
        col.prop(props, "texture_root_path", text="")
        
        row = box.row()
        row.template_list("GHOST_UL_ReplacementList", "", props, "replacements", props, "replacements_index")
        
        row = box.row(align=True)
        row.operator("ghost.remove_replacement", text="Remove Selected", icon='REMOVE')
        
        if len(props.replacements) > 0 and props.replacements_index >= 0:
            rep_item = props.replacements[props.replacements_index]
            col = box.column(align=True)
            col.separator()
            col.label(text="Tools for Selected:")
            
            if rep_item.new_mesh:
                op = col.operator("ghost.snap_to_bone", text="Snap to Bone (Auto-Rig)", icon='BONE_DATA')
                op.target_object_name = rep_item.new_mesh.name
            else:
                col.label(text="Select a Mesh above!", icon='ERROR')

        box.separator()
        row = box.row()
        row.scale_y = 1.5
        row.operator("ghost.inject_meshes", text="Inject / Export Mod", icon='EXPORT')

        #mod combiner
        layout.label(text="Mod Combiner", icon='GROUP')
        box = layout.box()
        box.label(text="1. Original XMesh must be selected above!", icon='INFO')
        
        row = box.row()
        row.template_list("GHOST_UL_ModFileList", "", props, "mod_files", props, "mod_files_index")
        
        col = box.column(align=True)
        col.operator("ghost.add_mod_file", icon='ADD', text="Add XPPS Mod")
        col.operator("ghost.clear_mod_files", icon='X', text="Clear")
        
        box.separator()
        box.operator("ghost.scan_conflicts", text="2. Scan for Changes", icon='VIEWZOOM')
        
        if len(props.conflicts) > 0:
            box.label(text="3. Resolve Conflicts:", icon='ERROR')
            row = box.row()
            row.template_list("GHOST_UL_ConflictList", "", props, "conflicts", props, "conflicts_index")
            
            if props.conflicts_index >= 0:
                item = props.conflicts[props.conflicts_index]
                if len(item.variants) > 1:
                    row = box.row()
                    row.operator("ghost.switch_variant", text=f"Switch Version (Current: {item.variants[item.selected_variant_index].name})", icon='FILE_REFRESH')
        
        box.separator()
        box.operator("ghost.combine_final", text="4. Create Merged Mod", icon='EXPORT')