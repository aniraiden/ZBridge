# ZBridge — ZBrush Cross-Version Migration Plugin Development Document

## 1. Project Goals

ZBridge is a helper plugin for **migrating projects between different ZBrush versions**.

> **Sole goal: transfer Tools created in newer ZBrush versions to older ones with minimal loss.**

E.g. ZBrush 2026 → 2024, ZBrush 2027 → 2025, any newer version → any older version.

This project is **not**: a GoZ replacement, a mesh import/export tool, a third-party bridge tool, a ZTL parser, or a ZTL downgrader.

The project is built entirely on the **official GoZ SDK**.

## 2. Design Principles

1. **Never parse ZTL/ZPR.** All data comes from the current Tool, the GoZ SDK, and the plugin's own records.
2. **GoZ handles the Mesh.** Mesh, UV, Polypaint, Texture, Material and Geometry are all left to GoZ; the plugin never saves them redundantly.
3. **The manifest only stores what GoZ cannot express.** e.g. SubTool order, Folder, Visible, Active Tool, plugin version, etc. — no duplicated records.
4. **The Recovery Engine is the core of the plugin.** GoZ restores the Mesh; the Recovery Engine restores the Tool state.

## 3. Overall Flow

```text
ZBrush 2026 --Export--> export directory (GoZ + manifest) --Import--> ZBrush 2024
```

The whole flow does not require both ZBrush versions to be open at the same time.

## 4. Plugin Features

The plugin has only two features: **Export** and **Import** — no other complex functionality.

## 5. Export Module

Flow: read the current Tool → iterate all SubTools → export GoZ → generate manifest.

Export responsibilities: export GoZ, record restoration information.

## 6. Import Module

Flow: choose the export directory → read manifest → import GoZ in a loop → Recovery Engine restores the Tool.

Import responsibilities: import GoZ, invoke the recovery engine.

## 7. Project Format

The export output is a **directory** (no packaging; ZIP can be done manually by the user):

```text
export_dir/
├── zbridge_manifest.txt   # metadata of all SubTools
├── Body.goz               # named after the subtool
├── Hair.goz
└── ...
```

GoZ files are named after the subtool (`<subtool name>.goz`) and stored flat alongside the manifest.

## 8. manifest

The manifest does not store Mesh; it only stores state that GoZ cannot express. Each record has 9 pipe-separated fields, null-terminated:

```text
colorize|maxSdiv|curSdiv|subtoolEye|folderEye|isFolder|isOpened|folderName|name\0
```

| Field | Meaning |
|-------|---------|
| colorize | 1 = has vertex color, 0 = none |
| maxSdiv / curSdiv | highest / current subdivision level |
| subtoolEye / folderEye | subtool eye bit (bit0) / folder eye bit (bit1) |
| isFolder / isOpened | is a folder / folder expanded state |
| folderName / name | owning folder name / subtool or folder name |

## 9. Recovery Engine

The Recovery Engine is the most important module of the plugin; it restores:

- Tool name, SubTool names and order
- Folder structure
- Visible state
- Colorize, subdivision level

Any future restoration of Material, Transform, etc. will be implemented in this module.

## 10. Compatibility Layer

On Import, it detects the target version and automatically ignores data that does not exist in older versions, without affecting the import.

## 11. Plugin Modules

The plugin stays minimal:

```text
ZBridge
├── UI                  # two buttons
├── Export              # export GoZ, generate manifest
├── Import              # import GoZ, invoke recovery
├── Recovery Engine     # restore Tool / SubTool state
├── Compatibility Layer # handle version differences
└── Manifest            # read/write manifest
```

## 12. Development Phases

| Phase | Content | Status |
|-------|---------|--------|
| MVP | GoZ export/import, Tool/SubTool, names, order | ✅ 0.1.0 |
| Phase 2 | Folder, Visible | ✅ 0.2.0–0.4.0 |
| Phase 3 | Duplicate subtool name check (prerequisite for later features) | ✅ 0.5.0 |
| Planned | Dynamic subdivision preview & attribute restore (8 attrs, manifest ext field) | ✅ 0.6.0 |
| Planned | Color texture restore (re-bind texture, hasTexture/textureFile) | ✅ 0.7.0 |
| Planned | Sculpt layer restore | Pending (0.8.5 in development) |
| Phase 4 | Active Tool, Material, Compatibility Layer | Pending |

> Version policy: bump the version number on each new feature release (e.g. 0.6.0, 0.7.0…), keeping the previous release archived.

## 13. Project Boundaries

This project explicitly does not handle: ZTL parsing/modification/downgrade, GoZ SDK development, third-party software bridging, mesh editing, or geometry computation.

## 14. Core Idea

Division of responsibility: **GoZ handles geometric data, ZBridge handles project state.**

> Clear separation — no redundant data storage, no ZTL parsing; automatic restoration from newer to older ZBrush versions is achieved solely through the official GoZ SDK.
