# Ghost of Tsushima Blender Tool

![Version](https://img.shields.io/badge/version-1.2.0-blue)
![Blender](https://img.shields.io/badge/Blender-4.0%2B-orange)
![License](https://img.shields.io/badge/License-MIT-green)

**An Inspector, Importer, and Mod Injector for Ghost of Tsushima.**  
Fully integrated into Blender, supporting custom weights, auto-rigging, and texture management.

Created by **Dave349234**.

---

## Support & Updates

If you enjoy this tool and want to support its development:

[![Nexus Mods](https://img.shields.io/badge/Nexus%20Mods-Profile-blue?style=for-the-badge&logo=nexusmods)](https://www.nexusmods.com/profile/Dave349234)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Donate-red?style=for-the-badge&logo=kofi)](https://ko-fi.com/dave349234)

---

## Key Features

- **Importing**: Import `.xmesh` files with all LOD support, Vertex Colors, and UV maps.
- **Skeleton Support**: Imports the game skeleton automatically.
- **Injection**: Inject custom meshes back into the game files. Supports custom Weights Painting and Vertex Groups.
- **Textures**: Automatically finds texture names linked to specific sub-meshes.
- **Texture Manager**: Can copy required texture files from the game dump to your mod folder automatically.
- **Auto-Match**: Batch-assigns multiple Blender objects to game slots based on vertex count (buggy + not really good).
- **Auto-Rig**: "Snap to Bone" feature to rigidly bind accessories (like helmets) to a specific bone without manual painting.
- **Mod Combiner**: Merge multiple mesh mods.

---

## Installation

1. Download the latest release `.zip` file from the **Releases** section on the right.
2. Open Blender (4.0 or higher)
3. Go to **Edit > Preferences > Add-ons**.
4. Click **Install** and select the zip file.
5. Enable the checkbox for **"Import-Export: Ghost of Tsushima Tool"**.

---

## Usage Guide

### 1. Importing Models
1. Open the **"Ghost Tool"** tab in the N-Panel (Right side of 3D View).
2. Click the folder icon to select your `.xmesh` file.
3. Click **Scan Model** to read the file structure.
   - *Note: Ensure the corresponding `hero.xpps` and `game.sprig.texmeshman` files are in the same folder or properly linked.*
4. Select the sub-meshes you want in the list (or use **Select All**).
5. Click **Import Checked** (or **Import All**).
   - If "Import Skeleton" is checked, the mesh will be rigged to an Armature.

### 2. Modding & Injection
1. Create your custom mesh in Blender.
   - You can use custom **Vertex Groups** (named `Bone_0`, `Bone_1`, etc.) for weight painting.
2. Select the original `.xmesh` file in the tool.
3. Select the sub-mesh you want to replace in the UI list.
4. Click **Add to Inject List**.
5. Assign your custom Blender Object to the slot in the "Injector / Modding" panel.
6. (Optional) Set the **Texture Assets Root** path if you want the tool to copy textures for you.
7. Click **Inject / Export Mod**.
   - A new folder with the modded files will be created automatically.

## ⚠️ Important Limitations

Before you start modding, please be aware of these technical constraints:

### 1. File Size Limits (Vertex Count)
This tool works by **injecting** data into pre-allocated game buffers. It does not resize the memory blocks.
*   Your custom mesh **CANNOT** have more vertices or triangles than the original sub-mesh you are replacing.
*   If your mesh is too large, the tool will block the injection to prevent file corruption.
*   **Tip:** Use the *Auto-Match* feature or Blender's *Decimate* modifier to reduce your poly count until it fits.

### 2. Supported Files
*   This tool is for **Character Models** (files typically starting with `hero_...`).

### 3. Tools

#### Texture Inspector
- Select a mesh in the list and click **Show Textures**.
- The tool reads the game database to tell you exactly which texture files (Diff, Norm, Spec) this mesh uses.
- Use the **Copy** buttons to copy filenames to the clipboard.

#### Auto-Match (Batch Processing)
- Useful for LODs or processing many parts at once.
- Select multiple objects in Blender.
- Set the **Target LOD** ID.
- Click **Auto Match Selected**. The tool will try to fit your objects into the game slots based on vertex count capacity.

#### Auto-Rig (Snap to Bone)
- Great for stiff objects like helmets.
- Select your mesh in the Replacement List.
- Enter the bone name (e.g., `Bone_5`) and click **Snap to Bone**.
- The tool creates the vertex group and assigns 100% weight automatically.

### 4. Mod Combiner
Use this if you have multiple mods (from other creators or yourself) that modifed `.xmesh` files. E.g. if you want to combine a costum helmet with costum hair.
1. Select the original (unmodified) `hero.xpps` at the top.
2. Under "Mod Combiner", add the `.xpps` files of the mods you want to merge.
3. Click **Scan for Changes**.
4. If conflicts are found (two mods editing the same mesh hash), resolve them in the list by selecting the desired version.
5. Click **Create Merged Mod**.

---

## License & Permissions

**Copyright (c) 2025 Dave349234**

This project is licensed under the **MIT License**.

**Attribution Requirement:**
You are free to use, modify, and redistribute this software (even commercially). However, you **MUST** explicitly credit the original author (**Dave349234**) and link back to the original [Nexus Mods Profile](https://www.nexusmods.com/profile/Dave349234) or [Ko-fi Page](https://ko-fi.com/dave349234).

See the [LICENSE](https://github.com/coolab342/Ghost-of-Tsushima-Toolkit-for-Blender/blob/main/LICENSE.txt) file for details.

---

*Disclaimer: This tool is not affiliated with Sucker Punch Productions or Sony Interactive Entertainment.*
