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
import shutil
import random
from . import importer, tex_db, injector, texture_manager, combiner


def estimate_game_vertices(obj):
    #counts vertices on the evaluated mesh to guess if it fits the buffer
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    count = len(eval_obj.data.vertices)
    print(f"[Ghost] {obj.name}: {count} vertices")
    return count

def auto_find_files(xmesh_path):
    #tries to locate xpps and db files based on xmesh location
    folder = os.path.dirname(xmesh_path)
    fname = os.path.splitext(os.path.basename(xmesh_path))[0]
    
    xpps_path = os.path.join(folder, fname + ".xpps")
    if not os.path.exists(xpps_path):
        xpps_path = os.path.join(folder, "hero.xpps")
        
    db_path = os.path.join(folder, "game.sprig.texmeshman")
    return xpps_path, db_path


class GHOST_OT_AutoMatch(bpy.types.Operator):
    bl_idname = "ghost.auto_match"
    bl_label = "Auto Match Selected"
    
    def execute(self, context):
        props = context.scene.ghost_tool
        selected_objs = [o for o in context.selected_objects if o.type == 'MESH']
        
        if not selected_objs:
            self.report({'WARNING'}, "Select Blender objects first!")
            return {'CANCELLED'}
            
        if len(props.found_meshes) == 0:
            self.report({'WARNING'}, "Scan an XMesh file first!")
            return {'CANCELLED'}

        target_lod = props.auto_match_lod
        
        available_slots = []
        for i, item in enumerate(props.found_meshes):
            if item.lod == target_lod:
                available_slots.append({
                    'index': i,
                    'capacity': item.vertex_count,
                    'hash': item.mesh_hash,
                    'used': False
                })
        
        if not available_slots:
            self.report({'ERROR'}, f"No submeshes found with LOD {target_lod}")
            return {'CANCELLED'}
            
        # sort slots by size (small to large)
        available_slots.sort(key=lambda x: x['capacity'])
        
        custom_meshes = []
        for obj in selected_objs:
            v_count = estimate_game_vertices(obj)
            custom_meshes.append({'obj': obj, 'count': v_count})
            
        # match logic, fit largest object into smallest available slot that fits it
        custom_meshes.sort(key=lambda x: x['count'], reverse=True)
        
        matches = []
        unmatched = []
        
        for custom in custom_meshes:
            best_slot = None
            for slot in available_slots:
                if not slot['used'] and slot['capacity'] >= custom['count']:
                    best_slot = slot
                    break
            
            if best_slot:
                best_slot['used'] = True
                matches.append((custom, best_slot))
            else:
                unmatched.append(custom)
                
        for custom, slot in matches:
            existing = next((r for r in props.replacements if r.original_hash == slot['hash']), None)
            if existing:
                existing.new_mesh = custom['obj']
            else:
                item = props.replacements.add()
                item.original_hash = slot['hash']
                item.new_mesh = custom['obj']

        for o in context.selected_objects: 
            o.select_set(False)

        for u in unmatched: 
            u['obj'].select_set(True)
            
        msg = f"Matched {len(matches)} objects."
        if unmatched:
            self.report({'WARNING'}, f"{msg} Failed to fit {len(unmatched)} high-poly objects.")
        else:
            self.report({'INFO'}, msg)
            
        return {'FINISHED'}

class GHOST_OT_AddModFile(bpy.types.Operator):
    bl_idname = "ghost.add_mod_file"
    bl_label = "Add XPPS File"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.xpps", options={'HIDDEN'})
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        item = context.scene.ghost_tool.mod_files.add()
        item.filepath = self.filepath
        return {'FINISHED'}

class GHOST_OT_ClearModFiles(bpy.types.Operator):
    bl_idname = "ghost.clear_mod_files"
    bl_label = "Clear"
    def execute(self, context):
        context.scene.ghost_tool.mod_files.clear()
        context.scene.ghost_tool.conflicts.clear()
        return {'FINISHED'}

class GHOST_OT_ScanConflicts(bpy.types.Operator):
    bl_idname = "ghost.scan_conflicts"
    bl_label = "Scan for Changes"
    
    def execute(self, context):
        props = context.scene.ghost_tool
        orig_file = bpy.path.abspath(props.filepath)
        
        xpps, _ = auto_find_files(orig_file)
        db_path = bpy.path.abspath(props.tex_db_path)
        
        files = [item.filepath for item in props.mod_files]
        
        conflicts_data, _, _ = combiner.scan_for_conflicts(xpps, files)
        
        # ensure db is loaded for names
        tex_db.DB.load(db_path)
        
        props.conflicts.clear()
        
        for h, mods in conflicts_data.items():
            item = props.conflicts.add()
            item.hash_str = f"{h:X}"
            item.mesh_name = tex_db.DB.get_name(h)
            
            for m in mods:
                var = item.variants.add()
                var.name = m.filename
                var.filepath = m.filepath
                var.vert_count = m.modifications[h]['vert_count']
                var.scale = m.modifications[h]['scale']
                var.warn_verts = m.modifications[h]['warn_verts']
            
        self.report({'INFO'}, f"Scan complete. Found {len(conflicts_data)} conflicts.")
        return {'FINISHED'}

class GHOST_OT_SwitchVariant(bpy.types.Operator):
    bl_idname = "ghost.switch_variant"
    bl_label = "Switch Version"
    
    def execute(self, context):
        props = context.scene.ghost_tool
        if props.conflicts_index >= 0 and len(props.conflicts) > 0:
            item = props.conflicts[props.conflicts_index]
            if len(item.variants) > 1:
                item.selected_variant_index = (item.selected_variant_index + 1) % len(item.variants)
        return {'FINISHED'}

class GHOST_OT_CombineFinal(bpy.types.Operator):
    bl_idname = "ghost.combine_final"
    bl_label = "Combine & Export"
    
    def execute(self, context):
        props = context.scene.ghost_tool
        orig_file = bpy.path.abspath(props.filepath)
        
        files = [item.filepath for item in props.mod_files]
        xpps, _ = auto_find_files(orig_file)
        
        _, clean_data, _ = combiner.scan_for_conflicts(xpps, files)
        
        final_map = {}
        
        for h, mod_state in clean_data.items():
            final_map[h] = mod_state.filepath
            
        for item in props.conflicts:
            h = int(item.hash_str, 16)
            if item.selected_variant_index < len(item.variants):
                final_map[h] = item.variants[item.selected_variant_index].filepath
                
        out_dir = os.path.dirname(orig_file)
        msg = combiner.combine_with_resolution(orig_file, out_dir, final_map, files)
        
        self.report({'INFO'}, msg)
        return {'FINISHED'}

class GHOST_OT_ShowTextures(bpy.types.Operator):
    bl_idname = "ghost.show_textures"
    bl_label = "Textures"
    
    mesh_hash: bpy.props.StringProperty()
    mesh_xmesh_path: bpy.props.StringProperty()
    
    text_lines = [] 

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        props = context.scene.ghost_tool
        
        xmesh_path = bpy.path.abspath(self.mesh_xmesh_path)
        if not xmesh_path or not os.path.exists(xmesh_path):
            xmesh_path = bpy.path.abspath(props.filepath)
            
        if not xmesh_path or not os.path.exists(xmesh_path):
             self.report({'ERROR'}, "XMesh file not found.")
             return {'CANCELLED'}

        xpps_path, db_path = auto_find_files(xmesh_path)
        
        if not os.path.exists(db_path):
            self.report({'ERROR'}, f"DB 'game.sprig.texmeshman' missing.")
            return {'CANCELLED'}
        
        try:
            m_hash_int = int(self.mesh_hash, 16)
            self.text_lines = tex_db.find_materials(xpps_path, m_hash_int, db_path)
            if not self.text_lines:
                self.text_lines = ["No textures found"]
        except Exception as e:
            self.text_lines = [f"Error: {str(e)}"]
            
        return context.window_manager.invoke_props_dialog(self, width=600)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Textures for Hash {self.mesh_hash}:", icon='TEXTURE')
        
        if self.text_lines and "Error" not in self.text_lines[0]:
            all_str = "\n".join(self.text_lines)
            row = layout.row()
            op = row.operator("ghost.copy_hash", text="Copy List to Clipboard", icon='DUPLICATE')
            op.hash_to_copy = all_str
            layout.separator()

        box = layout.box()
        col = box.column()
        for line in self.text_lines:
            row = col.row(align=True)
            row.label(text=line)
            if "Error" not in line:
                op = row.operator("ghost.copy_hash", text="", icon='COPY_ID')
                op.hash_to_copy = line

class GHOST_OT_CopyHash(bpy.types.Operator):
    bl_idname = "ghost.copy_hash"
    bl_label = "Copy Hash"
    hash_to_copy: bpy.props.StringProperty()
    def execute(self, context):
        context.window_manager.clipboard = self.hash_to_copy
        self.report({'INFO'}, "Copied to Clipboard")
        return {'FINISHED'}

class GHOST_OT_SnapToBone(bpy.types.Operator):
    bl_idname = "ghost.snap_to_bone"
    bl_label = "Snap Mesh to Bone"
    bl_options = {'REGISTER', 'UNDO'}
    
    target_object_name: bpy.props.StringProperty()
    bone_name: bpy.props.StringProperty(name="Bone Name", default="Bone_0")
    
    def execute(self, context):
        obj = bpy.data.objects.get(self.target_object_name)
        if not obj: return {'CANCELLED'}
        
        # clear old groups
        grp = obj.vertex_groups.get(self.bone_name)
        if grp: obj.vertex_groups.remove(grp)
        
        # create new weight group
        grp = obj.vertex_groups.new(name=self.bone_name)
        indices = [v.index for v in obj.data.vertices]
        grp.add(indices, 1.0, 'REPLACE')
        
        # remove others
        for g in obj.vertex_groups:
            if g.name != self.bone_name:
                obj.vertex_groups.remove(g)
                
        self.report({'INFO'}, f"Rigged {obj.name} to {self.bone_name}")
        return {'FINISHED'}
        
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class GHOST_OT_AnalyzeFile(bpy.types.Operator):
    bl_idname = "ghost.analyze_file"
    bl_label = "Scan File"
    
    def execute(self, context):
        props = context.scene.ghost_tool
        path = bpy.path.abspath(props.filepath)
        if not os.path.exists(path): 
            self.report({'ERROR'}, "File not found")
            return {'CANCELLED'}
        
        props.found_meshes.clear()
        props.found_meshes_index = 0  
        
        infos = importer.scan_xmesh(path)
        
        if not infos:
            self.report({'WARNING'}, "No meshes found.")
            return {'CANCELLED'}

        for info in infos:
            item = props.found_meshes.add()
            item.mesh_hash = info["hash"]
            item.lod = info["lod"]
            item.vertex_count = info["verts"]
            item.face_count = info["faces"]
        
        self.report({'INFO'}, f"Scanned {len(infos)} meshes.")
        return {'FINISHED'}

class GHOST_OT_ImportAll(bpy.types.Operator):
    bl_idname = "ghost.import_all"
    bl_label = "Import All"
    def execute(self, context):
        props = context.scene.ghost_tool
        path = bpy.path.abspath(props.filepath)
        db_path = bpy.path.abspath(props.tex_db_path)
        importer.import_selected(context, path, selected_hashes=None, use_skeleton=props.import_skeleton, db_path=db_path)
        return {'FINISHED'}

class GHOST_OT_ImportSelected(bpy.types.Operator):
    bl_idname = "ghost.import_selected"
    bl_label = "Import Checked"
    def execute(self, context):
        props = context.scene.ghost_tool
        path = bpy.path.abspath(props.filepath)
        db_path = bpy.path.abspath(props.tex_db_path)
        hashes = [m.mesh_hash for m in props.found_meshes if m.is_selected]
        
        if not hashes:
            self.report({'WARNING'}, "No meshes selected.")
            return {'CANCELLED'}

        importer.import_selected(context, path, selected_hashes=hashes, use_skeleton=props.import_skeleton, db_path=db_path)
        return {'FINISHED'}

class GHOST_OT_SelectAll(bpy.types.Operator):
    bl_idname = "ghost.select_all"
    bl_label = "Select All"
    action: bpy.props.BoolProperty()
    def execute(self, context):
        for m in context.scene.ghost_tool.found_meshes: m.is_selected = self.action
        return {'FINISHED'}

class GHOST_OT_AddReplacement(bpy.types.Operator):
    bl_idname = "ghost.add_replacement"
    bl_label = "Add to Inject List"
    
    def execute(self, context):
        props = context.scene.ghost_tool
        if props.found_meshes_index < 0 or props.found_meshes_index >= len(props.found_meshes):
             return {'CANCELLED'}

        target_hash = props.found_meshes[props.found_meshes_index].mesh_hash
        item = props.replacements.add()
        item.original_hash = target_hash
        
        if context.active_object and context.active_object.type == 'MESH':
            item.new_mesh = context.active_object
        return {'FINISHED'}

class GHOST_OT_RemoveReplacement(bpy.types.Operator):
    bl_idname = "ghost.remove_replacement"
    bl_label = "Remove"
    def execute(self, context):
        props = context.scene.ghost_tool
        if props.replacements_index >= 0:
            props.replacements.remove(props.replacements_index)
            props.replacements_index = max(0, props.replacements_index - 1)
        return {'FINISHED'}

class GHOST_OT_InjectMeshes(bpy.types.Operator):
    bl_idname = "ghost.inject_meshes"
    bl_label = "Inject / Export Mod"
    
    def execute(self, context):
        props = context.scene.ghost_tool
        
        # check original files
        orig_xmesh_path = bpy.path.abspath(props.filepath)
        if not os.path.exists(orig_xmesh_path): return {'CANCELLED'}
        orig_xpps_path, orig_db_path = auto_find_files(orig_xmesh_path)
        
        if not os.path.exists(orig_xpps_path):
            self.report({'ERROR'}, f"XPPS file not found")
            return {'CANCELLED'}
            
        if len(props.replacements) == 0:
            self.report({'WARNING'}, "No replacements defined.")
            return {'CANCELLED'}

        # create mod folder
        folder = os.path.dirname(orig_xmesh_path)
        fname_no_ext = os.path.splitext(os.path.basename(orig_xmesh_path))[0]
        mod_id = random.randint(10000, 99999)
        mod_folder_name = f"{fname_no_ext}_mod_{mod_id}"
        mod_dir = os.path.join(folder, mod_folder_name)
        
        try: os.makedirs(mod_dir, exist_ok=True)
        except OSError: return {'CANCELLED'}

        # copy original files
        target_xmesh_path = os.path.join(mod_dir, os.path.basename(orig_xmesh_path))
        target_xpps_path = os.path.join(mod_dir, os.path.basename(orig_xpps_path))
        shutil.copy2(orig_xmesh_path, target_xmesh_path)
        shutil.copy2(orig_xpps_path, target_xpps_path)

        success_count = 0
        
        # inject meshes
        for item in props.replacements:
            if not item.new_mesh: continue
            res = injector.inject_mesh(context, item, target_xmesh_path, orig_db_path)
            if res == "SUCCESS": success_count += 1
            else: self.report({'ERROR'}, res)
                
        # copy textures
        tex_root = bpy.path.abspath(props.texture_root_path)
        if tex_root and os.path.exists(tex_root) and os.path.exists(orig_db_path):
            texture_manager.collect_textures_for_mod(
                orig_xpps_path, orig_db_path, props.replacements, tex_root, mod_dir
            )
        
        if success_count > 0:
            self.report({'INFO'}, f"Export complete in {mod_folder_name}")
            bpy.ops.wm.path_open(filepath=mod_dir)
            
        return {'FINISHED'}

# registration list
classes = (
    GHOST_OT_AutoMatch,
    GHOST_OT_AddModFile,
    GHOST_OT_ClearModFiles,
    GHOST_OT_ScanConflicts,
    GHOST_OT_SwitchVariant,
    GHOST_OT_CombineFinal,
    GHOST_OT_ShowTextures,
    GHOST_OT_CopyHash,
    GHOST_OT_SnapToBone,
    GHOST_OT_AnalyzeFile,
    GHOST_OT_ImportAll,
    GHOST_OT_ImportSelected,
    GHOST_OT_SelectAll,
    GHOST_OT_AddReplacement,
    GHOST_OT_RemoveReplacement,
    GHOST_OT_InjectMeshes,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)