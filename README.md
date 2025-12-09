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

### Input Parameters – Detailed Description

**Input Centreline Features**  
Polyline layer representing the centrelines of proposed detainment bunds / stopbanks.  
Each feature is assumed to run along the crest of a single bund (or a logical section of bund).

---

**Centreline ID Field**  
Text or numeric field used to uniquely identify each bund.  
This ID is copied into outputs (footprints, volumes table, CSV) so you can trace results back to the original design line.

---

**Design Height Mode**  
Controls how crest elevations are defined along each centreline. One of:

- **Use Field** – a single absolute height (e.g. RL) taken from an attribute field for each feature.  
- **Use Start/End** – linearly interpolated crest height from a start value to an end value along the line.  
- **Use HAG Field** – height “above ground” stored in a field; tool adds this to the DEM.  
- **Use HAG Value** – single constant height above existing ground used for all centrelines.

Choose the mode that matches the design information you actually have.

---

**Design Height Field (m)**  
Used only when **Design Height Mode = Use Field**.  
Numeric field (e.g. `Level`, `DesignRL`) that stores the absolute crest elevation in metres for each centreline feature.

---

**Start Crest Height (m)**  
Used only when **Design Height Mode = Use Start/End**.  
Absolute crest height (metres) at the *start* of each centreline (line’s from-node).  
The tool interpolates from this value to the End Crest Height along the line.

---

**End Crest Height (m)**  
Used only when **Design Height Mode = Use Start/End**.  
Absolute crest height (metres) at the *end* of each centreline (line’s to-node).  
The tool creates a smooth longitudinal gradient between Start and End.

---

**HAG Field (m)**  
Used only when **Design Height Mode = Use HAG Field**.  
Numeric field containing **height above ground** (HAG) values per feature.  
The tool samples the DEM under the centreline, then adds the HAG value to build the crest elevation.

---

**HAG Value (m)**  
Used only when **Design Height Mode = Use HAG Value**.  
Single constant height above existing ground applied to all centrelines (e.g. “build all crests 1.0 m above current ground”).  
Useful for quick concept design or sensitivity testing.

---

**Input DEM**  
Ground surface raster representing existing terrain (1 m LiDAR DEM recommended).  
Must be in the same vertical datum as the design elevations. This surface is used both to build HAG-based crests and to compute fill depths.

---

**Crest Width (m)**  
Flat width of the bund crest in metres (e.g. 3.0–5.0 m).  
The tool uses this to define the core “flat” region around the centreline before batter slopes start.

---

**Maintain Crest Width (True/False)**  
If **True**: forces the full crest width to be preserved even where the existing ground surface intersects the design plane.  
- Inside the crest buffer, the crest elevation is enforced.  
- Outside, the design is allowed to blend down to ground.  

If **False**: the crest may be slightly eroded where DEM is higher than the theoretical batter.

---

**Batter Slope H:V**  
Horizontal-to-vertical batter slope ratio (H per 1 V).  
For example:
- `3` → 3H:1V  
- `2.5` → 2.5H:1V  

This controls how quickly the bund drops from crest to toe.

---

**End Taper Length (m)**  
Length over which the bund is tapered down to existing ground at each end.  
- `0` → vertical “end wall” (no taper)  
- `> 0` → smooth transition back to ground over the specified distance (e.g. 10–20 m).

---

**Vertical Datum Label**  
Short text label describing the vertical datum of both DEM and design heights (e.g. `NZVD2016`, `Moturiki`).  
Used for documentation and added into outputs (volume tables, footprints, multipatch).

---

**Append Datum Label to Output Names**  
If **True**: appends `_<datum>` to output dataset names (e.g. `_BundSurface_moturiki`).  
Helps avoid confusion when working with multiple datums or alternative surfaces.

---

**Topsoil Stripping Depth (m)**  
Thickness of material (in metres) to be stripped before bund construction (e.g. 0.10–0.30 m).  
The tool multiplies this depth by footprint area to calculate a separate **stripping volume** for costing.

---

**Output Workspace (File GDB)**  
Target geodatabase where all outputs will be written (rasters, feature classes, tables).  
Recommended: use a dedicated FGDB per scenario or design iteration.

---

**Output Merged Design Surface Raster**  
If **True**: writes a single merged design surface raster for all processed centrelines.  
Useful for viewing the full bund system as one continuous surface and for DEM–design comparisons.

---

**Output Per-Feature Surfaces**  
If **True**: optionally writes per-feature design surfaces (one raster per centreline).  
Useful for debugging or detailed per-bund analysis, but increases processing time and storage.

---

**Output Difference (Fill) Raster**  
If **True**: writes a raster of **fill thickness** (design surface minus DEM).  
Positive values indicate required fill; NoData or zero = no bund fill.

---

**Output 3D Multipatch Geometry**  
If **True** and 3D Analyst is available: builds a 3D multipatch bund object by extruding between:
- A TIN built from the DEM, and  
- A TIN built from the design surface.  

This is ideal for 3D visualisation, export to other 3D tools, or scene-based communication.

---

**Create Bund Footprint Polygon Layer**  
If **True**: creates a polygon feature class representing the **bund toe footprint** (area where fill > 0).  
Includes fields:
- Centreline ID  
- Area in hectares  
- Vertical datum  

---

**Output CSV Summary**  
If **True**: writes a summary table *and* CSV with:
- One row per centreline  
- A final `__TOTAL__` row with merged area and volumes  

Contains fill area, fill volume, strip volume, geometry parameters, and datum information.

---

**Treat Overlapping Centrelines as One Bund**  
If **True**: dissolves centrelines by the ID field and processes each dissolved line as a single bund.  
Also saves a copy of merged centrelines as `<InputName>_Centrelines_MergedByID` in the output workspace.  
Use this when you have segmented lines that logically represent one continuous bund.

---

**Processing Mask Buffer Extra (m)**  
Extra distance added around each centreline when creating the local processing mask.  
This ensures all batter slopes, tapers, and smoothing effects are safely contained within the mask.  
Defaults to something like 20 m; increase for very wide batters or if you see clipping at the edges.


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
