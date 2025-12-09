# BundDesigner_v5_2e.py
# Script-tool version for EngineeringArcProTools.atbx (Detainment Bund 3d Design)
# Requests addressed:
#  • Per-feature CSV rows (one per centreline) + a merged TOTALS row at the bottom.
#  • Persist dissolved centrelines as <base>_Centrelines_MergedByID when Merge by ID = True.
#  • Smoother crest/design surfaces: built-in gentle smoothing (crest ~2 m radius by default).
#  • Keeps mask safety & clean in_memory temp handling.
#  • Multipatch from full TINs + footprint via ExtrudeBetween (no ExtractTin).
# Usage:
#  • Save to: O:\_arcpro maps and templates\_python scripts\BundDesign\BundDesigner_v5_2e.py
#  • Point your Script Tool to this file. Param order 0–24 and the same ToolValidator as before.

import os, traceback
import arcpy
from arcpy import env
from arcpy.sa import *

arcpy.env.overwriteOutput = True

# ---- smoothing knobs (adjust here if you want stronger/weaker smoothing) ----
SMOOTH_CREST_METERS  = 2.0   # mean filter radius around crest elevations; 0 = none
SMOOTH_DESIGN_METERS = 0.0   # mean filter radius on the final design raster before merging; 0 = none

# ---------- helpers ----------

def _as_bool(s):
    return str(s).strip().lower() in ("true","1","yes","y")


def _safe(ws, name):
    return os.path.join(ws, arcpy.ValidateTableName(name, ws) if ws.lower().endswith(".gdb") else name)


def _tmp_fc(name_stub, memory_ok=True):
    nm = f"tmp_{name_stub}"
    if memory_ok:
        return os.path.join("in_memory", nm)
    return _safe(arcpy.env.scratchGDB, nm)


def _f(v, dflt=None):
    if v is None or v == "":
        return dflt
    try:
        return float(v)
    except Exception:
        return dflt


def _smooth_raster(ras, meters, cell):
    try:
        if meters and meters > 0:
            r = max(1, int(round(meters / max(cell, 0.0001))))
            return FocalStatistics(ras, NbrCircle(r, "CELL"), "MEAN", "DATA")
    except Exception as ex:
        arcpy.AddWarning(f"Smoothing skipped: {ex}")
    return ras


# ---------- core engine ----------

def run_engine(params):
    (
        in_lines, id_field, design_mode,
        height_field, start_h, end_h,
        hag_field, hag_value,
        dem_path,
        crest_w, keep_crest, batter, taper,
        datum, name_suffix, strip,
        out_ws,
        want_merged_surf, want_perfeat_surf, want_fill_ras,
        want_mpatch, want_footprint, want_csv,
        merge_by_id, extra_buf
    ) = params

    arcpy.AddMessage("### BundDesigner v5.2e (engine) START ###")

    # Licenses
    if arcpy.CheckExtension("Spatial") != "Available":
        raise arcpy.ExecuteError("Spatial Analyst license not available.")
    have_3d = (arcpy.CheckExtension("3D") == "Available")
    if want_mpatch and not have_3d:
        arcpy.AddWarning("3D Analyst not available — skipping multipatch output.")
        want_mpatch = False

    # Existence
    if not arcpy.Exists(in_lines):
        raise arcpy.ExecuteError(f"Missing centrelines: {in_lines}")
    if not arcpy.Exists(dem_path):
        raise arcpy.ExecuteError(f"Missing DEM: {dem_path}")
    if not arcpy.Exists(out_ws):
        raise arcpy.ExecuteError(f"Missing output workspace: {out_ws}")

    # Mode checks
    if design_mode == "Use Field":
        f = [f for f in arcpy.ListFields(in_lines) if f.name == height_field]
        if not f:
            raise arcpy.ExecuteError(f"Design height field '{height_field}' not on {in_lines}.")
        if f[0].type not in ("Double", "Single", "Integer", "SmallInteger"):
            raise arcpy.ExecuteError(f"Design height field '{height_field}' must be numeric (found {f[0].type}).")
    elif design_mode == "Use Start/End":
        if start_h is None or end_h is None:
            raise arcpy.ExecuteError("Start and End crest heights are required for 'Use Start/End' mode.")
    elif design_mode == "Use HAG Field":
        f = [f for f in arcpy.ListFields(in_lines) if f.name == hag_field]
        if not f:
            raise arcpy.ExecuteError(f"HAG field '{hag_field}' not on {in_lines}.")
        if f[0].type not in ("Double", "Single", "Integer", "SmallInteger"):
            raise arcpy.ExecuteError(f"HAG field '{hag_field}' must be numeric (found {f[0].type}).")
    elif design_mode == "Use HAG Value":
        if hag_value is None:
            raise arcpy.ExecuteError("Height Above Ground Value is required for 'Use HAG Value' mode.")
    else:
        raise arcpy.ExecuteError(f"Unknown design_mode: {design_mode}")

    # Env
    arcpy.CheckOutExtension("Spatial")
    dem = Raster(dem_path)
    env.snapRaster = dem
    env.cellSize = dem
    env.extent = dem.extent
    env.mask = None

    # Names
    base = os.path.splitext(os.path.basename(in_lines))[0]
    suffix = f"_{datum}" if (name_suffix and datum) else ""
    surf_path = _safe(out_ws, f"{base}_BundSurface{suffix}")
    fill_path = _safe(out_ws, f"{base}_BundFill{suffix}")
    fp_fc = _safe(out_ws, f"{base}_BundFootprint{suffix}")
    mp_fc = _safe(out_ws, f"{base}_BundMultipatch{suffix}")
    merged_id_fc = _safe(out_ws, f"{base}_Centrelines_MergedByID")
    is_gdb = out_ws.lower().endswith(".gdb")
    per_dir = out_ws if is_gdb else os.path.join(out_ws, "per_feature")

    # Containers
    if want_footprint:
        if arcpy.Exists(fp_fc):
            arcpy.management.Delete(fp_fc)
        arcpy.management.CreateFeatureclass(out_ws, os.path.basename(fp_fc), "POLYGON", spatial_reference=arcpy.Describe(in_lines).spatialReference)
        for fn, ft, ln in [("CentrelineID", "TEXT", 256), ("Area_ha", "DOUBLE", None), ("VertDatum", "TEXT", 32)]:
            arcpy.management.AddField(fp_fc, fn, ft, field_length=ln)

    merged_s = None
    merged_f = None

    # Merge by ID (optional) — and persist a copy if requested
    lines = in_lines
    if merge_by_id:
        arcpy.AddMessage(f"Merging overlaps by ID '{id_field}'…")
        tmp_merge = _tmp_fc("merge", memory_ok=False)
        if arcpy.Exists(tmp_merge):
            arcpy.management.Delete(tmp_merge)
        stats = None
        carry_field = height_field if design_mode == "Use Field" else (hag_field if design_mode == "Use HAG Field" else None)
        if carry_field:
            stats = [[carry_field, "MAX"]]
        arcpy.management.Dissolve(in_lines, tmp_merge, id_field, statistics_fields=stats, multi_part="SINGLE_PART")
        if carry_field:
            mx = f"MAX_{carry_field}"
            names = [f.name for f in arcpy.ListFields(tmp_merge)]
            if mx in names:
                if carry_field not in names:
                    arcpy.management.AddField(tmp_merge, carry_field, "DOUBLE")
                arcpy.management.CalculateField(tmp_merge, carry_field, f"!{mx}!")
        lines = tmp_merge
        try:
            # persist to output gdb with stable name
            if arcpy.Exists(merged_id_fc):
                arcpy.management.Delete(merged_id_fc)
            arcpy.management.CopyFeatures(tmp_merge, merged_id_fc)
            arcpy.AddMessage(f"Saved merged centrelines → {merged_id_fc}")
        except Exception as ex:
            arcpy.AddWarning(f"Could not save Centrelines_MergedByID: {ex}")

    # Iterate features and accumulate per-feature rows for CSV
    per_rows = []
    dsc = arcpy.Describe(lines)
    oid = dsc.OIDFieldName
    flds = [oid, id_field, "SHAPE@", "SHAPE@LENGTH"]
    if design_mode == "Use Field":
        flds.insert(2, height_field)
    if design_mode == "Use HAG Field":
        flds.insert(2, hag_field)

    with arcpy.da.SearchCursor(lines, flds) as cur:
        for row in cur:
            if design_mode == "Use Field":
                oidv, cid, crest_val, geom, L = row
                if crest_val is None:
                    arcpy.AddWarning(f"OID {oidv}: NULL design height; skipped.")
                    continue
                crest_const = float(crest_val)
                mode = "CONST_ABS"
            elif design_mode == "Use HAG Field":
                oidv, cid, hag_val, geom, L = row
                if hag_val is None:
                    arcpy.AddWarning(f"OID {oidv}: NULL HAG; skipped.")
                    continue
                hag_local = float(hag_val)
                mode = "HAG_FIELD"
            else:
                oidv, cid, geom, L = row
                mode = "GRADIENT" if design_mode == "Use Start/End" else "HAG_VALUE"

            arcpy.AddMessage(f"— Feature OID {oidv} (ID={cid})")

            # Local mask polygon (in_memory)
            ln_fc = _tmp_fc(f"ln_{oidv}")
            arcpy.management.CopyFeatures([geom], ln_fc)
            reach = (batter * 10.0) + (crest_w * 0.5) + max(taper, 0.0) + max(extra_buf, 0.0)
            msk = _tmp_fc(f"mask_{oidv}")
            arcpy.analysis.Buffer(ln_fc, msk, f"{reach} Meters", line_side="FULL", line_end_type="FLAT", dissolve_option="ALL", method="PLANAR")
            env.mask = msk

            # Crest polygon (for maintain-crest logic)
            cell = float(arcpy.GetRasterProperties_management(dem, "CELLSIZEX").getOutput(0))
            crest_buf = crest_w / 2.0 + (cell * 0.5 if keep_crest else 0.0)
            crest_fc = _tmp_fc(f"crest_{oidv}")
            arcpy.analysis.Buffer(ln_fc, crest_fc, f"{crest_buf} Meters", line_side="FULL", line_end_type="FLAT", dissolve_option="ALL", method="PLANAR")

            dist = EucDistance(crest_fc)

            # Crest elevation surface per mode
            if mode == "CONST_ABS":
                crest_z = Float(crest_const)
            elif mode == "GRADIENT":
                step = max(cell, 2 * cell)
                pts = _tmp_fc(f"pts_{oidv}")
                arcpy.management.GeneratePointsAlongLines(ln_fc, pts, "DISTANCE", Distance=f"{step} Meters", Include_End_Points="END_POINTS")
                arcpy.management.AddField(pts, "Chain_m", "DOUBLE")
                arcpy.management.AddField(pts, "Crest_m", "DOUBLE")
                with arcpy.da.UpdateCursor(pts, ["SHAPE@", "Chain_m", "Crest_m"]) as u:
                    for shp, _, _ in u:
                        ch = geom.measureOnLine(shp.firstPoint)
                        zc = start_h + (end_h - start_h) * (ch / max(L, 0.0001))
                        u.updateRow([shp, ch, zc])
                crest_z = NaturalNeighbor(pts, "Crest_m")
                crest_z = Con(IsNull(crest_z), Float(start_h), crest_z)
            else:
                step = max(cell, 2 * cell)
                pts0 = _tmp_fc(f"pts0_{oidv}")
                arcpy.management.GeneratePointsAlongLines(ln_fc, pts0, "DISTANCE", Distance=f"{step} Meters", Include_End_Points="END_POINTS")
                pts = _tmp_fc(f"ptsd_{oidv}")
                ExtractValuesToPoints(pts0, dem, pts, "INTERPOLATE", "VALUE_ONLY")
                if "Crest_m" not in [f.name for f in arcpy.ListFields(pts)]:
                    arcpy.management.AddField(pts, "Crest_m", "DOUBLE")
                hag = hag_local if mode == "HAG_FIELD" else float(hag_value)
                arcpy.management.CalculateField(pts, "Crest_m", f"!RASTERVALU! + {hag}", "PYTHON3")
                crest_z = NaturalNeighbor(pts, "Crest_m")
                crest_z = Con(IsNull(crest_z), Raster(dem) + Float(hag), crest_z)

            # Gentle crest smoothing to reduce jaggedness
            crest_z = _smooth_raster(crest_z, SMOOTH_CREST_METERS, cell)

            # Design surface from crest & batter (+ optional taper)
            design = Float(crest_z) - (Float(dist) / batter)
            if taper > 0:
                ends = _tmp_fc(f"ends_{oidv}")
                arcpy.management.FeatureVerticesToPoints(ln_fc, ends, "BOTH_ENDS")
                de = EucDistance(ends)
                t = Con(de >= taper, 1.0, de / taper)
                design = Raster(dem) + (design - Raster(dem)) * t

            if keep_crest:
                inside = Con(IsNull(ExtractByMask(dem, crest_fc)), 0, 1)
                bund = Con(inside == 1, crest_z, Con(design > Raster(dem), design))
            else:
                bund = Con(design > Raster(dem), design)

            # Optional light smoothing on final design
            bund = _smooth_raster(bund, SMOOTH_DESIGN_METERS, cell)

            fill = SetNull(IsNull(bund), bund - Raster(dem))

            # Footprint (single dissolved poly only) + per-feature volumes
            A = V = S = 0.0
            if want_footprint:
                poly = _tmp_fc(f"poly_{oidv}")
                try:
                    arcpy.conversion.RasterToPolygon(Con(fill, 1), poly, "NO_SIMPLIFY")
                    dis = _tmp_fc(f"dis_{oidv}")
                    arcpy.management.Dissolve(poly, dis)
                    # volume by zonal sum of fill depth * cell area
                    zt = _tmp_fc(f"zt_{oidv}", memory_ok=False)
                    arcpy.sa.ZonalStatisticsAsTable(dis, "OBJECTID", fill, zt, "DATA", "SUM")
                    depth_sum = 0.0
                    with arcpy.da.SearchCursor(zt, ["SUM"]) as c:
                        for (s,) in c:
                            if s is not None:
                                depth_sum += float(s)
                    cellx = float(arcpy.GetRasterProperties_management(dem, "CELLSIZEX").getOutput(0))
                    celly = float(arcpy.GetRasterProperties_management(dem, "CELLSIZEY").getOutput(0))
                    cell_area = abs(cellx * celly)
                    V = depth_sum * cell_area
                    with arcpy.da.SearchCursor(dis, ["SHAPE@AREA"]) as c:
                        for (a,) in c:
                            A += float(a)
                    S = A * (strip if strip else 0.0)

                    # tag + append dissolved polygon to footprint FC
                    for fn, ft in [("CentrelineID", "TEXT"), ("Area_ha", "DOUBLE"), ("VertDatum", "TEXT")]:
                        if fn not in [f.name for f in arcpy.ListFields(dis)]:
                            if ft == "TEXT":
                                arcpy.management.AddField(dis, fn, ft, field_length=256 if fn == "CentrelineID" else 32)
                            else:
                                arcpy.management.AddField(dis, fn, ft)
                    with arcpy.da.UpdateCursor(dis, ["CentrelineID", "Area_ha", "VertDatum", "SHAPE@AREA"]) as u:
                        for r in u:
                            r[0] = str(cid)
                            r[1] = r[3] / 10000.0
                            r[2] = datum
                            u.updateRow(r)
                    arcpy.management.Append(dis, fp_fc, "NO_TEST")
                except arcpy.ExecuteError:
                    arcpy.AddWarning(f"OID {oidv}: footprint/volumes failed; continuing.")
            else:
                # If no footprint requested, we can still compute A/V via raster where needed later
                pass

            # Per-feature CSV row (even if A/V are 0, include the line)
            per_rows.append([
                int(oidv), str(cid), float(L), design_mode,
                (float(hag_local) if mode == "HAG_FIELD" else (float(hag_value) if mode == "HAG_VALUE" else None)),
                (float(crest_const) if mode == "CONST_ABS" else None),
                (float(start_h) if design_mode == "Use Start/End" else None),
                (float(end_h) if design_mode == "Use Start/End" else None),
                float(crest_w), float(batter), float(taper),
                ("True" if keep_crest else "False"), float(strip if strip else 0.0),
                A, V, S, datum
            ])

            # Merge accumulators (mask OFF)
            prev = env.mask
            env.mask = None
            try:
                if want_merged_surf:
                    merged_s = bund if merged_s is None else Con(IsNull(merged_s), bund, Con(IsNull(bund), merged_s, Con(bund > merged_s, bund, merged_s)))
                if want_merged_surf or want_fill_ras:
                    merged_f = fill if merged_f is None else Con(IsNull(merged_f), fill, Con(IsNull(fill), merged_f, Con(fill > merged_f, fill, merged_f)))
            finally:
                env.mask = prev

            # Clean per-feature in-memory temp vectors
            for t in [ln_fc, msk, crest_fc]:
                try:
                    if t and arcpy.Exists(t):
                        arcpy.management.Delete(t)
                except Exception:
                    pass

    # Make absolutely sure no stale mask remains before final combine
    env.mask = None
    try:
        arcpy.ClearEnvironment("mask")
    except Exception:
        pass

    # Finalize rasters (mask-free context)
    if want_merged_surf and merged_s is not None:
        with arcpy.EnvManager(mask=None, extent=dem.extent, snapRaster=dem, cellSize=dem):
            ms = Raster(merged_s)
            final = Con(IsNull(ms), Raster(dem), ms)
            arcpy.AddMessage(f"Writing merged surface → {surf_path}")
            final.save(surf_path)
        try:
            arcpy.management.CalculateStatistics(surf_path)
            arcpy.management.BuildPyramids(surf_path)
        except Exception:
            pass

    if (want_merged_surf or want_fill_ras) and merged_f is not None:
        with arcpy.EnvManager(mask=None, extent=dem.extent, snapRaster=dem, cellSize=dem):
            arcpy.AddMessage(f"Writing merged fill → {fill_path}")
            merged_f.save(fill_path)
        try:
            arcpy.management.CalculateStatistics(fill_path)
        except Exception:
            pass

    # Multipatch (full TINs + footprint boundaries; no ExtractTin)
    if want_mpatch and arcpy.Exists(fp_fc) and arcpy.Exists(surf_path):
        try:
            arcpy.AddMessage("Building multipatch from design/DEM TINs…")
            cell = float(arcpy.GetRasterProperties_management(dem, "CELLSIZEX").getOutput(0))
            ztol = max(0.01, cell * 0.05)
            dem_tin = _safe(env.scratchGDB, "tmp_dem_tin_v52e")
            des_tin = _safe(env.scratchGDB, "tmp_des_tin_v52e")
            for t in [dem_tin, des_tin]:
                if arcpy.Exists(t):
                    arcpy.management.Delete(t)
            arcpy.ddd.RasterTin(dem_path, dem_tin, ztol, "", 1.0)
            arcpy.ddd.RasterTin(surf_path, des_tin, ztol, "", 1.0)
            tmp_mp = _safe(env.scratchGDB, "tmp_mp_v52e")
            if arcpy.Exists(tmp_mp):
                arcpy.management.Delete(tmp_mp)
            arcpy.ddd.ExtrudeBetween(des_tin, dem_tin, fp_fc, tmp_mp)
            if not arcpy.Exists(mp_fc):
                arcpy.management.CreateFeatureclass(out_ws, os.path.basename(mp_fc), "MULTIPATCH", spatial_reference=arcpy.Describe(in_lines).spatialReference)
            if "VertDatum" not in [f.name for f in arcpy.ListFields(tmp_mp)]:
                arcpy.management.AddField(tmp_mp, "VertDatum", "TEXT", field_length=32)
            arcpy.management.CalculateField(tmp_mp, "VertDatum", f"'{datum}'", "PYTHON3")
            arcpy.management.Append(tmp_mp, mp_fc, "NO_TEST")
            for t in [dem_tin, des_tin, tmp_mp]:
                try:
                    if arcpy.Exists(t):
                        arcpy.management.Delete(t)
                except Exception:
                    pass
        except Exception as ex:
            arcpy.AddWarning(f"Multipatch creation failed: {ex}")

    # -------- CSV: per-feature rows + merged totals --------
    if want_csv:
        try:
            # Merged totals from merged_f or from summed per_rows
            total_area_m2 = 0.0
            total_fill_m3 = 0.0
            total_strip_m3 = 0.0
            if 'merged_f' in locals() and merged_f is not None:
                fp_for_total = fp_fc
                if not arcpy.Exists(fp_for_total):
                    arcpy.AddMessage("Creating temporary footprint from merged fill raster for totals…")
                    tmp_poly = _tmp_fc("total_poly", memory_ok=False)
                    arcpy.conversion.RasterToPolygon(Con(merged_f, 1), tmp_poly, "NO_SIMPLIFY")
                    fp_for_total = _safe(env.scratchGDB, "total_fp")
                    arcpy.management.Dissolve(tmp_poly, fp_for_total)
                fp_all = _safe(env.scratchGDB, "fp_all")
                if arcpy.Exists(fp_all):
                    arcpy.management.Delete(fp_all)
                arcpy.management.Dissolve(fp_for_total, fp_all)
                cellx = float(arcpy.GetRasterProperties_management(dem, "CELLSIZEX").getOutput(0))
                celly = float(arcpy.GetRasterProperties_management(dem, "CELLSIZEY").getOutput(0))
                cell_area = abs(cellx * celly)
                zt = _safe(env.scratchGDB, "zt_total")
                if arcpy.Exists(zt):
                    arcpy.management.Delete(zt)
                arcpy.sa.ZonalStatisticsAsTable(fp_all, "OBJECTID", merged_f, zt, "DATA", "SUM")
                depth_sum = 0.0
                with arcpy.da.SearchCursor(zt, ["SUM"]) as c:
                    for (s,) in c:
                        if s is not None:
                            depth_sum += float(s)
                total_fill_m3 = depth_sum * cell_area
                with arcpy.da.SearchCursor(fp_all, ["SHAPE@AREA"]) as c:
                    for (a,) in c:
                        total_area_m2 += float(a)
                total_strip_m3 = total_area_m2 * (strip if strip else 0.0)
            else:
                # Fall back to sum of per-feature rows
                for r in per_rows:
                    total_area_m2  += float(r[13])
                    total_fill_m3  += float(r[14])
                    total_strip_m3 += float(r[15])

            # Write table in GDB
            tname = arcpy.ValidateTableName(f"{base}_BundVolumes{suffix}", out_ws)
            tpath = os.path.join(out_ws, tname)
            if arcpy.Exists(tpath):
                arcpy.management.Delete(tpath)
            arcpy.management.CreateTable(out_ws, tname)
            schema = [
                ("SourceOID", "LONG", None),
                ("CentrelineID", "TEXT", 64),
                ("Length_m", "DOUBLE", None),
                ("Mode", "TEXT", 16),
                ("HAG_m", "DOUBLE", None),
                ("CrestField_m", "DOUBLE", None),
                ("StartH_m", "DOUBLE", None),
                ("EndH_m", "DOUBLE", None),
                ("CrestWidth_m", "DOUBLE", None),
                ("Batter_HperV", "DOUBLE", None),
                ("EndTaper_m", "DOUBLE", None),
                ("MaintainCrest", "TEXT", 8),
                ("StripDepth_m", "DOUBLE", None),
                ("FillArea_m2", "DOUBLE", None),
                ("FillVolume_m3", "DOUBLE", None),
                ("StripVolume_m3", "DOUBLE", None),
                ("VertDatum", "TEXT", 32)
            ]
            for fn, tp, ln in schema:
                if tp == "TEXT":
                    arcpy.management.AddField(tpath, fn, tp, field_length=(ln or 255))
                else:
                    arcpy.management.AddField(tpath, fn, tp)
            with arcpy.da.InsertCursor(tpath, [s[0] for s in schema]) as ic:
                for r in per_rows:
                    ic.insertRow(r)
                # totals row at the end (SourceOID = -1, CentrelineID = "__TOTAL__")
                ic.insertRow([
                    -1, "__TOTAL__", None, design_mode,
                    (float(hag_value) if design_mode == "Use HAG Value" else None), None,
                    (float(start_h) if design_mode == "Use Start/End" else None),
                    (float(end_h) if design_mode == "Use Start/End" else None),
                    float(crest_w), float(batter), float(taper),
                    ("True" if keep_crest else "False"), float(strip if strip else 0.0),
                    total_area_m2, total_fill_m3, total_strip_m3, datum
                ])

            # CSV alongside GDB
            ws_dir = out_ws if os.path.isdir(out_ws) else os.path.dirname(out_ws)
            csv = os.path.join(ws_dir, f"{base}_BundVolumes{suffix}.csv")
            headers = [s[0] for s in schema]
            with open(csv, "w", encoding="utf-8") as f:
                f.write(",".join(headers) + "\n")
                def _fmt(v):
                    return "" if v is None else (str(v))
                for r in per_rows:
                    f.write(",".join(_fmt(v) for v in r) + "\n")
                total_row = [
                    -1, "__TOTAL__", "", design_mode,
                    (float(hag_value) if design_mode == "Use HAG Value" else ""), "",
                    (float(start_h) if design_mode == "Use Start/End" else ""),
                    (float(end_h) if design_mode == "Use Start/End" else ""),
                    float(crest_w), float(batter), float(taper),
                    ("True" if keep_crest else "False"), float(strip if strip else 0.0),
                    total_area_m2, total_fill_m3, total_strip_m3, datum
                ]
                f.write(",".join(_fmt(v) for v in total_row) + "\n")
            arcpy.AddMessage(f"Volumes table + CSV written → {tpath} and {csv}")
        except Exception as ex:
            arcpy.AddWarning(f"CSV creation failed: {ex}")

    # Hard clean in_memory at end
    try:
        arcpy.management.Delete("in_memory")
    except Exception:
        pass

    arcpy.AddMessage("### BundDesigner v5.2e (engine) DONE ###")


# ---------- entry point ----------

if __name__ == "__main__":
    try:
        arcpy.AddMessage("### Detainment Bund 3d Design — BundDesigner v5.2e (script) ###")
        g = [arcpy.GetParameterAsText(i) for i in range(25)]
        try:
            cnt = int(arcpy.management.GetCount(g[0]).getOutput(0))
            arcpy.AddMessage(f"Input features count: {cnt}")
        except Exception as e:
            arcpy.AddWarning(f"Could not count input features: {e}")
        vals = [
            g[0], g[1], (g[2] or "Use Field"), (g[3] or None),
            _f(g[4], None), _f(g[5], None),
            (g[6] or None), _f(g[7], None),
            g[8], _f(g[9], 2.0),
            _as_bool(g[10]), _f(g[11], 5.0), _f(g[12], 0.0),
            (g[13] or ""), _as_bool(g[14]), _f(g[15], 0.0),
            g[16], _as_bool(g[17]), _as_bool(g[18]), _as_bool(g[19]),
            _as_bool(g[20]), _as_bool(g[21]), _as_bool(g[22]),
            _as_bool(g[23]), _f(g[24], 20.0),
        ]
        run_engine(vals)
    except Exception as ex:
        arcpy.AddError("### BundDesigner ERROR ###")
        arcpy.AddError(str(ex))
        arcpy.AddError(traceback.format_exc())
        raise
