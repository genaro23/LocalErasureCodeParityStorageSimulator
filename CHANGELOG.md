# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1] - 2024-02-05 (Stable Release)

### Fixed
- **Critical:** Resolved "Python integer 256 out of bounds for uint8" overflow error
- Changed modulo operation from 256 to 255 in global parity weight calculation
- Replaced `%` operator with `np.remainder()` for better numpy compatibility
- Added explicit type casting in all parity calculation functions

### Technical Details
```python
# Before (v3.0) - CAUSED OVERFLOW
weight = np.uint8((drive_id % 256) + 1)  # Could produce 256

# After (v3.1) - FIXED
weight = np.uint8((drive_id % 255) + 1)  # Max value 255
```

### Tested
- Verified on macOS Sonoma
- Tested with files up to 100MB
- Validated all rebuild scenarios
- Confirmed color rendering on multiple platforms

---

## [3.0] - 2024-02-05 (Major Feature Release)

### Added
- **High Availability Mode:** 18% overhead mode using 2 drives per Dbox
- **Hex Viewer:** Right-click any drive to view full contents in hex dump format
- **Rebuild System:** Visual rebuild process showing which drives are read
- **Storage Statistics:** Real-time display of total/used/available storage
- **File Download:** Retrieve and verify stored files after rebuild
- **Enhanced Color Coding:**
  - Yellow (#FFD700) for hot spare drives
  - Blue (#1E90FF) for global parity drives
  - Purple (#9370DB) for local parity drives
- **Rebuild Analytics:** Track and display which drives were read during recovery
- **HA Toggle:** Checkbox to switch between normal and high-availability modes

### Changed
- Renamed "Dnode" to "Dbox" throughout codebase and documentation
- Improved tooltip information with rebuild instructions
- Enhanced status bar with real-time storage capacity
- Optimized thread handling with daemon threads

### GUI Improvements
- Added "Rebuild Drives" button with online/spare options
- Added "Download File" button for data verification
- Added "Dbox HA Mode" checkbox in control panel
- Storage statistics bar showing capacity usage
- Color-coded legend with visual swatches
- Right-click context menu for hex viewing

---

## [2.1] - 2024-02-05

### Fixed
- Improved color rendering on macOS
- Fixed uint8 overflow in weighted parity calculations (partial fix)
- Enhanced visual feedback with frame borders

### Changed
- Implemented explicit `np.uint8()` casting
- Used `astype(np.uint16)` for intermediate calculations
- Added color-coded legend panel

---

## [2.0] - 2024-02-05 (Major Architecture Update)

### Added
- **Expanded Capacity:** Increased from 146 to 484 drives
- **Dnode Organization:** 11 Dnodes with 44 drives each
- **Multi-File Support:** Accept and store multiple files with metadata
- **Hex Preview:** Display first 4 bytes in hex on each drive button
- **Dnode Management:** Enable/disable entire 44-drive groups
- **File Metadata System:** Headers for file boundaries and reconstruction

### Changed
- Per-Dnode configuration: 38 data + 3 local parity + 1 global parity + 2 spares
- Total: 418 data + 33 local parity + 11 global parity + 22 hot spares
- Overhead increased to ~8.5% (from 2.8%)
- 3-column grid layout for 11 Dnodes

### Technical
- Implemented file concatenation with boundary markers
- Added Dnode-level integrity checking
- Optimized drive distribution algorithm
- Enhanced failure tolerance analysis

---

## [1.1] - 2024-02-05

### Fixed
- **macOS Compatibility:** Fixed button color highlighting not showing on macOS
- Replaced `tk.Button` with `tk.Label` for better color support
- Added drive container frames with colored borders

### Changed
- Implemented specific hex color codes instead of named colors
- Used `#90EE90` (light green) for online drives
- Used `#FF4444` (red) for offline drives
- Added `update_idletasks()` for immediate visual updates
- Implemented `bind("<Button-1>")` for click events instead of command parameter

---

## [1.0] - 2024-02-05 (Initial Release)

### Added
- Initial implementation of erasure coded storage system
- 142 data drives + 4 parity drives (146 total)
- Two-level erasure coding with 10 local groups (14 drives each)
- 10 local parity drives (1 per group)
- 2 global parity drives
- 2 hot spares
- Tkinter GUI with drive visualization
- Drive status toggling (online/offline)
- Usage percentage display on drive buttons
- Integrity checking
- Basic rebuild functionality

### Technical Specifications
- Drive size: 1MB per drive
- Chunk size: 4KB
- Overhead: 2.8% (4/142)
- Single file input support
- XOR parity calculations

### Known Limitations
- Button colors not displaying properly on macOS
- Single file input only
- No hex preview of drive contents
- No rebuild visualization
- Limited failure scenario testing

---

## Version Comparison

| Feature | v1.0 | v1.1 | v2.0 | v2.1 | v3.0 | v3.1 |
|---------|------|------|------|------|------|------|
| Drives | 146 | 146 | 484 | 484 | 484 | 484 |
| Multi-File | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| macOS Colors | ❌ | ✅ | ⚠️ | ✅ | ✅ | ✅ |
| Hex Preview | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Hex Viewer | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| HA Mode | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Rebuild Viz | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Storage Stats | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Uint8 Bug | N/A | N/A | ❌ | ⚠️ | ❌ | ✅ |

---

## Upgrade Guide

### From v1.x to v2.x
1. Backup any existing storage directory
2. Update code to new version
3. Re-initialize storage (drive count changed)
4. Note: Previous data cannot be migrated

### From v2.x to v3.x
1. Update to v3.0 or v3.1
2. Existing storage files compatible
3. New features available immediately
4. Rebuild any failed drives to ensure compatibility

### From v3.0 to v3.1
1. Simple file replacement
2. Fully backward compatible
3. Fixes critical overflow bug
4. Recommended for all users

---

## Breaking Changes

### v2.0
- Complete storage architecture change
- Incompatible with v1.x storage files
- Must reinitialize and reload data

### v3.0
- Renamed "Dnode" to "Dbox" (terminology only)
- Storage format unchanged
- No migration needed

---

[3.1]: https://github.com/YOUR_USERNAME/erasure-storage-system/releases/tag/v3.1
[3.0]: https://github.com/YOUR_USERNAME/erasure-storage-system/releases/tag/v3.0
[2.1]: https://github.com/YOUR_USERNAME/erasure-storage-system/releases/tag/v2.1
[2.0]: https://github.com/YOUR_USERNAME/erasure-storage-system/releases/tag/v2.0
[1.1]: https://github.com/YOUR_USERNAME/erasure-storage-system/releases/tag/v1.1
[1.0]: https://github.com/YOUR_USERNAME/erasure-storage-system/releases/tag/v1.0
