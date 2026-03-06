# -*- coding: utf-8 -*-

import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "BLE Post Processing"
        self.alias = "BLEPostProcessing"

        # List of tool classes associated with this toolbox
        self.tools = [TWDBFlatAreas, TieInPolys, FBSCheck_1D, FBSCheck_2D, A5Check_Part1, A5Check_Part2, PriorityScore]


class TWDBFlatAreas(object):
    def __init__(self):
        self.label = "TWDB Flat Polygons"
        self.description = "Process flat (zero slope) and semi-flat (zero to two slope) areas \
            for polygon revising in accordance with Texas Water Development Board standards."

    def getParameterInfo(self):
    # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        dem = arcpy.Parameter(
            name='Ground DEM',
            displayName='Ground DEM',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required'
        )
        upperslope = arcpy.Parameter(
            name='Upper Slope Value',
            displayName='Upper Slope Value',
            datatype='GPString',
            direction='Input',
            parameterType='Required'
        )

        params = [folder, dem, upperslope]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        upperslope = parameters[2]
    # Set default value if not entered
        if not upperslope.altered:
            upperslope.value = "1.5" # default upper slope value
        return

    def updateMessages(self, parameters):
        upperslope = float(parameters[2].valueAsText)
        if upperslope > 3:
            arcpy.AddWarning(f"WARNING: Slope values of {upperslope} and under will include most areas.")
        return

    def execute(self, parameters, messages):
    # Step 1: Setup variables and file gdb
        folder = parameters[0].valueAsText
        DEM = parameters[1].valueAsText
        arcpy.management.CreateFileGDB(fr"{folder}", "FlatAreas.gdb", "CURRENT")
        arcpy.env.workspace = fr"{folder}\\FlatAreas.gdb"
        upperslope = float(parameters[2].valueAsText)
        arcpy.SetProgressorLabel("Calculating slope...")
        outSlope = arcpy.sa.Slope(DEM)
        outSlope.save("Slope")
        arcpy.AddMessage("Calculated slope")
        arcpy.SetProgressorLabel("Reclassifying flat slopes...")
        outSetNull = arcpy.sa.SetNull("Slope", 1, "Value >0")
        outSetNull.save("Flat_Slope")
        arcpy.AddMessage("Reclassified flat slopes")
        arcpy.SetProgressorLabel("Converting to polygon...")
        arcpy.conversion.RasterToPolygon("Flat_Slope", "Flat_Poly")
        arcpy.AddMessage("Converted to polygon")
        arcpy.SetProgressorLabel("Smoothing flat areas over 1/4 acre...")
        selFlat = arcpy.management.SelectLayerByAttribute("Flat_Poly", "NEW_SELECTION", '"Shape_Area">10890')
        arcpy.cartography.SmoothPolygon(selFlat, "FlatAreas", "PAEK", 25)
        arcpy.AddMessage("Smoothed flat areas over 1/4 acre")
        arcpy.SetProgressorLabel("Buffering flat areas...")
        arcpy.analysis.PairwiseBuffer("FlatAreas", "BufferedFlatAreas", "25 FEET")
        arcpy.AddMessage("Buffered flat areas")
        arcpy.SetProgressorLabel("Reclassifying semi-flat slopes...")
        outSetNull2 = arcpy.sa.SetNull("Slope", 1, f"VALUE > {upperslope}")
        outSetNull2.save("SemiFlat_Slope")
        arcpy.AddMessage(f"Reclassified semi-flat slopes under {upperslope}")
        arcpy.SetProgressorLabel("Converting to polygon...")
        arcpy.conversion.RasterToPolygon("SemiFlat_Slope", "SemiFlat_Poly")
        arcpy.AddMessage("Converted to polygon")
        arcpy.SetProgressorLabel("Simplifying bends and buffering semi-flat areas over 1/4 acre...")
        selFlat = arcpy.management.SelectLayerByAttribute("SemiFlat_Poly", "NEW_SELECTION", '"Shape_Area">10890')
        arcpy.analysis.PairwiseBuffer(selFlat, "SemiFlatAreas", "2 FEET")
        arcpy.cartography.SimplifyPolygon(in_features="SemiFlatAreas",
                                        out_feature_class="SemiFlatAreas_SimplifyBends",
                                        algorithm="BEND_SIMPLIFY",
                                        tolerance="20 Feet",
                                        minimum_area="0 SquareFeet",
                                        error_option="NO_CHECK",
                                        collapsed_point_option="KEEP_COLLAPSED_POINTS",
                                        in_barriers=None)
        arcpy.analysis.PairwiseBuffer("SemiFlatAreas_SimplifyBends", "SemiFlat_Buffer", "8 FEET")
        arcpy.AddMessage("Simplified bends and buffered semi-flat areas over 1/4 acre")
        # Clean up intermediate files
        arcpy.SetProgressorLabel("Cleaning up files...")
        arcpy.management.Delete("Flat_Slope;Flat_Poly;SemiFlat_Slope;SemiFlat_Poly", '')
        arcpy.AddMessage("Deleted intermediate files")

########################################################################################

class TieInPolys(object):
    def __init__(self):
        self.label = "Tie-In Polygons"
        self.description = "Process depth raster for minimum values and stream proximity to tie-in disconnected flood polygons after BLE processing."

    def getParameterInfo(self):
    # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        depth = arcpy.Parameter(
            name='Raw Depth Raster',
            displayName='Raw Depth Raster',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required'
        )
        mindepth = arcpy.Parameter(
            name='Lower Depth Value',
            displayName='Lower Depth Value',
            datatype='GPString',
            direction='Input',
            parameterType='Required'
        )
        streamexits = arcpy.Parameter(
            name='Stream Exits',
            displayName='Stream Exits',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        streamexits.filter.list = ["Polyline"]
        distanceb = arcpy.Parameter(
            name='Floodplain Width',
            displayName='Floodplain Width (Buffer Distance)',
            datatype='GPLinearUnit',
            direction='Input',
            parameterType='Required')
        polys_1pct = arcpy.Parameter(
            name='1pct Polygons',
            displayName='1pct Polygons',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        polys_1pct.filter.list = ["Polygon"]
        streams = arcpy.Parameter(
            name='Streams',
            displayName='Streams',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        streams.filter.list = ["Polyline"]

        params = [folder, depth, mindepth, streamexits, distanceb, polys_1pct, streams]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        mindepth = parameters[2]
    # Set default value if not entered
        if not mindepth.altered:
            mindepth.value = "0.25" # default minimum depth value
        distanceb = parameters[4]
        if not distanceb.altered:
            distanceb.values = "15 Feet" # default buffer distance value
        return

    def updateMessages(self, parameters):
        mindepth = float(parameters[2].valueAsText)
        if mindepth < 0.25:
            arcpy.AddWarning(f"WARNING: Depth values of {mindepth} and above will include large areas.")
        return

    def execute(self, parameters, messages):
    # Setup variables and environments
        folder = parameters[0].valueAsText
        arcpy.management.CreateFileGDB(fr"{folder}", "TiedIn.gdb", "CURRENT")
        arcpy.env.workspace = fr"{folder}\\TiedIn.gdb"
        depth = parameters[1].valueAsText
        mindepth = float(parameters[2].valueAsText)
        streamexits = parameters[3].valueAsText
        distanceb = parameters[4].valueAsText
        polys_1pct = parameters[5].valueAsText
        streams = parameters[6].valueAsText
        arcpy.env.outputCoordinateSystem = arcpy.Describe(depth).spatialReference
        arcpy.env.overwriteOutput = True
        arcpy.env.addOutputsToMap = False

    # Process depth raster tie-in polygons
        # Reclassify all minimum and above depth cells to 1 to simplify the floodplain
        arcpy.SetProgressorLabel("Reclassifying depth...")
        arcpy.ddd.Reclassify(
            depth, "VALUE", f"-300 {mindepth} NODATA;{mindepth} 100 1", 
            "Reclass_Depth", "DATA"
            )
        # Convert the depth raster to polygon
        arcpy.SetProgressorLabel("Converting to polygon...")
        arcpy.conversion.RasterToPolygon(
            "Reclass_Depth", "Depth_Poly_Multi", 
            "SIMPLIFY", "Value", "SINGLE_OUTER_PART", None
            )
        arcpy.management.RepairGeometry(
            "Depth_Poly_Multi", "DELETE_NULL", "ESRI"
            )
        # Add a 0.01 buffer to the simplified polygons (this gets rid of weird gaps caused by extremely close vertices)
        arcpy.SetProgressorLabel("Buffering polygons...")
        arcpy.analysis.PairwiseBuffer(
            "Depth_Poly_Multi", "Depth_Poly_Buffer", 
            "0.01 Feet", "ALL", None, "PLANAR", "0 Feet"
            )
        # Convert buffered polys to single part
        arcpy.SetProgressorLabel("Converting to single part...")
        arcpy.management.MultipartToSinglepart(
            "Depth_Poly_Buffer", 
            "Depth_Poly"
            )
        # Remove contained holes less than 15,625 sqft
        arcpy.SetProgressorLabel("Eliminating small holes...")
        arcpy.management.EliminatePolygonPart(
            "Depth_Poly", "Depth_Poly_EPP", 
            "AREA", "15625 SquareFeet", 0, "CONTAINED_ONLY"
            )
        # Find the distance from each depth polygon to each stream exit
        arcpy.SetProgressorLabel("Calculating near distances...")
        arcpy.analysis.Near(
            "Depth_Poly_EPP", streamexits, None, 
            "NO_LOCATION", "NO_ANGLE", "PLANAR", "NEAR_DIST NEAR_DIST"
            )
        # Delete any depth polys:
            # greater than 100 feet away from a stream exit OR
            # with area less than 100 sqft and do not intersect the stream exit
        arcpy.SetProgressorLabel("Cleaning up depth polygons (1 of 2)...")
        deleted_features = 0
        with arcpy.da.UpdateCursor("Depth_Poly_EPP", ['NEAR_DIST', 'SHAPE@AREA']) as cursor:
            for row in cursor:
                if row[0]>=100 or (row[1]<=100 and row[0]>0):
                    deleted_features +=1
                    cursor.deleteRow()
        arcpy.AddMessage(f"Deleted {deleted_features} features over 100 feet from a stream exit or with area less than 100 square feet and not intersecting a stream exit")
        # Find the distance from each depth polygon to each depth polygon or stream exit (closer distance of the two is populated in NEAR_DIST)
        arcpy.analysis.Near(
            "Depth_Poly_EPP", ["Depth_Poly_EPP", streamexits], None,
            "NO_LOCATION", "NO_ANGLE", "PLANAR", "NEAR_DIST NEAR_DIST"
            )
        # Delete any depth polys not within 25 feet of another feature or a stream exit
        arcpy.SetProgressorLabel("Cleaning up depth polygons (2 of 2)...")
        deleted_features = 0
        with arcpy.da.UpdateCursor("Depth_Poly_EPP", ['NEAR_DIST']) as cursor:
            for row in cursor:
                if row[0]>=25:
                    deleted_features +=1
                    cursor.deleteRow()
        arcpy.AddMessage(f"Deleted {deleted_features} features not within 25 feet of another feature or a stream exit")
        arcpy.SetProgressorLabel("Clipping polys to buffered stream exits...")
        # Buffer streams
        arcpy.analysis.PairwiseBuffer(
            streamexits, "StreamExits_Buffer", 
            f"{distanceb}", "ALL", None, "PLANAR", "0 Feet")
        # Clip polys to limit floodplain width
        arcpy.analysis.PairwiseClip(
            "Depth_Poly_EPP", 
            "StreamExits_Buffer", 
            "Depth_Clip", None
            )
        # Merge with 1pct polygons
        arcpy.SetProgressorLabel("Merging and smoothing tied-in polygons...")
        arcpy.management.Merge(
            f"{polys_1pct};Depth_Clip", 
            "Poly_Tied_Merge_1", 
            )
        # Dissolve (aggregate) features
        arcpy.analysis.PairwiseDissolve(
            "Poly_Tied_Merge_1", 
            "Poly_Tied_Merge", 
            None, None, "SINGLE_PART")
        # Smooth sharp edges
        arcpy.cartography.SmoothPolygon(
            "Poly_Tied_Merge", 
            "Poly_Tied_Smooth", 
            "PAEK", "5 Feet", "FIXED_ENDPOINT", "NO_CHECK", None)
        # Erase to isolate tie-ins
        arcpy.analysis.PairwiseErase(
            "Poly_Tied_Smooth", 
            polys_1pct, 
            "Poly_TieIns", 
            None
            )
        # Clean up intermediate files
        arcpy.management.Delete(
            "Depth_Poly_Multi;Depth_Poly_Buffer;Depth_Poly;Depth_Poly_EPP;StreamExits_Buffer;Poly_Tied_Merge_1;Poly_Tied_Merge", 
            ''
            )
        # Delete non-intersecting polygons
        nostream = arcpy.management.SelectLayerByLocation(
            "Poly_Tied_Smooth", 
            "INTERSECT", 
            streams, None, 
            "NEW_SELECTION", "INVERT"
            )
        nopoly = arcpy.management.SelectLayerByLocation(
            nostream, 
            "INTERSECT", 
            polys_1pct, None, 
            "SUBSET_SELECTION", "INVERT"
            )
        arcpy.management.DeleteRows(
            nopoly
            )
        # Delete memory
        arcpy.management.Delete('memory')
        return   

########################################################################################

class FBSCheck_1D(object):
    def __init__(self):
        self.label = "FBS Check - 1D BLE"
        self.description = "Perform a Flood Boundary Standards check with test point generation," \
        + " geoprocessing, and comparison of DEM and generated WSEL TIN. NOTE: For best results," \
            + " perform manual edits to 2 inputs before processing:" \
            + " \n1) Convert relevant Zone A flood hazard area polygons to line and merge" \
                + "\n2) Extract relevant XS lines"

    def getParameterInfo(self):
    # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        distancep = arcpy.Parameter(
            name='Test Point Distance',
            displayName='Test Point Distance',
            datatype='GPLinearUnit',
            direction='Input',
            parameterType='Required')
        lineshp = arcpy.Parameter(
            name='Input Flood Hazard Line/s',
            displayName='Input Flood Hazard Line/s',
            datatype='GPLayer',
            direction='Input',
            parameterType='Required')
        xsshp = arcpy.Parameter(
            name='Input XS Lines',
            displayName='Input XS Lines',
            datatype='GPLayer',
            direction='Input',
            parameterType='Required')
        elev_field = arcpy.Parameter(
            name='Elevation Field',
            displayName='Elevation Field',
            datatype='GPString',
            direction='Input',
            parameterType='Required')
        elev_field.filter.type = "ValueList"
        elev_field.filter.list = ["E_WSE_1PCT","WSEL_REG"]
        wtrshp = arcpy.Parameter(
            name='Input Water Lines',
            displayName='Input Water Lines',
            datatype='GPLayer',
            direction='Input',
            parameterType='Required')
        proj = arcpy.Parameter(
            displayName="Local Projected Coordinate System",
            name="Local Projected Coordinate System",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")
        dem = arcpy.Parameter(
            name='Input Surface Raster',
            displayName='Input Surface Raster',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required')
        distanceb = arcpy.Parameter(
            name='Buffer Distance',
            displayName='Buffer Distance',
            datatype='GPLinearUnit',
            direction='Input',
            parameterType='Required')
        
        params = [folder, distancep, lineshp, xsshp, elev_field, wtrshp, proj, dem, distanceb]
        return params
    
    def updateParameters(self, parameters):
    # Set default values if not entered
        distancep = parameters[1]
        if not distancep.altered:
            distancep.values = "100 Feet" # default test point distance value
        distanceb = parameters[8]
        if not distanceb.altered:
            distanceb.values = "38 Feet" # default buffer distance value
        return

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
    # Step 1: Setup variables and file gdb
        arcpy.env.addOutputsToMap = True
        arcpy.env.overwriteOutput = True
        folder = parameters[0].valueAsText
        arcpy.management.CreateFileGDB(fr"{folder}", "FBS_Check.gdb", "CURRENT")
        arcpy.env.workspace = fr"{folder}\\FBS_Check.gdb"
        distancep = parameters[1].valueAsText
        floodlines = parameters[2].valueAsText
        spatial_ref = arcpy.Describe(floodlines).spatialReference
        arcpy.AddMessage(f"{floodlines} is in {spatial_ref.name}")
        if "Projected" not in spatial_ref.type:
            arcpy.AddError(spatial_ref.name + " is angular; this is not recommended. Distances should be estimated using projected coordinate systems.")
        fc_count = int(arcpy.GetCount_management(floodlines).getOutput(0))
        if fc_count > 1:
            arcpy.AddMessage(f"{floodlines} has not been merged into a single feature.")
        else:
            arcpy.AddMessage(f"{floodlines} has {fc_count} feature.")
        xslines = parameters[3].valueAsText
        elev_field = parameters[4].valueAsText
        wtrlines = parameters[5].valueAsText
        prjctn = parameters[6].valueAsText
        if "PROJECTION" not in prjctn:
            arcpy.AddError(prjctn + " is angular; this is not recommended. TINs should be made using projected coordinate systems.")
        dem = parameters[7].valueAsText
        distanceb = parameters[8].valueAsText
    # Step 2: Generate test points
        arcpy.SetProgressorLabel("Generating test points...")
        arcpy.management.GeneratePointsAlongLines(
            Input_Features=floodlines,
            Output_Feature_Class="CheckPoints",
            Point_Placement="DISTANCE",
            Distance=distancep,
            Percentage=None,
            Include_End_Points="NO_END_POINTS"
            )
        arcpy.AddMessage("Generated test points")
    # Step 3: Generate intersection points
        arcpy.SetProgressorLabel("Generating intersections...")
        arcpy.analysis.Intersect(
            in_features= (xslines,wtrlines),
            out_feature_class="XS_Wtr_Ln_Intersect",
            join_attributes="ALL",
            cluster_tolerance=None,
            output_type="POINT"
            )
        arcpy.analysis.Intersect(
            in_features= (xslines,floodlines),
            out_feature_class="XS_Flood_Ln_Intersect",
            join_attributes="ALL",
            cluster_tolerance=None,
            output_type="POINT"
            )
        arcpy.AddMessage("Generated intersections")
    # Step 4: Create TIN
        arcpy.SetProgressorLabel("Creating TIN...")
        arcpy.ddd.CreateTin(
            out_tin="FBS_TIN",
            spatial_reference=prjctn,
            in_features={f"XS_Wtr_Ln_Intersect {elev_field} Mass_Points <None>;" + \
            f"XS_Flood_Ln_Intersect {elev_field} Mass_Points <None>;" + \
            f"{xslines} {elev_field} Soft_Line <None>;" + \
            f"{floodlines} <None> Hard_Line <None>"},
            constrained_delaunay="DELAUNAY"
            )
        arcpy.AddMessage("Created TIN")
    # Step 5: Populate Z from DEM and calculate GrELEV
        arcpy.SetProgressorLabel("Populating elevation fields...")
        arcpy.ddd.AddSurfaceInformation(
            in_feature_class="CheckPoints",
            in_surface=dem,
            out_property="Z",
            method="BILINEAR",
            sample_distance=None,
            z_factor=1,
            pyramid_level_resolution=0,
            noise_filtering=""
            )
        arcpy.management.CalculateField(
            in_table="CheckPoints",
            field="GrELEV",
            expression="!Z!",
            expression_type="PYTHON3",
            code_block="",
            field_type="DOUBLE",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )
    # Step 6: Populate Z from TIN (overwrite Z) and calculate FldELEV
        arcpy.ddd.AddSurfaceInformation(
            in_feature_class="CheckPoints",
            in_surface=fr"{folder}\FBS_TIN",
            out_property="Z",
            method="LINEAR",
            sample_distance=None,
            z_factor=1,
            pyramid_level_resolution=0,
            noise_filtering=""
            )
        arcpy.management.CalculateField(
            in_table="CheckPoints",
            field="FldELEV",
            expression="!Z!",
            expression_type="PYTHON3",
            code_block="",
            field_type="DOUBLE",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )
        arcpy.AddMessage("Populated elevation fields")
    # Step 7: Calculate validation fields
        arcpy.SetProgressorLabel("Calculating elevation fields...")
        nonnull = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="CheckPoints",
            selection_type="NEW_SELECTION",
            where_clause="FldELEV IS NOT NULL And GrELEV IS NOT NULL",
            invert_where_clause=None
            )
        arcpy.management.CalculateField(
            in_table=nonnull,
            field="ElevDIFF",
            expression="!FldELEV! - !GrELEV!",
            expression_type="PYTHON3",
            code_block="",
            field_type="DOUBLE",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )
        arcpy.management.CalculateField(
            in_table=nonnull,
            field="ElevDIFF",
            expression="Abs($feature.ElevDIFF)",
            expression_type="ARCADE",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )
        arcpy.management.CalculateField(
            in_table=nonnull,
            field="Status",
            expression="cat(!ElevDIFF!)",
            expression_type="PYTHON3",
            code_block="""def cat(ElevDIFF):
            if ElevDIFF <= 1:
                return "P"
            elif ElevDIFF > 1:
                return "F"
            """,
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )  
        arcpy.AddMessage("Calculated validation fields")   
    # Step 8: Buffer the test points
        arcpy.SetProgressorLabel("Buffering test points...")
        arcpy.analysis.Buffer(
            in_features="CheckPoints",
            out_feature_class="CheckPoints_Buffer",
            buffer_distance_or_field=distanceb,
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="NONE",
            dissolve_field=None,
            method="PLANAR"
            )
        arcpy.AddMessage("Buffered test points")
    # Step 9: Generate zonal statistics for the buffered points and join to the test points
        arcpy.SetProgressorLabel("Generating zonal statistics...")
        arcpy.ia.ZonalStatisticsAsTable(
            in_zone_data="CheckPoints_Buffer",
            zone_field="OBJECTID",
            in_value_raster=dem,
            out_table="ZonalStat_CheckPtsBfr"
            )
        arcpy.management.JoinField(
            in_data="CheckPoints",
            in_field="OBJECTID",
            join_table="ZonalStat_CheckPtsBfr",
            join_field="OBJECTID"
            )
        arcpy.AddMessage("Generated zonal statistics")
    # Step 10: Populate Comment field and recalculate Status field for exceptions based on zonal statistics
        arcpy.SetProgressorLabel("Evaluating test points...")
        selectfails = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="CheckPoints",
            selection_type="NEW_SELECTION",
            where_clause="ZonalStat_CheckPts_Bfr.MIN <= (CheckPoints.FldELEV + 1) And \
            ZonalStat_CheckPts_Bfr.MAX >= (CheckPoints.FldELEV - 1) And Status = 'F'",
            invert_where_clause=None
            )
        exceptions = int(arcpy.management.GetCount(selectfails)[0])
        if exceptions > 0:
            arcpy.management.CalculateField(
                in_table=selectfails,
                field="Comment",
                expression='"Passed due to 38\' buffer"',
                expression_type="PYTHON3",
                code_block="",
                field_type="TEXT",
                enforce_domains="NO_ENFORCE_DOMAINS"
                )
            arcpy.management.CalculateField(
                in_table=selectfails,
                field="Status",
                expression='"EX"',
                expression_type="PYTHON3",
                code_block="",
                field_type="TEXT",
                enforce_domains="NO_ENFORCE_DOMAINS"
                )
        arcpy.AddMessage("Evaluated status of test points")
    # Give passing score
        arcpy.SetProgressorLabel("Scoring FBS Check...")
        passing = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="CheckPoints",
            selection_type="NEW_SELECTION",
            where_clause="Status IN ('EX', 'P')",
            invert_where_clause=None
        )
        passing = int(arcpy.GetCount_management(passing).getOutput(0))
        total = int(arcpy.GetCount_management("CheckPoints").getOutput(0))
        failed = total-passing
        score = passing/total*100
        if score >= 95:
            message = "FBS Check passed with " + str(round(score, 2)) + "%:"
            arcpy.AddMessage(message)
            lines = [(str(total)+" points audited"), \
                     (str(passing)+" points passed"), \
                        (str(failed)+" points failed"), \
                            (str(exceptions)+" points excepted")]
            for line in lines:
                    arcpy.AddMessage("\t"+line)
        else:
            message = "FBS Check failed with " + str(round(score, 2)) + "%:"
            arcpy.AddMessage(message)
            lines = [(str(total)+" points audited"), \
                     (str(passing)+" points passed"), \
                        (str(failed)+" points failed"), \
                            (str(exceptions)+" points excepted")]
            for line in lines:
                    arcpy.AddMessage("\t"+line)
        arcpy.management.SelectLayerByAttribute("CheckPoints","CLEAR_SELECTION")

########################################################################################

class FBSCheck_2D(object):
    def __init__(self):
        self.label = "FBS Check - 2D BLE"
        self.description = "Perform a Flood Boundary Standards check with test point generation," \
        + " geoprocessing, and comparison of DEM and generated WSEL TIN. NOTE: For best results," \
            + " perform manual edits to 2 inputs before processing:" \
            + " \n1) Convert relevant Zone A flood hazard area polygons to line and merge" \
                + "\n2) Run Elevation Void Fill (Raster Functions) on the WSE01PCT raster with Short Range IDW Radius = 20"

    def getParameterInfo(self):
    # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        distancep = arcpy.Parameter(
            name='Test Point Distance',
            displayName='Test Point Distance',
            datatype='GPLinearUnit',
            direction='Input',
            parameterType='Required')
        lineshp = arcpy.Parameter(
            name='Input Flood Hazard Line/s',
            displayName='Input Flood Hazard Line/s',
            datatype='GPLayer',
            direction='Input',
            parameterType='Required')
        proj = arcpy.Parameter(
            displayName="Local Projected Coordinate System",
            name="Local Projected Coordinate System",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")
        dem = arcpy.Parameter(
            name='Input Surface Raster',
            displayName='Input Surface Raster',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required')
        wse01pct = arcpy.Parameter(
            name='Input WSE 1% Raster with Elevation Void Fill',
            displayName='Input WSE 1% Raster with Elevation Void Fill',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required')
        distanceb = arcpy.Parameter(
            name='Buffer Distance',
            displayName='Buffer Distance',
            datatype='GPLinearUnit',
            direction='Input',
            parameterType='Required')
        
        params = [folder, distancep, lineshp, dem, wse01pct, distanceb]
        return params
    
    def updateParameters(self, parameters):
    # Set default values if not entered
        distancep = parameters[1]
        if not distancep.altered:
            distancep.values = "100 Feet" # default test point distance value
        distanceb = parameters[5]
        if not distanceb.altered:
            distanceb.values = "38 Feet" # default buffer distance value
        return

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
    # Step 1: Setup variables and file gdb
        arcpy.env.addOutputsToMap = True
        arcpy.env.overwriteOutput = True
        folder = parameters[0].valueAsText
        arcpy.management.CreateFileGDB(fr"{folder}", "FBS_Check.gdb", "CURRENT")
        arcpy.env.workspace = fr"{folder}\\FBS_Check.gdb"
        distancep = parameters[1].valueAsText
        floodlines = parameters[2].valueAsText
        fc_count = int(arcpy.GetCount_management(floodlines).getOutput(0))
        if fc_count > 1:
            arcpy.AddMessage(f"{floodlines} has not been merged into a single feature.")
        else:
            arcpy.AddMessage(f"{floodlines} has {fc_count} feature.")
        spatial_ref = arcpy.Describe(floodlines).spatialReference
        arcpy.AddMessage(f"{floodlines} is in {spatial_ref.name}")
        if "Projected" not in spatial_ref.type:
            arcpy.AddError(spatial_ref.name + " is angular; this is not recommended. Distances should be estimated using projected coordinate systems.")
        dem = parameters[3].valueAsText
        wse01pct = parameters[4].valueAsText
        distanceb = parameters[5].valueAsText
    # Step 2: Generate test points
        arcpy.SetProgressorLabel("Generating test points...")
        arcpy.management.GeneratePointsAlongLines(
            Input_Features=floodlines,
            Output_Feature_Class="CheckPoints",
            Point_Placement="DISTANCE",
            Distance=distancep,
            Percentage=None,
            Include_End_Points="NO_END_POINTS"
            )
        arcpy.AddMessage("Generated test points")
    # Step 3: Extract values from expanded 1% raster
        arcpy.sa.ExtractMultiValuesToPoints(
            in_point_features="CheckPoints",
            in_rasters=fr"{wse01pct} WSEL;{dem} Ground",
            bilinear_interpolate_values="NONE"
            )
    # Step 4: Calculate GrELEV and delete temporary field
        arcpy.SetProgressorLabel("Populating elevation fields...")
        arcpy.management.CalculateField(
            in_table="CheckPoints",
            field="GrELEV",
            expression="!Ground!",
            expression_type="PYTHON3",
            code_block="",
            field_type="DOUBLE",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )
        arcpy.management.DeleteField(
            "CheckPoints", 
            "Ground", 
            "DELETE_FIELDS"
            )
    # Step 5: Calculate FldELEV and delete temporary field
        arcpy.management.CalculateField(
            in_table="CheckPoints",
            field="FldELEV",
            expression="!WSEL!",
            expression_type="PYTHON3",
            code_block="",
            field_type="DOUBLE",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )
        arcpy.management.DeleteField(
            "CheckPoints", 
            "WSEL", 
            "DELETE_FIELDS"
            )
        arcpy.AddMessage("Populated elevation fields")
    # Step 6: Calculate validation fields
        arcpy.SetProgressorLabel("Calculating elevation fields...")
        nonnull = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="CheckPoints",
            selection_type="NEW_SELECTION",
            where_clause="FldELEV IS NOT NULL And GrELEV IS NOT NULL",
            invert_where_clause=None
            )
        arcpy.management.CalculateField(
            in_table=nonnull,
            field="ElevDIFF",
            expression="!FldELEV! - !GrELEV!",
            expression_type="PYTHON3",
            code_block="",
            field_type="DOUBLE",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )
        arcpy.management.CalculateField(
            in_table=nonnull,
            field="ElevDIFF",
            expression="Abs($feature.ElevDIFF)",
            expression_type="ARCADE",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )
        arcpy.management.CalculateField(
            in_table=nonnull,
            field="Status",
            expression="cat(!ElevDIFF!)",
            expression_type="PYTHON3",
            code_block="""def cat(ElevDIFF):
            if ElevDIFF <= 1:
                return "P"
            elif ElevDIFF > 1:
                return "F"
            """,
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
            )  
        arcpy.AddMessage("Calculated validation fields")   
    # Step 7: Buffer the test points
        arcpy.SetProgressorLabel("Buffering test points...")
        arcpy.analysis.Buffer(
            in_features="CheckPoints",
            out_feature_class="CheckPoints_Buffer",
            buffer_distance_or_field=distanceb,
            line_side="FULL",
            line_end_type="ROUND",
            dissolve_option="NONE",
            dissolve_field=None,
            method="PLANAR"
            )
        arcpy.AddMessage("Buffered test points")
    # Step 8: Generate zonal statistics for the buffered points and join to the test points
        arcpy.SetProgressorLabel("Generating zonal statistics...")
        arcpy.ia.ZonalStatisticsAsTable(
            in_zone_data="CheckPoints_Buffer",
            zone_field="OBJECTID",
            in_value_raster=dem,
            out_table="ZonalStat_CheckPtsBfr"
            )
        arcpy.management.JoinField(
            in_data="CheckPoints",
            in_field="OBJECTID",
            join_table="ZonalStat_CheckPtsBfr",
            join_field="OBJECTID"
            )
        arcpy.AddMessage("Generated zonal statistics")
    # Step 9: Populate Comment field and recalculate Status field for exceptions based on zonal statistics
        arcpy.SetProgressorLabel("Evaluating test points...")
        selectfails = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="CheckPoints",
            selection_type="NEW_SELECTION",
            where_clause="ZonalStat_CheckPts_Bfr.MIN <= (CheckPoints.FldELEV + 1) And \
            ZonalStat_CheckPts_Bfr.MAX >= (CheckPoints.FldELEV - 1) And Status = 'F'",
            invert_where_clause=None
            )
        exceptions = int(arcpy.management.GetCount(selectfails)[0])
        if exceptions > 0:
            arcpy.management.CalculateField(
                in_table=selectfails,
                field="Comment",
                expression='"Passed due to 38\' buffer"',
                expression_type="PYTHON3",
                code_block="",
                field_type="TEXT",
                enforce_domains="NO_ENFORCE_DOMAINS"
                )
            arcpy.management.CalculateField(
                in_table=selectfails,
                field="Status",
                expression='"EX"',
                expression_type="PYTHON3",
                code_block="",
                field_type="TEXT",
                enforce_domains="NO_ENFORCE_DOMAINS"
                )
        arcpy.AddMessage("Evaluated status of test points")
    # Give passing score
        arcpy.SetProgressorLabel("Scoring FBS Check...")
        passing = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="CheckPoints",
            selection_type="NEW_SELECTION",
            where_clause="Status IN ('EX', 'P')",
            invert_where_clause=None
        )
        passing = int(arcpy.GetCount_management(passing).getOutput(0))
        total = int(arcpy.GetCount_management("CheckPoints").getOutput(0))
        failed = total-passing
        score = passing/total*100
        if score >= 95:
            message = "FBS Check passed with " + str(round(score, 2)) + "%:"
            arcpy.AddMessage(message)
            lines = [(str(total)+" points audited"), \
                     (str(passing)+" points passed"), \
                        (str(failed)+" points failed"), \
                            (str(exceptions)+" points excepted")]
            for line in lines:
                    arcpy.AddMessage("\t"+line)
        else:
            message = "FBS Check failed with " + str(round(score, 2)) + "%:"
            arcpy.AddMessage(message)
            lines = [(str(total)+" points audited"), \
                     (str(passing)+" points passed"), \
                        (str(failed)+" points failed"), \
                            (str(exceptions)+" points excepted")]
            for line in lines:
                    arcpy.AddMessage("\t"+line)
        arcpy.management.SelectLayerByAttribute("CheckPoints","CLEAR_SELECTION")

########################################################################################

class A5Check_Part1(object):
    def __init__(self):
        self.label = "A5 Check Part 1"
        self.description = "Perform an A5 check with test point generation" \
        + "and extraction/interpolation of WSE 1 plus/1 minus values for later comparison to DEM." \
            + " NOTE: For best results, perform manual edits to input before processing: " \
                + "\n Extract and merge relevant flood hazard lines"

    def getParameterInfo(self):
    # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        template = arcpy.Parameter(
            name='A5 Points Template',
            displayName='A5 Points Template',
            datatype='DEShapeFile',
            direction='Input',
            parameterType='Required')
        huc = arcpy.Parameter(
            name='Study Area HUC12',
            displayName='Study Area HUC12',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        huc.filter.list = ["Polygon"]
        quads = arcpy.Parameter(
            name='USGS Quads',
            displayName='USGS Quads',
            datatype='DELayer',
            direction='Input',
            parameterType='Optional')
        distancep = arcpy.Parameter(
            name='Test Point Distance',
            displayName='Test Point Distance',
            datatype='GPLinearUnit',
            direction='Input',
            parameterType='Required')
        floodlines = arcpy.Parameter(
            name='Input Flood Hazard Line/s',
            displayName='Input Flood Hazard Line/s',
            datatype='GPLayer',
            direction='Input',
            parameterType='Required')
        proj = arcpy.Parameter(
            displayName="Local Projected Coordinate System",
            name="Local Projected Coordinate System",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")
        dem = arcpy.Parameter(
            name='Input Surface Raster',
            displayName='Input Surface Raster',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required')
        wse01min = arcpy.Parameter(
            name='Input WSE 1 Minus Raster',
            displayName='Input WSE 1 Minus Raster',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required')
        wse01plus = arcpy.Parameter(
            name='Input WSE 1 Plus Raster',
            displayName='Input WSE 1 Plus Raster',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required')
        
        params = [folder, template, huc, quads, distancep, floodlines, proj, dem, wse01min, wse01plus]
        return params
    
    def updateParameters(self, parameters):
        distancep = parameters[4]
    # Set default value if not entered
        if not distancep.altered:
            distancep.values = "200 Feet" # default test point distance value
        return

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
    # Step 1: Setup variables and file gdb
        arcpy.env.addOutputsToMap = True
        arcpy.env.overwriteOutput = True
        folder = parameters[0].valueAsText
        arcpy.management.CreateFileGDB(fr"{folder}", "A5_Check.gdb", "CURRENT")
        arcpy.env.workspace = fr"{folder}\\A5_Check.gdb"
        template = parameters[1].valueAsText
        huc = parameters[2].valueAsText
        quads = parameters[3].valueAsText
        distancep = parameters[4].valueAsText
        floodlines = parameters[5].valueAsText
        fc_count = int(arcpy.GetCount_management(floodlines).getOutput(0))
        if fc_count > 1:
            arcpy.AddMessage("{0} has not been merged into a single feature.".format(floodlines))
        else:
            arcpy.AddMessage("{0} has {1} feature.".format(floodlines, fc_count))
        prjctn = parameters[6].valueAsText
        if "PROJECTION" not in prjctn:
            arcpy.AddError(prjctn + " is angular; this is not recommended. Distances should be estimated using projected coordinate systems.")
        dem = parameters[7].valueAsText
        wse01min = parameters[8].valueAsText
        wse01plus = parameters[9].valueAsText
    # Step 2: Create template point feature class
        arcpy.management.CreateFeatureclass(
        fr"{folder}\\A5_Check.gdb", 
        "A5_Test_Pnts", 
        "POINT", 
        template, 
        "DISABLED", 
        "ENABLED", 
        prjctn
        )
    # Step 3: Select quads in the BLE project footprint and save for later
        if quads:
            arcpy.management.SelectLayerByLocation(
                in_layer=quads,
                overlap_type="INTERSECT",
                select_features=huc,
                search_distance=None,
                selection_type="NEW_SELECTION",
                invert_spatial_relationship="NOT_INVERT"
                )
            arcpy.conversion.FeatureClassToFeatureClass(
                "Resources.GIS.USGS_Quad_24k", 
                fr"{folder}\\A5_Check.gdb", 
                "USGS_24k_Quads"
                )
    # Step 4: Generate test points, load to template point feature class and attribute unique IDs
        arcpy.SetProgressor("step", "Generating test points...")
        arcpy.management.GeneratePointsAlongLines(
            Input_Features=floodlines,
            Output_Feature_Class="A5_Test_Pnts_blank",
            Point_Placement="DISTANCE",
            Distance=distancep
            )
        arcpy.management.Append(
            inputs="A5_Test_Pnts_blank",
            target="A5_Test_Pnts",
            schema_type="NO_TEST"
            )
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "Id", 
            "SequentialNumber()", 
            "PYTHON3", 
            """rec=0
def SequentialNumber():
    global rec
    pStart = 1
    pInterval = 1
    if (rec == 0):
        rec = pStart
    else:
        rec = rec + pInterval
    return rec""", 
    "LONG"
    )
        arcpy.AddMessage("Generated test points with unique IDs")
    # Step 5: Extract WSE and ELEV values to points and populate, clean up attributes
        arcpy.ResetProgressor()
        arcpy.SetProgressor("step", "Extracting elevation values...")
        arcpy.sa.ExtractMultiValuesToPoints(
            in_point_features="A5_Test_Pnts", 
            in_rasters=[[dem, "Gr_EL_1"]], 
            bilinear_interpolate_values="NONE"
            )
        arcpy.ResetProgressor()
        arcpy.SetProgressor("step", "Extracting WSE minus values...")
        arcpy.sa.ExtractMultiValuesToPoints(
            in_point_features="A5_Test_Pnts", 
            in_rasters=[[wse01min, "F1PCT_MINUS_1"]], 
            bilinear_interpolate_values="NONE"
            )
        arcpy.ResetProgressor()
        arcpy.SetProgressor("step", "Extracting WSE plus values...")
        arcpy.sa.ExtractMultiValuesToPoints(
            in_point_features="A5_Test_Pnts", 
            in_rasters=[[wse01plus, "F1PCT_PLUS_1"]], 
            bilinear_interpolate_values="NONE"
            )
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "F1PCT_MINUS", 
            "!F1PCT_MINUS_1!", 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "F1PCT_PLUS", 
            "!F1PCT_PLUS_1!", 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "Gr_EL", 
            "!Gr_EL_1!", 
            "PYTHON3"
            )
        arcpy.management.DeleteField(
            "A5_Test_Pnts", 
            "F1PCT_PLUS_1;F1PCT_MINUS_1;Gr_EL_1", 
            "DELETE_FIELDS"
            )
        arcpy.AddMessage("Extracted WSE and elevation values")
    # Step 6: Integerize the WSE rasters
        arcpy.SetProgressorLabel("Calculating integer rasters...")
        int_wse01min = arcpy.sa.RasterCalculator([wse01min, 10], ["BLE_WSE_01min", "x"], "Int(BLE_WSE_01min*x)"); int_wse01min.save(fr"{folder}\\A5_Check.gdb\int_WSE_01min")
        int_wse01plus = arcpy.sa.RasterCalculator([wse01plus, 10], ["BLE_WSE_01plus", "x"], "Int(BLE_WSE_01plus*x)"); int_wse01plus.save(fr"{folder}\\A5_Check.gdb\int_WSE_01plus")
        arcpy.AddMessage("Created integer rasters")
    # Step 7: Convert integer WSE rasters to polygon
        arcpy.ResetProgressor()
        arcpy.SetProgressor("step", "Converting int minus raster to polygon...")
        arcpy.conversion.RasterToPolygon(
            "int_WSE_01plus", 
            "int_WSE01plus_poly", 
            "NO_SIMPLIFY", 
            "Value", 
            "SINGLE_OUTER_PART", 
            None
            )
        arcpy.ResetProgressor()
        arcpy.SetProgressor("step", "Converting int plus raster to polygon...")
        arcpy.conversion.RasterToPolygon(
            "int_WSE_01min", 
            "int_WSE01min_poly", 
            "NO_SIMPLIFY", 
            "Value", 
            "SINGLE_OUTER_PART", 
            None
            )
        arcpy.AddMessage("Converted integer rasters to polygon")
    # Step 8: Select null F1PCT_MINUS points and populate from nearby raster
        nullmin = arcpy.management.SelectLayerByAttribute(
            "A5_Test_Pnts", 
            "NEW_SELECTION", 
            "F1PCT_MINUS IS NULL", 
            None
            )
        null_count = int(arcpy.GetCount_management(nullmin).getOutput(0))
        if null_count > 0:
            # try 5000 ft search radius
            arcpy.ResetProgressor()
            arcpy.SetProgressor("step", "Joining closest WSE minus values...")
            arcpy.analysis.SpatialJoin(
                target_features=nullmin, 
                join_features="int_WSE01min_poly", 
                out_feature_class="A5_Test_Pnts_WSE01min_Join", 
                join_operation="JOIN_ONE_TO_ONE", 
                join_type="KEEP_ALL", 
                match_option="CLOSEST", 
                search_radius="5000 Feet"
                )
            arcpy.AddMessage(f"Joined int_WSE01min_poly to test points")
            arcpy.management.JoinField(
                "A5_Test_Pnts", 
                "Id", 
                "A5_Test_Pnts_WSE01min_Join", 
                "Id", 
                "gridcode"
                )
            gridvalues = arcpy.management.SelectLayerByAttribute(
                "A5_Test_Pnts", 
                "NEW_SELECTION", 
                "gridcode IS NOT NULL", 
                None
                )
            arcpy.management.CalculateField(
                gridvalues, 
                "F1PCT_MINUS", 
                "!gridcode! / 10", 
                "PYTHON3"
                )
            arcpy.management.DeleteField(
                "A5_Test_Pnts", 
                "gridcode", 
                "DELETE_FIELDS"
                )
            nullmin = arcpy.management.SelectLayerByAttribute(
                "A5_Test_Pnts", 
                "NEW_SELECTION", 
                "F1PCT_MINUS IS NULL", 
                None
                )
            null_count = int(arcpy.GetCount_management(nullmin).getOutput(0))
            if null_count > 0:
                arcpy.AddMessage(f"5000 ft search radius returned {null_count} null F1PCT_MINUS values. Consider deleting based on location.")
            else:
                arcpy.AddMessage("Test points have no null F1PCT_MINUS values after 5000 ft spatial join.")
        else:
            arcpy.AddMessage("Test points have no null F1PCT_MINUS values.")
    # Step 9: Select null F1PCT_PLUS points and populate from nearby raster
        nullplus = arcpy.management.SelectLayerByAttribute(
            "A5_Test_Pnts", 
            "NEW_SELECTION", 
            "F1PCT_PLUS IS NULL", 
            None
            )
        null_count = int(arcpy.GetCount_management(nullplus).getOutput(0))
        if null_count > 0:
            # try 5000 ft search radius
            arcpy.ResetProgressor()
            arcpy.SetProgressor("step", "Joining closest WSE plus values...")
            arcpy.analysis.SpatialJoin(
            target_features=nullplus, 
            join_features="int_WSE01plus_poly", 
            out_feature_class="A5_Test_Pnts_WSE01plus_Join", 
            join_operation="JOIN_ONE_TO_ONE", 
            join_type="KEEP_ALL", 
            match_option="CLOSEST", 
            search_radius="5000 Feet"
            )
            arcpy.AddMessage(f"Joined int_WSE01plus_poly to test points")
            arcpy.management.JoinField(
                "A5_Test_Pnts", 
                "Id", 
                "A5_Test_Pnts_WSE01plus_Join", 
                "Id", 
                "gridcode"
                )
            gridvalues = arcpy.management.SelectLayerByAttribute(
                "A5_Test_Pnts", 
                "NEW_SELECTION", 
                "gridcode IS NOT NULL", 
                None
                )
            arcpy.management.CalculateField(
                gridvalues, 
                "F1PCT_PLUS", 
                "!gridcode! / 10", 
                "PYTHON3"
                )
            arcpy.management.DeleteField(
                "A5_Test_Pnts", 
                "gridcode", 
                "DELETE_FIELDS"
                )
            nullplus = arcpy.management.SelectLayerByAttribute(
                "A5_Test_Pnts", 
                "NEW_SELECTION", 
                "F1PCT_PLUS IS NULL", 
                None
                )
            null_count = int(arcpy.GetCount_management(nullplus).getOutput(0))
            if null_count > 0:
                arcpy.AddMessage(f"5000 ft search radius returned {null_count} null F1PCT_PLUS values. Consider deleting based on location.")
            else: 
                arcpy.AddMessage("Test points have no null F1PCT_PLUS values after 5000 ft spatial join.")
        else:
            arcpy.AddMessage("Test points have no null F1PCT_PLUS values.")
        arcpy.SetProgressorLabel("Cleaning up files...")
        # Delete intermediate files
        arcpy.management.Delete(
            "A5_Test_Pnts_blank;int_WSE_01min;int_WSE_01plus;\
            A5_Test_Pnts_WSE01min_Join;A5_Test_Pnts_WSE01plus_Join", 
            ''
            )
        arcpy.AddMessage("Deleted intermediate files")

########################################################################################

class A5Check_Part2(object):
    def __init__(self):
        self.label = "A5 Check Part 2"
        self.description = "Complete the A5 check after manual inspection of test points from Part 1" \
            + " with geoprocessing, horizontal and vertical comparison with the DEM, comparison of" \
                + " WSE 1 plus - 1 minus value ranges, and scoring and attribution of test points"

    def getParameterInfo(self):
    # Define parameters
        filegdb = arcpy.Parameter(
            name='Part 1 File GDB',
            displayName='Part 1 File GDB',
            datatype='DEWorkspace',
            direction='Input',
            parameterType='Required')
        distancet = arcpy.Parameter(
            name='Vertical Tolerance',
            displayName='Vertical Tolerance',
            datatype='GPString',
            direction='Input',
            parameterType='Required')
        distanceb = arcpy.Parameter(
            name='Horizontal Tolerance',
            displayName='Horizontal Tolerance (Buffer Distance)',
            datatype='GPLinearUnit',
            direction='Input',
            parameterType='Required')
        dem = arcpy.Parameter(
            name='Input Surface Raster',
            displayName='Input Surface Raster',
            datatype='GPRasterLayer',
            direction='Input',
            parameterType='Required')
        huc = arcpy.Parameter(
            name='Study Area HUC12',
            displayName='Study Area HUC12',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        huc.filter.list = ["Polygon"]
        studylines = arcpy.Parameter(
            name='S_Studies_Ln',
            displayName='S_Studies_Ln',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        studylines.filter.list = ["Polyline"]
        
        params = [filegdb, distancet, distanceb, dem, huc, studylines]
        return params
    
    def updateParameters(self, parameters):
    # Set default values if not entered
        distancet = parameters[1]
        if not distancet.altered:
            distancet.value = "2.5" # default vertical tolerance value
        distanceb = parameters[2]
        if not distanceb.altered:
            distanceb.values = "75 Feet" # default horizontal tolerance value
        return

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
    # Step 1: Setup variables
        arcpy.env.addOutputsToMap = True
        arcpy.env.overwriteOutput = True
        filegdb = parameters[0].valueAsText
        end = filegdb.rindex("\\")
        folder = filegdb[:end]
        arcpy.env.workspace = filegdb
        distancet = parameters[1].valueAsText
        distanceb = parameters[2].valueAsText
        dem = parameters[3].valueAsText
        huc = parameters[4].valueAsText
        studylines = parameters[5].valueAsText
    # Step 2: Populate minus and plus fields
        arcpy.SetProgressorLabel("Populating minus and plus fields...")
        # Calculate minus tolerance
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "F1PCT_MIN_T", 
            f"!F1PCT_MINUS! - {distancet}", 
            "PYTHON3"
            )
        # Calculate plus tolerance
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "F1PCT_PL_T", 
            f"!F1PCT_PLUS! + {distancet}", 
            "PYTHON3"
            )
        # Range Difference: Subtract minus from plus
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "diff", 
            "!F1PCT_PLUS! - !F1PCT_MINUS!", 
            "PYTHON3", 
            '', 
            "DOUBLE"
            )
        # Select negative range differences
        negdiff = arcpy.management.SelectLayerByAttribute(
            "A5_Test_Pnts", 
            "NEW_SELECTION", 
            "diff < 0", 
            None
            )
        negdiff_count = int(arcpy.GetCount_management(negdiff).getOutput(0))
        if negdiff_count > 0:
            arcpy.AddMessage(f"{negdiff_count} rows with plus values greater than minus values.")
            # Save the original values
            arcpy.management.CalculateField(
                negdiff, 
                "F1PCT_MINUS_orig", 
                "!F1PCT_MINUS!", 
                "PYTHON3", 
                '', 
                "DOUBLE"
                )
            arcpy.management.CalculateField(
                negdiff, 
                "F1PCT_PLUS_orig", 
                "!F1PCT_PLUS!", 
                "PYTHON3", 
                '', 
                "DOUBLE"
                )
            # Set min equal to original plus
            arcpy.management.CalculateField(
                negdiff, 
                "F1PCT_MINUS", 
                "!F1PCT_PLUS_orig!", 
                "PYTHON3"
                )
            # Set plus equal to original minus
            arcpy.management.CalculateField(
                negdiff, 
                "F1PCT_PLUS", 
                "!F1PCT_MINUS_orig!", 
                "PYTHON3"
                )
            # Range Difference: Subtract new minus from new plus
            arcpy.management.CalculateField(
                negdiff, 
                "diff_adj", 
                "!F1PCT_PLUS! - !F1PCT_MINUS!", 
                "PYTHON3", 
                '', 
                "DOUBLE"
                )
            arcpy.AddMessage("Plus and minus values rectified.")
        else:
            # Accept original values
            arcpy.AddMessage("All plus values greater than minus values.")
        arcpy.management.SelectLayerByAttribute(
            "A5_Test_Pnts",
            "CLEAR_SELECTION"
            )
        # Vertical Difference: Compare DEM to DEM less 2.5 tolerance
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "V_MIN_DIF", 
            "!Gr_EL! - !F1PCT_MIN_T!", 
            "PYTHON3"
            )
        # Vertical Difference: Compare DEM to DEM plus 2.5ft tolerance
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "V_PL_DIF", 
            "!F1PCT_PL_T! - !Gr_EL!", 
            "PYTHON3"
            )
        arcpy.AddMessage("Populated minus and plus fields")
    # Step 3: Buffer and generate zonal statistics
        arcpy.SetProgressorLabel("Buffering test points...")
        arcpy.analysis.PairwiseBuffer(
            "A5_Test_Pnts", 
            "A5_Test_Pnts_PairwiseBuffer", 
            distanceb
            )
        arcpy.AddMessage("Buffered test points")
        arcpy.SetProgressorLabel("Generating zonal statistics...")
        arcpy.sa.ZonalStatisticsAsTable(
            "A5_Test_Pnts_PairwiseBuffer", 
            "Id", 
            dem, 
            "ZonalMinMax_A5_Test", 
            "DATA", 
            "MIN_MAX"
            )
        arcpy.management.JoinField(
            "A5_Test_Pnts", 
            "Id", 
            "ZonalMinMax_A5_Test", 
            "Id", 
            "COUNT;AREA;MIN;MAX"
            )
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "Gr_EL_Min", 
            "!MIN!", 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "Gr_EL_Max", 
            "!MAX!", 
            "PYTHON3"
            )
        # Horizontal Difference: Compare DEM max to 1pct minus WSEL
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "H_MIN_DIF", 
            "!Gr_EL_Max! - !F1PCT_MINUS!", 
            "PYTHON3"
            )
        # Horizontal Difference: Compare DEM min to 1pct plus WSEL
        arcpy.management.CalculateField(
            "A5_Test_Pnts", 
            "H_PL_DIF", 
            "!F1PCT_PLUS! - !Gr_EL_Min!", 
            "PYTHON3"
            )
        arcpy.AddMessage("Generated zonal statistics")
        arcpy.conversion.FeatureClassToFeatureClass(
            "A5_Test_Pnts", 
            filegdb, 
            "A5_Raw_Results"
            )
        # Select negative horizontal differences
        horizfails = arcpy.management.SelectLayerByAttribute(
            "A5_Raw_Results", 
            "NEW_SELECTION", 
            "H_MIN_DIF < 0 Or H_PL_DIF < 0", 
            None
            )
        # Select negative vertical differences
        vertifails = arcpy.management.SelectLayerByAttribute(
            horizfails, 
            "ADD_TO_SELECTION", 
            "V_MIN_DIF < 0 Or V_PL_DIF < 0", 
            None
            )
        # Score as fails
        arcpy.management.CalculateField(
            vertifails, 
            "FAIL", 
            "1", 
            "PYTHON3"
            )
        # Score as passes
        passes = arcpy.management.SelectLayerByAttribute(
            "A5_Raw_Results", 
            "NEW_SELECTION", 
            "FAIL IS NULL", 
            None
            )
        arcpy.management.CalculateField(
            passes, 
            "PASS", 
            "1", 
            "PYTHON3"
            )
        arcpy.management.SelectLayerByAttribute(
            "A5_Raw_Results",
            "CLEAR_SELECTION"
            )
        arcpy.SetProgressorLabel(f"Intersecting results with {huc}...")
        # Intersect test points with HUC12 
        arcpy.analysis.Intersect(
            f"A5_Raw_Results #;{huc} #", 
            "A5_Raw_Results_HUC12", 
            "ALL", 
            None, 
            "POINT"
            )
        arcpy.SetProgressorLabel("Generating statistics by HUC12...")
        # Statistics by HUC12
        arcpy.analysis.Statistics(
            "A5_Raw_Results_HUC12", 
            "A5_Final_Results_HUC12", 
            "FAIL SUM;PASS SUM", 
            "huc12"
            )
        arcpy.AddMessage("Summarized test points by HUC12")
        arcpy.SetProgressorLabel("Calculating passing and scoring...")
        # Calculate passing and score
        arcpy.management.CalculateField(
            "A5_Final_Results_HUC12", 
            "PCT_PASS", 
            "func(!SUM_PASS!,!FREQUENCY!)", 
            "PYTHON3", 
            """def func(SUM_PASS,FREQUENCY):
            passing = SUM_PASS
            freq = FREQUENCY
            if passing:
                return passing / freq * 100
            else:
                return "FAIL"  
            """, 
            "DOUBLE"
            )
        arcpy.management.CalculateField(
            "A5_Final_Results_HUC12", 
            "PASS_FAIL", 
            "func(!PCT_PASS!)", 
            "PYTHON3", 
            """def func(PCT_PASS):
            score = PCT_PASS
            if score:
                if score >= 85:
                    return "PASS"
                else:
                    return "FAIL"
            else:
                return "FAIL"  
            """, 
            "TEXT"
            )
        arcpy.AddMessage("Scored test points by HUC12")
        arcpy.management.JoinField(
            "A5_Final_Results_HUC12", 
            "huc12", 
            "WBDHU12", 
            "huc12", 
            "name"
            )
        # Export Excel table
        arcpy.conversion.TableToExcel(
            "A5_Final_Results_HUC12", 
            fr"{folder}\\A5_Final_Results_HUC12.xlsx", 
            "ALIAS", 
            "CODE"
            )
        arcpy.management.CalculateField(
            studylines, 
            "WTR_NM", 
            "!WTR_NM!.title()", 
            "PYTHON3"
            )
        arcpy.SetProgressorLabel("Generating unique water names...")
        cursor = arcpy.da.SearchCursor(
            studylines, 
            ['FLD_ZONE', 'STATUS_TYPE', 'STUDY_TYPE', 'WTR_NM']
            )
        wtr_names = []
        for row in cursor:
            if row[3] is not None:
                wtr_name = row[3]
                wtr_names.append(wtr_name)
            else:
                continue
        for name in wtr_names:
            if "'" in name:
                apos = name.index("'")
                qname = name[:apos] + "'" + name[apos:]
                where_clause = f"WTR_NM = '{qname}'"
            else:
                where_clause = f"WTR_NM = '{name}'"
            stream = arcpy.management.SelectLayerByAttribute(
                studylines, 
                "NEW_SELECTION",
                where_clause, 
                None
                )
            stream_count = int(arcpy.GetCount_management(stream).getOutput(0))
            if stream_count > 1:
                # Generate unique Study Line WTR_NM_1
                arcpy.management.CalculateField(
                        stream, 
                        "WTR_NM_1", 
                        "SequentialNum(!WTR_NM!)", 
                        "PYTHON3", 
                        """rec=0
def SequentialNum(WTR_NM):
    global rec
    name = WTR_NM
    pStart = 1
    pInterval = 1
    if (rec == 0):
        rec = pStart
    else:
        rec = rec + pInterval
    return name + " " + str(rec)"""
    )
            else:
                arcpy.management.CalculateField(
                    stream, 
                    "WTR_NM_1", 
                    "!WTR_NM!", 
                    "PYTHON3"
                    )
        arcpy.management.SelectLayerByAttribute(
            studylines,
            "CLEAR_SELECTION"
            )
        del cursor
        arcpy.AddMessage("Generated unique water names")
        arcpy.SetProgressorLabel(f"Joining results to {studylines}...")
        # Join closest test points with Study Lines
        arcpy.analysis.SpatialJoin(
            target_features="A5_Raw_Results", 
            join_features=studylines, 
            out_feature_class="A5_Raw_Results_Studies_Ln", 
            join_operation="JOIN_ONE_TO_ONE", 
            join_type="KEEP_ALL",
            match_option="CLOSEST", 
            search_radius="500 Feet"
            )
        arcpy.AddMessage(f"Joined results to {studylines} within 500 ft")
        arcpy.SetProgressorLabel("Generating statistics by unique water name...")
        # Statistics by unique Study Line WTR_NM_1
        arcpy.analysis.Statistics(
            "A5_Raw_Results_Studies_Ln", 
            "A5_Final_Results_Studies_Ln", 
            "FAIL SUM;PASS SUM", 
            "WTR_NM_1"
           )
        arcpy.AddMessage("Summarized test points by Study Line")
        arcpy.SetProgressorLabel("Calculating passing and scoring...")
        # Calculate passing and score
        arcpy.management.CalculateField(
            "A5_Final_Results_Studies_Ln",
            "PCT_PASS",
            "func(!SUM_PASS!,!FREQUENCY!)",
            "PYTHON3",
            """def func(SUM_PASS,FREQUENCY):
            if SUM_PASS:
                return SUM_PASS / FREQUENCY * 100
            else:
                return 0""",
            "DOUBLE"
            )
        arcpy.management.CalculateField(
            "A5_Final_Results_Studies_Ln", 
            "PASS_FAIL", 
            "func(!PCT_PASS!)", 
            "PYTHON3", 
            """def func(PCT_PASS):
            if PCT_PASS >= 85:
                return "PASS"
            else:
                return "FAIL"
            """, 
            "TEXT"
            )
        arcpy.AddMessage("Scored test points by Study Line")
        arcpy.management.JoinField(
            studylines, 
            "WTR_NM_1", 
            "A5_Final_Results_Studies_Ln", 
            "WTR_NM_1", 
            "FREQUENCY;SUM_FAIL;SUM_PASS;PCT_PASS;PASS_FAIL"
            )
        # Export Excel table
        arcpy.conversion.TableToExcel(
            "A5_Final_Results_Studies_Ln", 
            fr"{folder}\\A5_Final_Results_Studies_Ln.xlsx", 
            "ALIAS", 
            "CODE"
            )
        arcpy.SetProgressorLabel("Populating A5 fields...")
        insuff = arcpy.management.SelectLayerByAttribute(
            studylines, 
            "NEW_SELECTION", 
            "FREQUENCY < 20 And (FLD_ZONE = 'A' Or FLD_ZONE = '1 PCT-ANNUAL-CHANCE FLOOD HAZARD CONTAINED') And STATUS_TYPE = 'BEING STUDIED' And STUDY_TYPE LIKE '%APPROXIMATE%'",
            None
            )
        arcpy.management.CalculateField(
            insuff, 
            "A5_COMPARE", 
            "None", 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            insuff, 
            "A5_CMT", 
            '"Insufficient sample points for A5 analysis"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            insuff, 
            "A5_SRC", 
            '"Compass A5 analysis, Effective Zone A floodplain boundaries, 1%+ and 1%- BLE WSEL data"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            insuff, 
            "A5_URL", 
            '"https://hazards.fema.gov"', 
            "PYTHON3"
            )
        suff = arcpy.management.SelectLayerByAttribute(
            studylines, 
            "NEW_SELECTION", 
            "FREQUENCY >= 20 And FLD_ZONE = 'A' And STATUS_TYPE = 'BEING STUDIED' And STUDY_TYPE LIKE '%APPROXIMATE%'", 
            None
            )
        arcpy.management.CalculateField(
            suff, 
            "A5_COMPARE", 
            "func(!PASS_FAIL!)", 
            "PYTHON3", 
            """def func(PASS_FAIL):
            score = PASS_FAIL
            if score == "PASS":
                return 10
            else:
                return 11
            """
            )
        PASS = arcpy.management.SelectLayerByAttribute(
            studylines, 
            "NEW_SELECTION", 
            "A5_COMPARE = 10", 
            None
            )
        arcpy.management.CalculateField(
            PASS, 
            "A5_CMT", 
            '"Passes A5 analysis: Percent of test points passing is greater than or equal to the passing threshold of the project’s defined Risk Class"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            PASS, 
            "A5_SRC", 
            '"Compass A5 analysis, Effective Zone A floodplain boundaries, 1%+ and 1%- BLE WSEL data"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            PASS, 
            "A5_URL", 
            '"https://hazards.fema.gov"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            PASS, 
            "REASON", 
            '"Study passes A5 Comparison Check"', 
            "PYTHON3"
            )
        FAIL = arcpy.management.SelectLayerByAttribute(
            studylines, 
            "NEW_SELECTION", 
            "A5_COMPARE = 11", 
            None
            )
        arcpy.management.CalculateField(
            FAIL, 
            "A5_CMT", 
            '"Fails A5 analysis: Percent of test points passing is less than the passing threshold of the project’s defined Risk Class"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            FAIL, 
            "A5_SRC", 
            '"Compass A5 analysis, Effective Zone A floodplain boundaries, 1%+ and 1%- BLE WSEL data"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            FAIL, 
            "A5_URL", 
            '"https://hazards.fema.gov"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            FAIL, 
            "REASON", 
            '"Study fails A5 Comparison Check"', 
            "PYTHON3"
            )
        arcpy.management.SelectLayerByAttribute(
            studylines,
            "CLEAR_SELECTION"
            )
        arcpy.management.CalculateField(
            studylines, 
            "VALIDATION_STATUS", 
            "func(!A5_COMPARE!)", 
            "PYTHON3", 
            """def func(A5_COMPARE):
            compare = A5_COMPARE
            if compare == 10:
                return "VALID"
            if compare == 11:
                return "UNVERIFIED"
            else:
                return None
            """
            )
        nullvalid = arcpy.management.SelectLayerByAttribute(
            studylines, 
            "NEW_SELECTION", 
            "VALIDATION_STATUS IS NULL And FLD_ZONE = 'A' And STATUS_TYPE = 'BEING STUDIED' And STUDY_TYPE LIKE '%APPROXIMATE%'", 
            None
            )
        arcpy.management.CalculateField(
            nullvalid, 
            "VALIDATION_STATUS", 
            "func(!A1_TOPO!,!A2_HYDRO!,!A3_IMPAR!,!A4_TECH!)", 
            "PYTHON3", 
            """def func(A1_TOPO,A2_HYDRO,A3_IMPAR,A4_TECH):
            A1 = A1_TOPO
            A2 = A2_HYDRO
            A3 = A3_IMPAR
            A4 = A4_TECH
            if (A1 == "PASS" and 
            A2  == "PASS" and
            A3  == "PASS" and
            A4 == "PASS"):
                return "VALID"
            else:
                return "UNVERIFIED"
            """
            )
        assessed = arcpy.management.SelectLayerByAttribute(
            studylines, 
            "NEW_SELECTION", 
            "FLD_ZONE = 'A' And STATUS_TYPE = 'BEING STUDIED' And STUDY_TYPE LIKE '%APPROXIMATE%'", 
            None
            )
        arcpy.management.CalculateField(
            assessed,
            "STATUS_DATE",
            "date()",
            "PYTHON3",
            """def date():
            from datetime import date
            today = date.today()
            return today
            """
            )
        nulla5 = arcpy.management.SelectLayerByAttribute(
            studylines, 
            "NEW_SELECTION", 
            "A5_COMPARE IS NULL And (FLD_ZONE = 'A' Or FLD_ZONE = '1 PCT-ANNUAL-CHANCE FLOOD HAZARD CONTAINED') And STATUS_TYPE = 'BEING STUDIED' And STUDY_TYPE LIKE '%APPROXIMATE%'", 
            None
            )
        arcpy.management.CalculateField(
            nulla5, 
            "REASON", 
            '"Insufficient sample points for A5 assessment, Validation Status based on A1 through A4 Checks"', 
            "PYTHON3"
            )
        arcpy.management.CalculateField(
            nulla5,
            "VAL_DATE",
            "date()",
            "PYTHON3",
            """def date():
            from datetime import date
            today = date.today()
            return today
            """
            )
        nonnulla5 = arcpy.management.SelectLayerByAttribute(
            studylines, 
            "NEW_SELECTION", 
            "A5_COMPARE IS NOT NULL And FLD_ZONE = 'A' And STATUS_TYPE = 'BEING STUDIED' And STUDY_TYPE LIKE '%APPROXIMATE%'", 
            None
            )
        arcpy.management.CalculateField(
            nonnulla5,
            "VAL_DATE",
            "date()",
            "PYTHON3",
            """def date():
            from datetime import date
            today = date.today()
            return today
            """
            )
        arcpy.management.SelectLayerByAttribute(
            studylines, 
            "CLEAR_SELECTION"
            )
        arcpy.AddMessage("Populated A5 fields")
        # Delete non-schema fields
        arcpy.SetProgressorLabel("Dropping extra fields...")
        arcpy.management.DeleteField(
            studylines, 
            "FREQUENCY;SUM_FAIL;SUM_PASS;PCT_PASS;PASS_FAIL", 
            "DELETE_FIELDS"
            )
        arcpy.AddMessage("Deleted extra fields")
        arcpy.SetProgressorLabel("Cleaning up files...")
        # Delete intermediate files
        arcpy.management.Delete(
            "ZonalMinMax_A5_Test;A5_Test_Pnts_PairwiseBuffer", 
            ''
            )
        arcpy.AddMessage("Deleted intermediate files")
        return

########################################################################################

class PriorityScore(object):
    def __init__(self):
        self.label = "A5 Priority Score"
        self.description = "This script was adapted from Priority_Score_Calculator_v2.py"

    def getParameterInfo(self):
    # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        huc = arcpy.Parameter(
            name='Study Area HUC12',
            displayName='Study Area HUC12',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        huc.filter.list = ["Polygon"]
        proj = arcpy.Parameter(
            displayName="Local Projected Coordinate System",
            name="Local Projected Coordinate System",
            datatype="GPCoordinateSystem",
            parameterType="Required",
            direction="Input")
        cbgrisk = arcpy.Parameter(
            name='CBGs Risk Data Polys',
            displayName='CBGs Risk Data Polys',
            datatype='GPLayer',
            direction='Input',
            parameterType='Required')
        a5huctable = arcpy.Parameter(
            name='A5 HUC12 Summary Table',
            displayName='A5 HUC12 Summary Table',
            datatype='GPTableView',
            direction='Input',
            parameterType='Required')
        
        params = [folder, huc, proj, cbgrisk, a5huctable]
        return params
    
    def updateParameters(self, parameters):
        return

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):
    # Step 1: Setup variables and file gdb
        arcpy.env.addOutputsToMap = True
        arcpy.env.overwriteOutput = True
        folder = parameters[0].valueAsText
        arcpy.management.CreateFileGDB(fr"{folder}", "PriorityScore.gdb", "CURRENT")
        arcpy.env.workspace = fr"{folder}\\PriorityScore.gdb"
        huc = parameters[1].valueAsText
        proj = parameters[2].valueAsText
        if "PROJECTION" not in proj:
            arcpy.AddError(proj + " is angular; this is not recommended.")
        cbgrisk = parameters[3].valueAsText
        a5huctable = parameters[4].valueAsText
        # Project to local coordinate system
        arcpy.management.Project(
            huc, 
            "HUC12_Project", 
            proj 
            )
        # Calculate total area
        arcpy.management.CalculateGeometryAttributes(
            "HUC12_Project", 
            "Area_12 AREA",
            '', 
            "SQUARE_KILOMETERS", 
            proj
            )
        # Intersect HUC12 with Risk Areas
        arcpy.analysis.Intersect(
            f"HUC12_Project #;{cbgrisk} #", 
            "HUC12_Risk"
            )   
        # Calculate partial area
        arcpy.management.CalculateGeometryAttributes(
            "HUC12_Risk", 
            "Area_12_2 AREA", 
            '', 
            "SQUARE_KILOMETERS", 
            proj
            )
        # Calculate St_Score by Risk_Perce
        # 100 percent
        select100 = arcpy.management.SelectLayerByAttribute(
            "HUC12_Risk", 
            "NEW_SELECTION", 
            "Risk_Perce = '0-25'", 
            None
            )
        count = int(arcpy.management.GetCount(select100)[0])
        if count > 0:
            arcpy.management.CalculateField(
                select100, 
                "St_Score", 
                100, 
                "PYTHON3", 
                "", 
                "DOUBLE"
                )
        # 90 percent
        select90 = arcpy.management.SelectLayerByAttribute(
            "HUC12_Risk", 
            "NEW_SELECTION", 
            "Risk_Perce = '51-80'", 
            None
            )
        count = int(arcpy.management.GetCount(select90)[0])
        if count > 0:
            arcpy.management.CalculateField(
                select90, 
                "St_Score", 
                90, 
                "PYTHON3", 
                "", 
                "DOUBLE"
                )
        # 80 percent
        select80 = arcpy.management.SelectLayerByAttribute(
            "HUC12_Risk", 
            "NEW_SELECTION", 
            "Risk_Perce = '81-90'", 
            None
            )
        count = int(arcpy.management.GetCount(select80)[0])
        if count > 0:
            arcpy.management.CalculateField(
                select80, 
                "St_Score", 
                80, 
                "PYTHON3", 
                "", 
                "DOUBLE"
                )
        # 50 percent
        select50 = arcpy.management.SelectLayerByAttribute(
            "HUC12_Risk", 
            "NEW_SELECTION", 
            "Risk_Perce = '91-95'", 
            None
            )
        count = int(arcpy.management.GetCount(select50)[0])
        if count > 0:
            arcpy.management.CalculateField(
                select50, 
                "St_Score", 
                50, 
                "PYTHON3", 
                "", 
                "DOUBLE"
                )
        # 25 percent
        select25 = arcpy.management.SelectLayerByAttribute(
            "HUC12_Risk", 
            "NEW_SELECTION", 
            "Risk_Perce = '96-100'", 
            None
            )
        count = int(arcpy.management.GetCount(select25)[0])
        if count > 0:
            arcpy.management.CalculateField(
                select25, 
                "St_Score", 
                25, 
                "PYTHON3", 
                "", 
                "DOUBLE"
                )
        arcpy.management.SelectLayerByAttribute(
            "HUC12_Risk",
            "CLEAR_SELECTION"
            )
        # Concatenate HUC12 code and St_Score
        arcpy.management.CalculateField(
            "HUC12_Risk", 
            "HUC12_2", 
            "str(!huc12! )+ ' ' + str(!St_Score!)", 
            "PYTHON3", '', 
            "TEXT"
            )
        # Calculate area percent
        arcpy.management.CalculateField(
            "HUC12_Risk", 
            "HUC12_2_PCT", 
            "!Area_12_2! / !Area_12!", 
            "PYTHON3", 
            "", 
            "DOUBLE"
            )
        # Join FREQUENCY and SUM_FAIL to intersected HUC12_Risk
        arcpy.management.JoinField(
            "HUC12_Risk", 
            "huc12", 
            a5huctable, 
            "huc12", 
            "FREQUENCY;SUM_FAIL"
            )
        # Calculate fail percent
        arcpy.management.CalculateField(
            "HUC12_Risk", 
            "FAIL_PCT", 
            "score(!SUM_FAIL!,!FREQUENCY!)", 
            "PYTHON3", 
            """def score(SUM_FAIL,FREQUENCY):
        if SUM_FAIL != None:
            return SUM_FAIL / FREQUENCY
        else:
            return None
        """, 
            "DOUBLE"
            )
        # Calculate final score from the product of St_Score, area percent, and fail percent
        nonnull = arcpy.management.SelectLayerByAttribute(
            "HUC12_Risk", 
            "NEW_SELECTION", 
            "St_Score IS NOT NULL And FAIL_PCT IS NOT NULL", 
            None
            )
        arcpy.management.CalculateField(
            nonnull, 
            "Final_Score", 
            "!St_Score! * !HUC12_2_PCT! * !FAIL_PCT!", 
            "PYTHON3",
            "",
            "DOUBLE"
            )
        arcpy.analysis.Statistics(
            "HUC12_Risk", 
            "HUC12_Risk_Results", 
            "Final_Score SUM", 
            "huc12"
            )
        # Join SUM_Final_Score to projected HUC12
        arcpy.management.JoinField(
            "HUC12_Project", 
            "huc12", 
            "HUC12_Risk_Results", 
            "huc12", 
            "SUM_Final_Score"
            )
        # Export Excel table and shapefile
        arcpy.conversion.TableToExcel(
            "HUC12_Risk_Results", 
            fr"{folder}\\HUC12_Risk_Results.xlsx", 
            "ALIAS", 
            "CODE"
            )
        arcpy.conversion.FeatureClassToShapefile("HUC12_Project", folder)

########################################################################################

class MarkRevisions(object):
    def __init__(self):
        self.label = "Mark for Revisions"
        self.description = "Use stream exits, NHD water bodies, and semi-flat areas to mark "\
            "0.2pct and 1pct floodplains for potential polygon revisions."

    def getParameterInfo(self):
    # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        polys02 = arcpy.Parameter(
            name='0.2pct Polygons',
            displayName='0.2pct Polygons',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        polys02.filter.list = ["Polygon"]
        water = arcpy.Parameter(
            name='NHD Water Bodies',
            displayName='NHD Water Bodies',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        water.filter.list = ["Polygon"]
        exits = arcpy.Parameter(
            name='Stream Exits',
            displayName='Stream Exits',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        exits.filter.list = ["Polyline"]
        roads = arcpy.Parameter(
            name='Transportation Features',
            displayName='Transportation Features',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Optional')
        roads.filter.list = ["Polyline"]
        workarea = arcpy.Parameter(
            name='Work Area Number',
            displayName='Work Area Number',
            datatype='GPString',
            direction='Input',
            parameterType='Optional')
        
        params = [folder, polys02, water, exits, roads, workarea]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
    # Setup variables and file gdb
        arcpy.env.addOutputsToMap = True
        folder = parameters[0].valueAsText
        polys02 = parameters[1].valueAsText
        water= parameters[2].valueAsText
        exits = parameters[3].valueAsText
        roads = parameters[4].valueAsText
        workarea = parameters[5].valueAsText
        if workarea:
            gdbname = "Backchecks_" + workarea + ".gdb"
        else:
            gdbname = "Backchecks.gdb"
        arcpy.SetProgressorLabel("Setting up...")
        arcpy.AddMessage("Setting up...")
        arcpy.management.CreateFileGDB(fr"{folder}", gdbname, "CURRENT")
        arcpy.env.workspace = fr"{folder}\\{gdbname}"
        arcpy.SetProgressorLabel("Marking stream exits...")
        arcpy.AddMessage("Marking stream exits...")
        if roads:
            notAOMI = arcpy.management.SelectLayerByLocation(in_layer=exits,
                                                overlap_type="INTERSECT",
                                                select_features=roads,
                                                search_distance=None,
                                                selection_type="NEW_SELECTION",
                                                invert_spatial_relationship="INVERT")
            exitpts = arcpy.management.FeatureToPoint(in_features=notAOMI,
                                            out_feature_class="Exits_ToPoint",
                                            point_location="INSIDE")
            count = int(arcpy.management.GetCount(exitpts)[0])
            arcpy.AddMessage(f"Generated {count} stream exit points")
        else:
            exitpts = arcpy.management.FeatureToPoint(in_features=exits,
                                            out_feature_class="Exits_Backchecks",
                                            point_location="INSIDE")
            count = int(arcpy.management.GetCount(exitpts)[0])
            arcpy.AddMessage(f"Generated {count} stream exit points")
        waters = arcpy.management.SelectLayerByLocation(in_layer=water,
                                                overlap_type="BOUNDARY_TOUCHES",
                                                select_features=polys02,
                                                search_distance=None,
                                                selection_type="NEW_SELECTION",
                                                invert_spatial_relationship="INVERT")
        waterpts = arcpy.management.FeatureToPoint(in_features=waters,
                                            out_feature_class="WaterBodies_Backchecks",
                                            point_location="INSIDE")
        count = int(arcpy.management.GetCount(waterpts)[0])
        arcpy.AddMessage(f"Generated {count} water body points")
        return
    
########################################################################################

class PolygonRevisions(object):
    def __init__(self):
        self.label = "Revise Polygons"
        self.description = "Select semi-flat polygons (see TWDB Flat Polygons) that intersect backcheck points "\
            "(areas marked for revision) and split these areas by the existing 0.2percent and 1percent polygons "\
                "that intersect them, then append the resulting split semi-flat polygons that intersect backcheck points "\
                    "to existing 0.2pct and 1pct polygons. Resulting revised polygons may need to be merged and exploded."

    def getParameterInfo(self):
    # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        polys1pct = arcpy.Parameter(
            name='1pct Polys',
            displayName='1pct Polys',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        polys1pct.filter.list = ["Polygon"]
        polys02pct = arcpy.Parameter(
            name='0.2pct Polys',
            displayName='0.2pct Polys',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        polys02pct.filter.list = ["Polygon"]
        semiflats = arcpy.Parameter(
            name='Semi-Flat Area Polygons',
            displayName='Semi-Flat Area Polygons',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        semiflats.filter.list = ["Polygon"]
        backcheck = arcpy.Parameter(
            name='Backcheck Points',
            displayName='Backcheck Points',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required')
        backcheck.filter.list = ["Point"]
        workarea = arcpy.Parameter(
            name='Work Area Number',
            displayName='Work Area Number',
            datatype='GPString',
            direction='Input',
            parameterType='Optional')
        
        params = [folder, polys1pct, polys02pct, semiflats, backcheck, workarea]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
    # Setup variables and file gdb
        arcpy.env.addOutputsToMap = True
        folder = parameters[0].valueAsText
        polys1pct = parameters[1].valueAsText
        polys02pct = parameters[2].valueAsText
        semiflats = parameters[3].valueAsText
        backcheck = parameters[4].valueAsText
        workarea = parameters[5].valueAsText
        if workarea:
            gdbname = "PolygonRevisions_" + workarea + ".gdb"
        else:
            gdbname = "PolygonRevisions.gdb"
        arcpy.management.CreateFileGDB(fr"{folder}", gdbname, "CURRENT")
        arcpy.env.workspace = fr"{folder}\\{gdbname}"
        arcpy.SetProgressorLabel("Setting up...")
        arcpy.AddMessage("Setting up...")
        arcpy.management.CopyFeatures(in_features=polys1pct,
                                      out_feature_class="Polys_1pct_Copy")
        arcpy.management.CopyFeatures(in_features=polys02pct,
                                      out_feature_class="Polys_02pct_Copy")
        # Clip semi-flats to existing data
        include = arcpy.management.SelectLayerByLocation(in_layer=semiflats,
                                                overlap_type="INTERSECT",
                                                select_features="Polys_02pct_Copy",
                                                search_distance=None,
                                                selection_type="NEW_SELECTION",
                                                invert_spatial_relationship="NOT_INVERT")
        # Make new copy for revision editing
        arcpy.management.CopyFeatures(in_features=include,
                                      out_feature_class="SemiFlats_Copy")
        arcpy.management.SelectLayerByAttribute(semiflats,"CLEAR_SELECTION")
        # Select pond and cutting features
        ponds = arcpy.management.SelectLayerByLocation(in_layer="SemiFlats_Copy",
                                                overlap_type="INTERSECT",
                                                select_features=backcheck,
                                                search_distance=None,
                                                selection_type="NEW_SELECTION",
                                                invert_spatial_relationship="NOT_INVERT")
        cuts = arcpy.management.SelectLayerByLocation(in_layer="Polys_1pct_Copy",
                                                overlap_type="INTERSECT",
                                                select_features=ponds,
                                                search_distance=None,
                                                selection_type="NEW_SELECTION",
                                                invert_spatial_relationship="NOT_INVERT")
    # Append ponds to 0.2pct
        arcpy.SetProgressorLabel("Revising 0.2pct polygons...")
        arcpy.AddMessage("Revising 0.2pct polygons...")
        arcpy.topographic.SplitFeatures(cutting_features=cuts,
                                        target_features=ponds)
        arcpy.management.Rename(in_data="SemiFlats_Copy",
                                out_data="SemiFlatAreas_cut1")
        append = arcpy.management.SelectLayerByLocation(in_layer="SemiFlatAreas_cut1",
                                            overlap_type="INTERSECT",
                                            select_features=backcheck,
                                            search_distance=None,
                                            selection_type="NEW_SELECTION",
                                            invert_spatial_relationship="NOT_INVERT")
        appendcount = int(arcpy.management.GetCount(append)[0])
        arcpy.AddMessage(f"{appendcount} ponds post-split.")
        arcpy.management.Append(inputs=append,
                                target="Polys_02pct_Copy",
                                schema_type="NO_TEST")
        arcpy.management.Rename(in_data="Polys_02pct_Copy",
                                out_data="Polys_02pct_Revised")
    # Append ponds to 1pct
        arcpy.SetProgressorLabel("Revising 1pct polygons...")
        arcpy.AddMessage("Revising 1pct polygons...")
        arcpy.management.Append(inputs=append,
                                target="Polys_1pct_Copy",
                                schema_type="NO_TEST")
        arcpy.management.Rename(in_data="Polys_1pct_Copy",
                                out_data="Polys_1pct_Revised")
        return
    
