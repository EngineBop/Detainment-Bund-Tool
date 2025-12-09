# Detainment Bund 3D Design Tool  
*(BundDesigner v5.2e for ArcGIS Pro)*  

## Overview
The **Detainment Bund 3D Design Tool** is an ArcGIS Pro Python script designed to generate 3D bund geometry, design surfaces, volumetric calculations, and visualisation outputs for detainment bunds and stopbanks.  
Originally built for the **Whakatāne RSS Project**, the tool follows BOPRC Engineering Guidelines for crest widths, batter slopes, end tapers, and stripping depths.

The tool:
- Builds a **3D design surface raster** from polyline centrelines.  
- Produces **fill thickness rasters** showing required earthworks.  
- Generates **footprint polygons** representing bund toes.  
- Outputs **multipatch 3D objects** for visualisation.  
- Adds **per-feature CSV rows + a total summary row** for costing.  
- Supports **4 design modes**:  
  **Use Field**, **Use Start/End**, **Use HAG Field**, **Use HAG Value**.  

---

## Features
- Per-centreline design surfaces and volumes  
- Optional merged design surface  
- Footprint polygons with ID, area, and datum labels  
- 3D multipatch bund solid (TIN-based extrusion)  
- Optional crest-width enforcement  
- Optional smoothing to reduce raster stepping  
- Topsoil stripping volume calculation  
- Support for overlapping centrelines (Merge-by-ID)

---

## Input Parameters (25 total)
1. **Input Centreline Features** — polyline layer  
2. **Centreline ID Field** — field identifying each bund  
3. **Design Height Mode** — one of:  
   - *Use Field*  
   - *Use Start/End*  
   - *Use HAG Field*  
   - *Use HAG Value*  
4. **Design Height Field** (if mode = Use Field)  
5. **Start Crest Height** (if mode = Start/End)  
6. **End Crest Height** (if mode = Start/End)  
7. **HAG Field** (if mode = HAG Field)  
8. **HAG Value** (if mode = HAG Value)  
9. **Input DEM**  
10. **Crest Width (m)**  
11. **Maintain Crest Width (True/False)**  
12. **Batter Slope H:V**  
13. **End Taper Length (m)**  
14. **Vertical Datum Label**  
15. **Append Datum Label to Output Names**  
16. **Topsoil Stripping Depth (m)**  
17. **Output Workspace (File GDB)**  
18. **Output Merged Design Surface Raster**  
19. **Output Per-Feature Surfaces**  
20. **Output Difference (Fill) Raster**  
21. **Output 3D Multipatch Geometry**  
22. **Create Bund Footprint Polygon Layer**  
23. **Output CSV Summary**  
24. **Treat Overlapping Centrelines as One Bund**  
25. **Processing Mask Buffer Extra (m)**  

---

## Outputs
**Raster Layers**
- `*_BundSurface` — design surface raster  
- `*_BundFill` — fill depth raster  

**Vector Layers**
- `*_BundFootprint` — toe polygon with:  
  - CentrelineID  
  - Area_ha  
  - VertDatum  
- `*_BundMultipatch` — 3D bund object (if enabled)

**Tables**
- `*_BundVolumes` — GDB table + CSV:  
  - One row per centreline  
  - Final row = `__TOTAL__`  
  - Includes: FillArea, FillVolume, StripVolume, Mode, CrestWidth, Batter, Datum, etc.

**Optional**
- `*_Centrelines_MergedByID` — persisted dissolved centrelines when “Merge by ID” is switched on.

---

## How the Tool Works (Summary)
1. Buffers each centreline to create a processing area.  
2. Builds crest elevations based on chosen design mode.  
3. Computes batter slopes using Euclidean distance.  
4. Applies optional crest-width protection and smoothing.  
5. Subtracts the DEM from the design surface to get fill depth.  
6. Converts fill raster > polygon to form the footprint.  
7. Calculates:  
   - Fill volume = Σ(depth × cell area)  
   - Strip volume = footprint area × strip depth  
8. Builds merged design/ fill surfaces (if selected).  
9. Generates multipatch geometry using TIN-based extrusion.  
10. Writes CSV and GDB tables with full per-feature stats.

---

## Suggested Workflow
### 1. Prepare Inputs
- Clean centreline layer  
- Ensure DEM has same vertical datum as design heights  
- Check ID fields for duplicates  

### 2. Run the Tool
- Pick Design Mode  
- Set crest width, batter, taper  
- Choose whether to maintain crest width  
- Choose output workspace (GDB recommended)  
- Enable or disable optional outputs  

### 3. Review Outputs
- Inspect `BundSurface` and `BundFill`  
- Check footprint alignment  
- Load multipatch in a 3D Scene (ArcGIS Pro)  
- Validate volumes in the CSV  

---

## Visualisation Tips
- Use **Drape (Interpolate Shape)** on the footprint polygon for clean scene rendering.  
- Turn on **Edges = Visible** for multipatches to inspect crest and batters.  
- Export multipatch to OBJ/DAE for 12d, Civil 3D, Blender, or Unreal Engine.

---

## Quality Control (Recommended)
### DEM Accuracy Test  
- Perturb DEM by ±0.15 m (RMSE)  
- Re-run tool → compare volume differences  

### Pixelation Test  
- Resample DEM to 0.5 m and 2 m  
- Compare with baseline volumes  

### TIN Method Cross-Check  
- Convert DEM & design surfaces to TIN  
- Use **Surface Difference** to confirm raster-based volumes  

**Typical uncertainty for NZ 1 m DEM:**  
**±10–15%** of total fill volume.

---

## Version History
| Version | Notes |
|---------|-------|
| **v5.2e** | Stable release with: per-feature CSV rows, totals row, crest smoothing, footprint persistence, robust multipatch creation, dissolved centrelines output. |

---

## Author
**Dan Van Nistelrooy**  
Bay of Plenty Regional Council  
Engineering & GIS Development  
2025

---

## License
Internal BOPRC use only.  
Redistribution requires written approval.  
© 2025 Bay of Plenty Regional Council.
