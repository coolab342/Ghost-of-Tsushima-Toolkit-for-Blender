import bpy
from . import panels, lists

classes = (
    lists.GHOST_UL_MeshInfoList,
    lists.GHOST_UL_ReplacementList,
    lists.GHOST_UL_ModFileList,
    lists.GHOST_UL_ConflictList,
    
    panels.VIEW3D_PT_GhostPanel
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)