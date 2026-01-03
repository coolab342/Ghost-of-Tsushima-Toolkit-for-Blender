# -----------------------------------------------------------------------------------
# Ghost of Tsushima Blender Tool
# Copyright (c) 2025 Dave349234
#
# AUTHOR: Dave349234
# NEXUS MODS: https://www.nexusmods.com/profile/Dave349234
# KO-FI:      https://ko-fi.com/dave349234
#
# LICENSE & PERMISSIONS:
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software.
#
# ATTRIBUTION REQUIREMENT:
# If you use, modify, or redistribute this code (commercially or otherwise),
# you MUST explicitly credit the original author "Dave349234" and provide a
# link to the original profile (Nexus Mods or Ko-fi).
#
# If you find this tool useful for your workflow or projects, please consider
# supporting the development via Ko-fi. Every donation is appreciated!
# -----------------------------------------------------------------------------------

bl_info = {
    "name": "Ghost of Tsushima Tool",
    "author": "Dave349234",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > N-Panel > Ghost Tool",
    "description": "Inspector, Importer, and Mod Injector for Ghost of Tsushima",
    "category": "Import-Export",
    "doc_url": "https://ko-fi.com/dave349234",
    "tracker_url": "https://www.nexusmods.com/profile/Dave349234",    
}

import bpy
import importlib

from . import (
    utils,
    tex_db,
    properties,
    importer,
    injector,
    texture_manager,
    combiner,
    operators,
    ui
)

modules = [
    utils,
    tex_db,
    properties,
    importer,
    injector,
    texture_manager,
    combiner,
    operators,
    ui
]

def register():
    for m in modules:
        importlib.reload(m)
    
    properties.register()
    operators.register()
    ui.register()
    
    pass

def unregister():
    ui.unregister()
    operators.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()