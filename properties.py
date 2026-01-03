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


class GHOST_ModVariant(bpy.types.PropertyGroup):

    name: bpy.props.StringProperty() 
    filepath: bpy.props.StringProperty() 
    
    vert_count: bpy.props.IntProperty()
    scale: bpy.props.FloatProperty()
    warn_verts: bpy.props.BoolProperty()

class GHOST_ConflictItem(bpy.types.PropertyGroup):
    hash_str: bpy.props.StringProperty()
    mesh_name: bpy.props.StringProperty() 
    
    variants: bpy.props.CollectionProperty(type=GHOST_ModVariant)
    selected_variant_index: bpy.props.IntProperty(name="Select Version", default=0)

class GHOST_ModFileItem(bpy.types.PropertyGroup):
    filepath: bpy.props.StringProperty(name="Path")

class GHOST_MeshInfoItem(bpy.types.PropertyGroup):
    is_selected: bpy.props.BoolProperty(name="Select", default=True)
    mesh_hash: bpy.props.StringProperty(name="Hash")
    lod: bpy.props.IntProperty(name="LOD")
    vertex_count: bpy.props.IntProperty(name="Vertices")
    face_count: bpy.props.IntProperty(name="Triangles")

class GHOST_ReplacementItem(bpy.types.PropertyGroup):
    # links a game hash to a blender object for injection
    original_hash: bpy.props.StringProperty(name="Original Hash")
    new_mesh: bpy.props.PointerProperty(
        name="New Mesh", 
        type=bpy.types.Object, 
        description="Your custom Blender mesh"
    )

class GHOST_SceneProperties(bpy.types.PropertyGroup):
    # main container for all tool settings
    # attached to bpy.types.Scene
    
    filepath: bpy.props.StringProperty(
        name="XMesh File", 
        description="Select .xmesh file", 
        subtype='FILE_PATH'
    )
    
    texture_root_path: bpy.props.StringProperty(
        name="Texture Assets Root", 
        description="Folder containing gapack_bitmaps_* folders", 
        subtype='DIR_PATH'
    )

    tex_db_path: bpy.props.StringProperty(
        name="TexMeshMan DB", 
        description="Select game.sprig.texmeshman file", 
        subtype='FILE_PATH',
        default="//game.sprig.texmeshman"
    )

    #auto match settings
    auto_match_lod: bpy.props.IntProperty(name="Target LOD", default=1536)
    
    # import settings
    import_skeleton: bpy.props.BoolProperty(name="Import Skeleton", default=True)
    search_filter: bpy.props.StringProperty(name="Search", description="Filter by Hash")
    
    # lists
    found_meshes: bpy.props.CollectionProperty(type=GHOST_MeshInfoItem)
    found_meshes_index: bpy.props.IntProperty()
    
    replacements: bpy.props.CollectionProperty(type=GHOST_ReplacementItem)
    replacements_index: bpy.props.IntProperty()

    mod_files: bpy.props.CollectionProperty(type=GHOST_ModFileItem)
    mod_files_index: bpy.props.IntProperty()
    
    conflicts: bpy.props.CollectionProperty(type=GHOST_ConflictItem)
    conflicts_index: bpy.props.IntProperty()

classes = (
    GHOST_ModVariant,
    GHOST_ConflictItem,
    GHOST_ModFileItem,
    GHOST_MeshInfoItem,
    GHOST_ReplacementItem,
    GHOST_SceneProperties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.ghost_tool = bpy.props.PointerProperty(type=GHOST_SceneProperties)

def unregister():
    del bpy.types.Scene.ghost_tool
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)