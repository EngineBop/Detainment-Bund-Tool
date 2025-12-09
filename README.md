# Detainment Bund 3D Design Tool  
**BundDesigner v5.2e — ArcGIS Pro (Spatial Analyst + 3D Analyst)**  

[![Status: Stable](https://img.shields.io/badge/Status-Stable-brightgreen)](#)  
[![ArcGIS Pro](https://img.shields.io/badge/ArcGIS%20Pro-3.x-blue)](#)  
[![Python](https://img.shields.io/badge/Python-3.9+-yellow)](#)  
[![License: MIT](https://img.shields.io/badge/License-MIT-purple)](#)  

A specialised ArcGIS Pro tool for generating **3D detainment bund designs**, **fill volumes**, **footprints**, **surface rasters**, and **optional 3D multipatch solids**.  
Ideal for **concept design, rapid alignment testing, early-stage costing, flood mitigation planning, and visualisation**.

---

# 📑 Table of Contents

- [1. Overview](#1-overview)  
- [2. What the Tool Produces](#2-what-the-tool-produces)  
- [3. Typical Use Cases](#3-typical-use-cases)  
- [4. Installation](#4-installation)  
- [5. Input Parameters (Detailed)](#5-input-parameters-detailed)  
- [6. Output Datasets Explained](#6-output-datasets-explained)  
- [7. Quality Control / QA Workflow](#7-quality-control--qa-workflow)  
- [8. Accuracy, Limitations & Expected Error](#8-accuracy-limitations--expected-error)  
- [9. Repository Structure](#9-repository-structure)  
- [10. Licensing](#10-licensing)  
- [11. Support](#11-support)  

---

# 1. Overview

> **Purpose:**  
> This tool provides *fast, repeatable, screening-level* 3D design and volume estimation for detainment bunds and stopbanks. It is designed to rapidly test alignments, crest heights, batter configurations, and earthwork quantities — all using a 1 m DEM or similar ground model.

⚠️ **Important Engineering Note:**  
This tool **does not** replace detailed design workflows in 12d, Civil 3D or full geotechnical assessment.  
It is intended for **early planning**, **concept design**, **cost estimation**, **flood model pre-processing**, and **scenario comparison**.

---

# 2. What the Tool Produces

### ✔ **Bund Surface Raster** (`*_BundSurface_<datum>`)
A new elevation surface representing the **bund burnt into the DEM**.  
This is your “if the bund were built today, what would the ground look like?” raster.

### ✔ **Bund Fill Raster** (`*_BundFill_<datum>`)
A raster of **fill thickness** (design surface minus DEM).  
Shows where and how much material is needed.

### ✔ **Bund Footprint Polygon** (`*_BundFootprint_<datum>`)
Toe-to-toe footprint of each bund.  
Attributes include:
- Centreline ID  
- Area (ha)  
- Vertical datum  

### ✔ **Volume Table + CSV** (`*_BundVolumes_<datum>`)
Contains:
- Fill volume  
- Fill area  
- Strip volume  
- Crest parameters  
- Batter slope  
- Height mode  
- And a final **TOTALS** row  

### ✔ **Multipatch Solid (optional)** (`*_BundMultipatch_<datum>`)
A 3D solid suitable for:
- ArcGIS Pro Scene  
- Web Scene / AGOL  
- Unreal Engine  
- Blender  
- Civil 3D import (via multipatch → mesh)  

---

# 3. Typical Use Cases

🎯 **Concept stopbank & bund design**  
🎯 **Scenario & option testing (change height, change alignment)**  
🎯 **Budget-level earthworks estimates**  
🎯 **Flood-model pre-processing (burn bunds into DEM)**  
🎯 **Engineering planning & hazard mitigation**  
🎯 **3D visualisation for stakeholders**  

---

# 4. Installation

1. Download or clone this repository.  
2. Place `BundDesigner_v5_2e.py` in a known tools directory.  
3. In ArcGIS Pro:  
   - Open **Toolboxes**  
   - Add → **Script Tool**  
   - Point to the script  
4. Add parameters **in correct order (0–24)**.  
5. Save your toolbox (`EngineeringArcProTools.atbx` or equivalent).

---

# 5. Input Parameters (Detailed)

### **Input Centreline Features**  
Polyline representing bund crest alignment.

### **Centreline ID Field**  
Unique ID copied to all outputs.

### **Design Height Mode**  
- **Use Field** — absolute crest RL per feature  
- **Use Start/End** — linear gradient along centreline  
- **Use HAG Field** — DEM + attribute offset  
- **Use HAG Value** — DEM + constant offset  

### **Design Height Field (m)**  
Used when *Use Field* is selected.

### **Start / End Crest Height (m)**  
Used when *Use Start/End* is selected.

### **HAG Field / HAG Value**  
Defines height above ground.

### **Input DEM**  
Existing terrain.

### **Crest Width (m)**  
Flat top width of bund.

### **Maintain Crest Width**  
True = enforce full crest width.

### **Batter Slope (H:V)**  
Example: `3` = 3H:1V.

### **End Taper Length (m)**  
Zero creates a vertical end wall.

### **Vertical Datum Label**  
E.g., `NZVD2016`, `Moturiki`.

### **Append Datum to Output Names**  
Adds `_moturiki` etc.

### **Topsoil Stripping Depth (m)**  
Strip thickness for costing.

### **Output Workspace (File GDB)**  
Destination FGDB.

### **Output Merged Design Surface Raster**  
Writes global bund surface.

### **Output Per-Feature Surfaces**  
Debugging only.

### **Output Difference Raster (Fill)**  
Writes fill depth raster.

### **Output 3D Multipatch Geometry**  
Generates 3D solid.

### **Create Bund Footprint Polygon Layer**  
Toe polygon.

### **Output CSV Summary**  
One row per bund + TOTAL.

### **Treat Overlapping Centrelines as One Bund**  
Dissolves by ID.

### **Processing Mask Buffer Extra (m)**  
Ensures batters are not clipped.

---

# 6. Output Datasets Explained

### 🟦 BundSurface Raster  
A realistic **constructed ground level** surface.  
Used for:
- Flood modelling (burn into DEM)  
- Cross-sections  
- Visualisation  
- Surface area checks  

### 🟧 BundFill Raster  
Fill depth in metres.  
Used for:
- Volume calculation  
- Identifying high-fill zones  
- Estimating material transport costs  

### 🟩 BundFootprint Polygon  
Toe polygon of bund.  
Used for:
- Land take  
- Consenting overlays  
- Property impact checks  

### 🟪 BundMultipatch (optional)  
True 3D object.  
Used for:
- Scene rendering  
- Stakeholder presentations  
- Export to Unreal/Blender  

### 📄 BundVolumes (Table + CSV)  
Highly structured output for:
- Costing  
- Reporting  
- Model documentation  
- Auditing & QC  

---

# 7. Quality Control / QA Workflow

### 🔎 **A. Visual Checks**
- BundSurface sits smoothly over DEM  
- Crest width looks consistent  
- Batter slopes look uniform  
- No gaps between adjacent bund sections  

### 📏 **B. Elevation Checks**
Use Identify tool to sample:
- DEM elevation  
- Crest elevation  
- BundSurface elevation  
Expected: DEM < BundSurface by ~fill thickness.

### 🧮 **C. Volume Checks**
Compare with:
- 12d volume from TIN  
- Civil 3D volume surfaces  
- Hand-calculated prism approximations  
Consistency within **5–12%** is typical.

### 🧱 **D. Footprint QC**
Check:
- Polygon aligns tightly to fill raster  
- No slivers or holes  
- Area matches expectations  

### 🎥 **E. Multipatch QC**
In a 3D Scene:
- Bund should match BundSurface shape  
- Vertical faces clean  
- Footprint extrusion correct  
- Datum written in attribute  

---

# 8. Accuracy, Limitations & Expected Error

### 🌐 DEM Limitation  
Bunds narrower than DEM resolution (e.g., 3.5 m crest on a 1 m DEM) will appear pixelated.  
Volume calculations remain reliable because all raster cells contribute correctly.

### 📉 Vertical Error  
NZ 1 m LiDAR DEM typically:  
- RMSE ≈ **0.15–0.25 m**  

### 📊 Expected Volume Error  
Typical expected uncertainty:  
- **±8–12%** for small or complex bunds  
- **±5–8%** for long simple bunds  

### ❗ Engineering Disclaimer  
This tool **does not** replace detailed design.  
It is **for concept alignment, optioneering, costing, and flood-model preparation only**.

---

# 9. Repository Structure

Detainment-Bund-Tool/
│
├── BundDesigner_v5_2e.py # Main engine script
├── README.md # Documentation
└── examples/ # (Optional) example outputs

---

# 10. Licensing

MIT License — use it freely in professional or research contexts.

---

# 11. Support

If you encounter:
- Missing outputs  
- Geometry errors  
- Multipatch issues  
- Strange fill depths  

Open a GitHub Issue and include:
- Your parameter list  
- Screenshots  
- A sample centreline (if possible)

Happy designing.
