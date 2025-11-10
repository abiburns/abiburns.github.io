# -*- coding: utf-8 -*-

import arcpy
import arcgis
import pandas as pd
# This module is supposed to clear the cache for faster processing
import importlib


class Toolbox(object):
    def __init__(self):
        self.label = "DFIRM & FRD Toolbox"
        self.alias = "DFIRMFRDToolbox"
        self.description = "This Python toolbox contains geoprocessing tools associated with building" \
        " a Draft FIRM or FRD file geodatabase."

        # List of tool classes associated with this toolbox
        self.tools = [Remove_Add_SpatialIndex, MatchCodes_FC, MatchCodes_TBL, EndStationSelect, StartStations, Indx_Wtr_Features, Append_XS_Elev]


class Remove_Add_SpatialIndex(object):
    def __init__(self):
        self.label = "Remove & Add Spatial Index"
        self.description = "Iterate through feature classes in a feature dataset" \
            " OR through shapefiles in a folder and regenerate (remove and add)" \
                 " or generate (add) spatial indexes."
    def getParameterInfo(self):
    # Define parameters
        fd = arcpy.Parameter(
            name='Input Workspace',
            displayName='Input Workspace',
            datatype='DEWorkspace',
            direction='Input',
            parameterType='Required'
        )
        params = [fd]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        fd = parameters[0].valueAsText
        arcpy.env.workspace = fd
        datasets = arcpy.ListDatasets()
        for ds in datasets:
            featureclasses = arcpy.ListFeatureClasses(feature_dataset=ds)
            for fc in featureclasses:
                indexes = arcpy.ListIndexes(dataset=fc)
                if "SHAPE_INDEX" in indexes:
                    arcpy.management.RemoveSpatialIndex(in_features=fc)
                    arcpy.AddMessage(f"Removed spatial index for {fc}")
                    arcpy.management.AddSpatialIndex(in_features=fc)
                    arcpy.AddMessage(f"Added spatial index for {fc}")
                else:
                    arcpy.management.AddSpatialIndex(in_features=fc)
                    arcpy.AddMessage(f"Added spatial index for {fc}")

class MatchCodes_FC(object):
    def __init__(self):
        self.label = "Codes to Descriptions (Feature Classes)"
        self.description = "Convert input feature classes to shapefiles," \
        " then iterate through the shapefiles and replace domain codes with their matching descriptions."

    def getParameterInfo(self):
        # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder (NOTE: Do not use a folder already containing shapefiles)',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        fcs = arcpy.Parameter(
            name='Feature Classes',
            displayName='Feature Classes',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required',
            multiValue = True
        )
        params = [folder, fcs]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        folder = parameters[0].valueAsText
        fcs = parameters[1].valueAsText
        arcpy.AddMessage("Converting to shapefile (NOTE: May need to increase field lengths).")
        arcpy.conversion.FeatureClassToShapefile(fcs, folder)
        arcpy.env.workspace = folder
        for shp in arcpy.ListFiles("*.shp"):
            fields = arcpy.ListFields(shp)
            count = 0
            for field in fields:
                if field.name == 'STUDY_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "STUDY_TYP",
                        expression="MatchDescrip(!STUDY_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(STUDY_TYP):
                        D_Study_Typ = {
                        'NP': "NP",
                        '1000': "SFHA without BFE",
                        '1010': "SFHA with BFE published only in FIS",
                        '1030': "BLE available but unpublished",
                        'SFHA with unpublished BFE': "SFHA with unpublished BFE",
                        '1040': "SFHA with unpublished BFE",
                        '1050': "SFHA with BFE no floodway",
                        '1060': "SFHA with BFE and floodway",
                        '1070': "Shaded Zone X with depths less than 1"
                        }
                        x = D_Study_Typ[STUDY_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'VEL_UNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "VEL_UNIT",
                        expression="MatchDescrip(!VEL_UNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(VEL_UNIT):
                        D_Velocity_Units = {
                        ' ': " ",
                        '1000': "Centimeters / Day",
                        '1010': "Centimeters / Hour",
                        '1020': "Feet / Second",
                        '1030': "Inches / Day",
                        '1040': "Inches / Hour",
                        '1050': "Meters / Second",
                        '1060': "Micrometers / Second",
                        '1070': "Millimeters / Day",
                        '1080': "Millimeters / Hour",
                        'NP': "NP"
                        }
                        x = D_Velocity_Units[VEL_UNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'LEN_UNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "LEN_UNIT",
                        expression="MatchDescrip(!LEN_UNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(LEN_UNIT):
                        D_Length_Units = {
                        ' ': " ",
                        'CM': "Centimeters",
                        'FT': "Feet",
                        'Feet': "Feet",
                        'IN': "Inches",
                        'KM': "Kilometers",
                        'M': "Meters",
                        'MI': "Miles",
                        'MM': "Millimeters",
                        'USFT': "U.S. Survey Feet",
                        'NP': "NP"
                        }
                        x = D_Length_Units[LEN_UNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'AREA_UNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "AREA_UNIT",
                        expression="MatchDescrip(!AREA_UNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(AREA_UNIT):
                        D_Area_Units = {
                        ' ': " ",
                        '1000': "Acres",
                        '1010': "Hectares",
                        '1020': "Square Feet",
                        'Square Feet': "Square Feet",
                        '1030': "Square Meters",
                        'Square Meters': "Square Meters",
                        '1040': "Square Yards",
                        '1050': "Square Miles",
                        'Square Miles': "Square Miles",
                        '1060': "Square Kilometers",
                        'NP': "NP"
                        }
                        x = D_Area_Units[AREA_UNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'LN_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "LN_TYP",
                        expression="MatchDescrip(!LN_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(LN_TYP):
                        D_Ln_Typ = {
                        '2034': "SFHA / Flood Zone Boundary",
                        'SFHA / Flood Zone Boundary': "SFHA / Flood Zone Boundary",
                        'Limit Lines': "Limit Lines",
                        '1010': "Limit Lines",
                        'Other Boundary': "Other Boundary",
                        '1020': "Other Boundary",
                        '2050': "Flowage Easement Boundary"
                        }
                        x = D_Ln_Typ[LN_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'XS_LN_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "XS_LN_TYP",
                        expression="MatchDescrip(!XS_LN_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(XS_LN_TYP):
                        D_Ln_Typ = {
                        '1010': "LETTERED, MAPPED",
                        'LETTERED, MAPPED': "LETTERED, MAPPED",
                        '1020': "NOT LETTERED, MAPPED",
                        'NOT LETTERED, MAPPED': "NOT LETTERED, MAPPED",
                        '1030': "NOT LETTERED, NOT MAPPED",
                        'NOT LETTERED, NOT MAPPED': "NOT LETTERED, NOT MAPPED"
                        }
                        x = D_Ln_Typ[XS_LN_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'METHOD_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "METHOD_TYP",
                        expression="MatchDescrip(!METHOD_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(METHOD_TYP):
                        D_Study_Mth = {
                        '1000': "New H&H",
                        '1010': "BLE TIER A",
                        '1020': "BLE TIER B",
                        '1030': "BLE TIER C",
                        '1040': "BLE TIER D",
                        '1050': "BLE TIER E",
                        '1060': "LSAE",
                        '1100': "REDELINEATION",
                        '1200': "DIGITAL CONVERSION",
                        'NP': "NP",
                        '1300': "SECLUSION"
                        }
                        x = D_Study_Mth[METHOD_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'TASK_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "TASK_TYP",
                        expression="MatchDescrip(!TASK_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(TASK_TYP):
                        D_Task_Typ = {
                        '1000': "ALLUVIAL FAN",
                        '1010': "BASE MAP",
                        '1020': "COASTAL",
                        '1030': "FIRM DATABASE",
                        '1040': "FLOODPLAIN MAPPING",
                        '1050': "HYDRAULIC",
                        '1060': "HYDROLOGIC",
                        '1070': "SURVEY",
                        '1090': "DISCOVERY",
                        '1100': "FLOOD RISK ASSESSMENT",
                        '1200': "LOMR",
                        '1300': "Levee Seclusion",
                        'NP': "NP",
                        '1080': "NEW TOPO CAPTURE",
                        '1081': "EXISTING TOPO CAPTURE",
                        '1082': "TERRAIN CAPTURE"
                        }
                        x = D_Task_Typ[TASK_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'WATER_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "WATER_TYP",
                        expression="MatchDescrip(!WATER_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(WATER_TYP):
                        D_Prof_Baseln_Typ = {
                        '1000': "Profile Baseline",
                        '2000': "Profile Baseline and Stream Centerline",
                        '3000': "Hydraulic Link",
                        'UNK': "Unknown"
                        }
                        x = D_Prof_Baseln_Typ[WATER_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'PANEL_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "PANEL_TYP",
                        expression="MatchDescrip(!PANEL_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(PANEL_TYP):
                        D_Panel_Typ = {
                        '1000': "Countywide, Panel Printed",
                        '1010': "Countywide, Not Printed",
                        '1020': "Community Based, Panel Printed",
                        '1030': "Community Based, Not Printed",
                        '1040': "Unmapped Community",
                        '1050': "Statewide, Panel Printed",
                        '1060': "Statewide, Not Printed"
                        }
                        x = D_Panel_Typ[PANEL_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'LOC_ACC':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "LOC_ACC",
                        expression="MatchDescrip(!LOC_ACC!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(LOC_ACC):
                        D_Mtg_Typ = {
                        'H': "High",
                        'High': "High",
                        'M': "Medium",
                        'Medium': "Medium",
                        'L': "Low",
                        'Low': "Low"
                        }
                        x = D_Mtg_Typ[LOC_ACC]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'SCALE':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "SCALE",
                        expression="MatchDescrip(!SCALE!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(SCALE):
                        D_Scale = {
                        '1000': "6000",
                        '1010': "12000",
                        '1020': "24000",
                        '2000': "10000"
                        }
                        x = D_Scale[SCALE]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'BASE_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "BASE_TYP",
                        expression="MatchDescrip(!BASE_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(BASE_TYP):
                        D_Basemap_Typ = {
                        ' ': " ",
                        '1000': "Orthophoto",
                        '2000': "Vector",
                        'NP': "NP"
                        }
                        x = D_Basemap_Typ[BASE_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'BASIN_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "BASIN_TYP",
                        expression="MatchDescrip(!BASIN_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(BASIN_TYP):
                        D_Subbasin_Typ = {
                        'HYD': "Hydrologic Analyses",
                        'NP': "NP",
                        'HUC8': "USGS HUC-8",
                        'USGS HUC-8': "USGS HUC-8"
                        }
                        x = D_Subbasin_Typ[BASIN_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'MTFCC':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "MTFCC",
                        expression="MatchDescrip(!MTFCC!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(MTFCC):
                        D_MTFCC = {
                        'R1051': "Carline, Streetcar Track, Monorail, Other Mass Transit Rail",
                        'R1052': "Cog Rail Line, Incline Rail Line, Tram",
                        'S1100': "Primary Road",
                        'S1200': "Secondary Road",
                        'S1400': "Local Neighborhood Road, Rural Road, City Street",
                        'S1500': "Vehicular Trail (4WD)",
                        'S1630': "Ramp",
                        'S1710': "Walkway/Pedestrian Trail",
                        'S1720': "Stairway",
                        'S1730': "Alley",
                        'S1750': "Internal U.S. Census Bureau Use",
                        'S1780': "Parking Lot Road",
                        'S1830': "Bridle Path",
                        'S2000': "Road Median",
                        'NP': "NP",
                        'R1011': "Railroad Feature (Main, Spur, or Yard)",
                        'S1640': "Service Drive Usually Along a Limited Access Highway",
                        'S1740': "Private Road for Service Vehicles (Logging, Oil Fields, Ranches, Etc.)",
                        'S1820': "Bike Path or Trail"
                        }
                        x = D_MTFCC[MTFCC]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'ROUTE_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "ROUTE_TYP",
                        expression="MatchDescrip(!ROUTE_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(ROUTE_TYP):
                        D_Carto_Trans_Code = {
                        'NP': "NP",
                        '0100': "Interstates",
                        '0200': "US Highways",
                        '0300': "State Highways",
                        '0400': "County Roads",
                        '0500': "Local Roads",
                        '0700': "Railroads",
                        '0800': "Airports"
                        }
                        x = D_Carto_Trans_Code[ROUTE_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'HYDRA_MDL':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "HYDRA_MDL",
                        expression="MatchDescrip(!HYDRA_MDL!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(HYDRA_MDL):
                        D_Hydra_Mdl = {
                        ' ': "",
                        '0110': "CHAN for Windows v. 2.03 (1997)",
                        '0120': "Culvert Master v. 2.0 (September 2000) and up",
                        '1001': "DHM 21 and 34 (Aug. 1987)",
                        '0140': "FAN",
                        '1002': "FEQ 8.92 (1999) and FEQ 9.98 (2005)",
                        '1003': "FEQUTL 4.68 (1999) and FEQUTL 5.46 (2005)",
                        '1004': "FESWMS 2DH 1.1 and up (Jun. 1995)",
                        '1005': "FLDWAV (Nov. 1998)",
                        '1006': "FLO-2D v. 2007.06 and 2009.06",
                        '1007': "FLO-2D V.2003.6, 2004.10 and 2006.1",
                        '1008': "Gage Analysis",
                        '1009': "HCSWMM 4.31B (August 2000)",
                        '1010': "HEC-2 4.6.2 (May 1991)",
                        '1012': "HEC-RAS 3.1.1 and up",
                        '1013': "HY8 4.1 and up (Nov. 1992)",
                        '1000': "ICPR 2.20 (Oct. 2000), 3.02 (Nov. 2002), and 3.10 (April 2008) with PercPack Option",
                        '1015': "MIKE 11 HD (2002 D, 2004)",
                        '1030': "MIKE 11 HD v.2009 SP4",
                        '0260': "MIKE Flood HD (2002 D and 2004)",
                        '1028': "MIKE URBAN Collection Systems (MOUSE) Release 2009, date June 2010",
                        '0262': "MIKE Flood HD v.2009 SP4",
                        '0270': "NETWORK (June 2002)",
                        '0280': "PondPack v. 8 (May 2002) and up",
                        '1017': "QUICK-2 1.0 and up (Jan. 1995)",
                        '0300': "S2DMM (Feb 2008)",
                        '0401': "SMS ADH v11.1 and up",
                        '0402': "SMS ADCIRC v11.1 and up",
                        '0403': "SMS BOUSS-2D v11.1 and up",
                        '0404': "SMS CGWAVE v11.1 and up",
                        '0405': "SMS CMS Flow v11.1 and up",
                        '0406': "SMS CMS Wave v11.1 and up",
                        '0407': "SMS FESWMS v11.1 and up",
                        '0408': "SMS HYDRO_AS-2D",
                        '0409': "SMS GENCADE v11.1 and up",
                        '0410': "SMS PTM v11.1 and up",
                        '0411': "SMS RiverFlow2D v11.2 and up",
                        '0412': "SMS RMA2 v11.1 and up",
                        '0413': "SMS RMA4 v11.1 and up",
                        '0414': "SMS SRH-2D v11.2 and up",
                        '0415': "SMS STWAVE v11.1 and up",
                        '0416': "SMS TUFLOW v11.1 and up",
                        '0417': "SMS TUFLOW AD v11.1 and up",
                        '0418': "SMS TUFLOW Multiple Domains v11.1 and up",
                        '0419': "SMS TUFLOW FV v11.1 and up",
                        '0420': "SMS WAM v11.1 and up",
                        '0310': "StormCAD v.4 (June 2002) and up",
                        '1021': "SWMM 4.30 (MAY 1994)",
                        '1022': "SWMM 4.31 (JANUARY 1997)",
                        '0322': "SWMM 5 Version 5.0.005 (May 2005) and up",
                        '1023': "TABS RMA2 v. 4.3 and up (Oct. 1996)",
                        '1024': "TABS RMA4 v. 4.5 and up (July 2000)",
                        '1025': "UNET 4.0 (April 2001)",
                        '1026': "WSPGW 12.96 (OCTOBER 2000)",
                        '1027': "WSPRO (Jun. 1988 and up)",
                        '0370': "Xpstorm 10.0 (May 2006)",
                        '0362': "XPSWMM 2D/XPStorm 2D v. 12.00 (May 2010)",
                        '0360': "XP-SWMM 8.52 and up",
                        '1029': "TUFLOW Release Version 2010-10 (October 2010)",
                        '9000': "Other",
                        '1014': "HEC-RAS 5.0 and up"
                        }
                        x = D_Hydra_Mdl[HYDRA_MDL]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'HYDRO_MDL':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "HYDRO_MDL",
                        expression="MatchDescrip(!HYDRO_MDL!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(HYDRO_MDL):
                        D_Hydro_Mdl = {
                        ' ': "",
                        '2000': "AHYMO 97 (Aug. 1997)",
                        '2001': "CUHPF/PC (May 1996 and May 2002)",
                        '2006': "HEC-1 4.0.1 and up 1 (May 1991)",
                        '2005': "HEC-FFA 3.1 (February 1995)",
                        '2008': "HEC-HMS 3.0 and up (Dec 2005)",
                        '2040': "HEC-SSP 1.1 (April 2009) and up",
                        '2018': "HSPF 10.10 (Dec 1993) and up",
                        '2042': "MIKE 11 (2009 SP4)",
                        '2022': "MIKE 11 RR (2009 SP4)",
                        '2023': "MIKE 11 UHM (2002 D and 2004)",
                        '2024': "PEAKFQ 2.4 (April 1998) and up",
                        '0190': "PondPack v.8 (May 2002) and up",
                        '0200': "PRMS Version 2.1 (Jan 1996)",
                        '2029': "Regression Equations",
                        '2032': "SWMM (RUNOFF) 4.31 (Jan 1997)",
                        '0222': "SWMM 5 Version 5.0.005 (May 2005) and up",
                        '2033': "TR-20 Win (Feb 1992)",
                        '0231': "TR-20 Win 1.00 (Jan 2005)",
                        '0240': "TR-55 (JUNE 1986)",
                        '2041': "VCRat 2.6 (Dec. 2008)",
                        '2034': "WinTR-55 1.0.08 (Jan 2005)",
                        '0260': "Xpstorm 10.0 (May 2006)",
                        '0250': "XP-SWMM 8.52 and up",
                        '9000': "OTHER",
                        '2031': "SWMM (RUNOFF) 4.30 (May1994)"
                        }
                        x = D_Hydro_Mdl[HYDRO_MDL]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'AOMI_CLASS':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "AOMI_CLASS",
                        expression="MatchDescrip(!AOMI_CLASS!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(AOMI_CLASS):
                        D_AOMI_Class = {
                        'RIV': "Riverine",
                        'COAS': "Coastal",
                        'OTH': "Other",
                        'PAS': "Past Claims and Mitigation",
                        'NP': "NP"
                        }
                        x = D_AOMI_Class[AOMI_CLASS]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'AOMI_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "AOMI_TYP",
                        expression="MatchDescrip(!AOMI_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(AOMI_TYP):
                        D_AOMI_Typ = {
                        '0100': "Dams",
                        '0200': "Non-Accredited Levees",
                        '0210': "Accredited Levees",
                        '0300': "Coastal Structures",
                        '0400': "Streamflow Constrictions",
                        '0500': "Key Emergency Routes Overtopped",
                        '0600': "Past Claims Hot Spot",
                        '0700': "Individual Assistance (IA) or Public Assistance (PA)",
                        '0800': "Significant Land Use Change",
                        '0900': "Areas of Significant Erosion",
                        '1000': "Non-Levee Embankments",
                        '1100': "At Risk Essential Facilities",
                        '2000': "Other Flood Risk Areas",
                        '3000': "Areas of Mitigation Success",
                        '9000': "Other",
                        'NP': "NP"
                        }
                        x = D_AOMI_Typ[AOMI_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'ZONE_SUBTY':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "ZONE_SUBTY",
                        expression="MatchDescrip(!ZONE_SUBTY!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(ZONE_SUBTY):
                        D_Zone_Subtyp = {
                        ' ': " ",
                        '1010': "ADMINISTRATIVE FLOODWAY",
                        '1020': "AREA OF SPECIAL CONSIDERATION",
                        '1040': "COLORADO RIVER FLOODWAY",
                        '1030': "COMMUNITY ENCROACHMENT AREA",
                        '1050': "DENSITY FRINGE AREA",
                        '1100': "FLOODWAY",
                        '1110': "FLOODWAY CONTAINED IN STRUCTURE",
                        '1200': "FLOWAGE EASEMENT AREA",
                        '1230': "NARROW FLOODWAY",
                        '1220': "RIVERINE FLOODWAY SHOWN IN COASTAL ZONE",
                        '1210': "STATE ENCROACHMENT AREA",
                        'AREA OF MINIMAL FLOOD HAZARD': "AREA OF MINIMAL FLOOD HAZARD",
                        '2000': "AREA OF MINIMAL FLOOD HAZARD",
                        '1120': "FLOODWAY CONTAINED IN CHANNEL",
                        '0100': "COASTAL FLOODPLAIN",
                        '0120': "COMBINED RIVERINE AND COASTAL FLOODPLAIN",
                        '1240': "RIVERINE FLOODWAY IN COMBINED RIVERINE AND COASTAL ZONE",
                        '3000': "AREA WITH FLOOD HAZARD DUE TO NON-ACCREDITED LEVEE SYSTEM",
                        '3010': "AREA WITH REDUCED FLOOD HAZARD DUE TO PROVISIONALLY ACCREDITED LEVEE SYSTEM",
                        '0.2 PCT ANNUAL CHANCE FLOOD HAZARD': "0.2 PCT ANNUAL CHANCE FLOOD HAZARD",
                        '0500': "0.2 PCT ANNUAL CHANCE FLOOD HAZARD",
                        '0510': "0.2 PCT ANNUAL CHANCE FLOOD HAZARD CONTAINED IN STRUCTURE",
                        '0210': "1 PCT ANNUAL CHANCE FLOOD HAZARD CONTAINED IN CHANNEL",
                        '0200': "1 PCT ANNUAL CHANCE FLOOD HAZARD CONTAINED IN STRUCTURE",
                        '0400': "1 PCT DEPTH LESS THAN 1 FOOT",
                        '0410': "1 PCT DRAINAGE AREA LESS THAN 1 SQUARE MILE",
                        '0300': "1 PCT FUTURE CONDITIONS",
                        '0310': "1 PCT FUTURE CONDITIONS CONTAINED IN STRUCTURE",
                        '0520': "0.2 PCT ANNUAL CHANCE FLOOD HAZARD CONTAINED IN CHANNEL",
                        '0110': "RIVERINE FLOODPLAIN IN COASTAL ZONE",
                        '0530': "0.2 PCT ANNUAL CHANCE FLOOD HAZARD IN COASTAL ZONE",
                        '0540': "0.2 PCT ANNUAL CHANCE FLOOD HAZARD IN COMBINED RIVERINE AND COASTAL ZONE",
                        '3020': "AREA WITH UNDETERMINED FLOOD HAZARD DUE TO NON-ACCREDITED LEVEE SYSTEM",
                        '3030': "AREA WITH REDUCED FLOOD HAZARD DUE TO ACCREDITED LEVEE SYSTEM",
                        '1000': "AREA WITH REDUCED FLOOD HAZARD DUE TO NON-ACCREDITED LEVEE SYSTEM"
                        }
                        x = D_Zone_Subtyp[ZONE_SUBTY]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'STRUCT_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "STRUCT_TYP",
                        expression="MatchDescrip(!STRUCT_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(STRUCT_TYP):
                        D_Struct_Typ = {
                        ' ': " ",
                        '1000': "Aqueduct",
                        '1001': "Bridge",
                        'Bridge': "Bridge",
                        '1002': "Canal",
                        '1003': "Channel",
                        '1006': "Control Structure",
                        'Control Structure': "Control Structure",
                        '1007': "Culvert",
                        'Culvert': "Culvert",
                        '1010': "Dam",
                        'Dam': "Dam",
                        '1012': "Dock",
                        '1013': "Drop Structure",
                        '1014': "Energy Dissipater",
                        '1015': "Fish Ladder",
                        '1017': "Flume",
                        '1018': "Footbridge",
                        '1019': "Gate",
                        '1020': "Jetty",
                        '1021': "Levee",
                        '1022': "Lock",
                        '1023': "Penstock",
                        '1024': "Pier",
                        '1025': "Pump Station",
                        'Pump Station': "Pump Station",
                        '1026': "Seawall",
                        '1027': "Side Weir Structure",
                        '1028': "Storm Sewer",
                        'Storm Sewer': "Storm Sewer",
                        '1029': "Utility Crossing",
                        'Utility Crossing': "Utility Crossing",
                        '1030': "Weir",
                        'Weir': "Weir",
                        '1031': "Wing Wall",
                        '1036': "Floodway Contained in Structure",
                        '1037': "Pipeline",
                        '1038': "Retaining Wall",
                        '1039': "Revetment",
                        '1040': "Siphon",
                        'NP': "NP",
                        '1033': "0.2-Percent-Annual-Chance Flood Discharge Contained in Structure",
                        '0.2-Percent-Annual-Chance Flood Discharge Contained in Structure': "0.2-Percent-Annual-Chance Flood Discharge Contained in Structure",
                        '1032': "1-Percent-Annual-Chance Flood Discharge Contained in Structure",
                        '1-Percent-Annual-Chance Flood Discharge Contained in Structure': "1-Percent-Annual-Chance Flood Discharge Contained in Structure",
                        '9000': "Other / Misc. Structure"
                        }
                        x = D_Struct_Typ[STRUCT_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'NODE_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        shp,
                        "NODE_TYP",
                        expression="MatchDescrip(!NODE_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(NODE_TYP):
                        D_Node_Typ = {
                        ' ': " ",
                        '1000': "Diversion",
                        '1010': "Junction",
                        'Junction': "Junction",
                        '1020': "Reservoir",
                        '1030': "Structure",
                        '1040': "Sub-Basin Outlet"
                        }
                        x = D_Node_Typ[NODE_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
            arcpy.AddMessage(f"Converted {count} fields in {shp}.")


class MatchCodes_TBL(object):
    def __init__(self):
        self.label = "Codes to Descriptions (Tables)"
        self.description = "Convert input geodatabase tables to standalone tables," \
        " then iterate through the standalone tables and replace domain codes with their matching descriptions."

    def getParameterInfo(self):
        # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder (NOTE: Do not use a folder already containing standalone tables)',
            datatype='DEFolder',
            direction='Input',
            parameterType='Required'
        )
        tbs = arcpy.Parameter(
            name='DB Tables',
            displayName='DB Tables',
            datatype='GPTableView',
            direction='Input',
            parameterType='Required',
            multiValue = True
        )
        params = [folder, tbs]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        folder = parameters[0].valueAsText
        tbs = parameters[1].valueAsText
        arcpy.AddMessage("Converting to standalone table (NOTE: May need to increase field lengths).")
        tbs = tbs.split(";")
        # arcpy.AddMessage(f"{tbs}")
        for tb in tbs:
            arcpy.conversion.TableToTable(
                tb, 
                folder, 
                f"{tb}.dbf"
                )
        arcpy.env.workspace = folder
        for dbf in arcpy.ListFiles("*.dbf"):
            fields = arcpy.ListFields(dbf)
            count = 0
            for field in fields:
                if field.name == 'VEL_UNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "VEL_UNIT",
                        expression="MatchDescrip(!VEL_UNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(VEL_UNIT):
                        D_Velocity_Units = {
                        ' ': " ",
                        '1000': "Centimeters / Day",
                        '1010': "Centimeters / Hour",
                        '1020': "Feet / Second",
                        'Feet / Second': "Feet / Second",
                        '1030': "Inches / Day",
                        '1040': "Inches / Hour",
                        '1050': "Meters / Second",
                        'Meters / Second': "Meters / Second",
                        '1060': "Micrometers / Second",
                        '1070': "Millimeters / Day",
                        '1080': "Millimeters / Hour",
                        'NP': "NP"
                        }
                        x = D_Velocity_Units[VEL_UNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'LEN_UNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "LEN_UNIT",
                        expression="MatchDescrip(!LEN_UNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(LEN_UNIT):
                        D_Length_Units = {
                        ' ': " ",
                        'CM': "Centimeters",
                        'FT': "Feet",
                        'Feet': "Feet",
                        'IN': "Inches",
                        'KM': "Kilometers",
                        'M': "Meters",
                        'MI': "Miles",
                        'MM': "Millimeters",
                        'USFT': "U.S. Survey Feet",
                        'NP': "NP"
                        }
                        x = D_Length_Units[LEN_UNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'WSEL_UNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "WSEL_UNIT",
                        expression="MatchDescrip(!WSEL_UNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(WSEL_UNIT):
                        D_Length_Units = {
                        ' ': " ",
                        'CM': "Centimeters",
                        'FT': "Feet",
                        'Feet': "Feet",
                        'IN': "Inches",
                        'KM': "Kilometers",
                        'M': "Meters",
                        'MI': "Miles",
                        'MM': "Millimeters",
                        'USFT': "U.S. Survey Feet",
                        'NP': "NP"
                        }
                        x = D_Length_Units[WSEL_UNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'STRUCT_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "STRUCT_TYP",
                        expression="MatchDescrip(!STRUCT_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(STRUCT_TYP):
                        D_Struct_Typ = {
                        ' ': " ",
                        '1000': "Aqueduct",
                        '1001': "Bridge",
                        'Bridge': "Bridge",
                        '1002': "Canal",
                        '1003': "Channel",
                        '1006': "Control Structure",
                        'Control Structure': "Control Structure",
                        '1007': "Culvert",
                        'Culvert': "Culvert",
                        '1010': "Dam",
                        'Dam': "Dam",
                        '1012': "Dock",
                        '1013': "Drop Structure",
                        '1014': "Energy Dissipater",
                        '1015': "Fish Ladder",
                        '1017': "Flume",
                        '1018': "Footbridge",
                        '1019': "Gate",
                        '1020': "Jetty",
                        '1021': "Levee",
                        '1022': "Lock",
                        '1023': "Penstock",
                        '1024': "Pier",
                        '1025': "Pump Station",
                        'Pump Station': "Pump Station",
                        '1026': "Seawall",
                        '1027': "Side Weir Structure",
                        '1028': "Storm Sewer",
                        'Storm Sewer': "Storm Sewer",
                        '1029': "Utility Crossing",
                        'Utility Crossing': "Utility Crossing",
                        '1030': "Weir",
                        'Weir': "Weir",
                        '1031': "Wing Wall",
                        '1036': "Floodway Contained in Structure",
                        '1037': "Pipeline",
                        '1038': "Retaining Wall",
                        '1039': "Revetment",
                        '1040': "Siphon",
                        'NP': "NP",
                        '1033': "0.2-Percent-Annual-Chance Flood Discharge Contained in Structure",
                        '0.2-Percent-Annual-Chance Flood Discharge Contained in Structure': "0.2-Percent-Annual-Chance Flood Discharge Contained in Structure",
                        '1032': "1-Percent-Annual-Chance Flood Discharge Contained in Structure",
                        '1-Percent-Annual-Chance Flood Discharge Contained in Structure': "1-Percent-Annual-Chance Flood Discharge Contained in Structure",
                        '9000': "Other / Misc. Structure"
                        }
                        x = D_Struct_Typ[STRUCT_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'AREA_UNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "AREA_UNIT",
                        expression="MatchDescrip(!AREA_UNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(AREA_UNIT):
                        D_Area_Units = {
                        ' ': " ",
                        '1000': "Acres",
                        '1010': "Hectares",
                        '1020': "Square Feet",
                        'Square Feet': "Square Feet",
                        '1030': "Square Meters",
                        'Square Meters': "Square Meters",
                        '1040': "Square Yards",
                        '1050': "Square Miles",
                        'Square Miles': "Square Miles",
                        '1060': "Square Kilometers",
                        'NP': "NP"
                        }
                        x = D_Area_Units[AREA_UNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'STUDY_PRE':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "STUDY_PRE",
                        expression="MatchDescrip(!STUDY_PRE!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(STUDY_PRE):
                        D_Study_Prefix = {
                        ' ': " ",
                        '0100': "Borough of",
                        '0200': "City and County of",
                        '0300': "City of",
                        '0400': "Municipality of",
                        '0500': "Town of",
                        '0600': "Township of",
                        '0700': "Village of",
                        '0800': "Town and Village of",
                        '0900': "Tribal Nation",
                        '9000': "Other",
                        'Other': "Other"
                        }
                        x = D_Study_Prefix[STUDY_PRE]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'JURIS_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "JURIS_TYP",
                        expression="MatchDescrip(!JURIS_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(JURIS_TYP):
                        D_Juris_Typ = {
                        ' ': " ",
                        '0100': "All Jurisdictions",
                        '0200': "And Incorporated Areas",
                        'And Incorporated Areas': "And Incorporated Areas",
                        '0300': "Independent City",
                        '0400': "Tribal Nation",
                        '0900': "Unincorporated Areas",
                        'Unincorporated Areas': "Unincorporated Areas"
                        }
                        x = D_Juris_Typ[JURIS_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'H_DATUM':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "H_DATUM",
                        expression="MatchDescrip(!H_DATUM!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(H_DATUM):
                        D_Horiz_Datum = {
                        ' ': " ",
                        'NAD27': "North American Datum 1927",
                        'NAD83': "North American Datum 1983",
                        'North American Datum 1983': "North American Datum 1983",
                        '83HARN': "North American Datum 1983 HARN",
                        'NSRS07': "NAD83 (NSRS2007)",
                        'NP': "NP"
                        }
                        x = D_Horiz_Datum[H_DATUM]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                # incomplete
                if field.name == 'PROJECTION':
                    try:
                        count += 1
                        arcpy.management.CalculateField(
                            dbf,
                            "PROJECTION",
                            expression="MatchDescrip(!PROJECTION!)",
                            expression_type="PYTHON3",
                            code_block="""def MatchDescrip(PROJECTION):
                            D_Proj = {
                            ' ': " ",
                            'GCS': "GEOGRAPHIC COORDINATE SYSTEM",
                            '9000': "OTHER",
                            '0301': "STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS NORTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS NORTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS NORTH ZONE",
                            '0302': "STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS SOUTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS SOUTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS SOUTH ZONE",
                            '3501': "STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA NORTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA NORTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA NORTH ZONE",
                            '3502': "STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA SOUTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA SOUTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA SOUTH ZONE",
                            '4203': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS CENTRAL ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS CENTRAL ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS CENTRAL ZONE",
                            '4202': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH CENTRAL ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH CENTRAL ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH CENTRAL ZONE",
                            '4201': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH ZONE",
                            '4204': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH CENTRAL ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH CENTRAL ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH CENTRAL ZONE",
                            '4205': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH ZONE",
                            'UTM': "UNIVERSAL TRANSVERSE MERCATOR",
                            'UNIVERSAL TRANSVERSE MERCATOR': "UNIVERSAL TRANSVERSE MERCATOR",
                            'NP': "NP"
                            }
                            x = D_Proj[PROJECTION]
                            return x
                        """,
                            field_type="TEXT",
                            enforce_domains="NO_ENFORCE_DOMAINS"
                        )
                    except KeyError:
                        fname = field.name
                        error_message = arcpy.AddError(arcpy.GetMessages(2))
                        arcpy.AddMessage(f"{error_message}")
                        arcpy.AddMessage(f"The above attribute value could not be matched to a domain code for field {fname} in {dbf}.")
                # incomplete
                if field.name == 'PROJ_SECND':
                    try:
                        count += 1
                        arcpy.management.CalculateField(
                            dbf,
                            "PROJ_SECND",
                            expression="MatchDescrip(!PROJ_SECND!)",
                            expression_type="PYTHON3",
                            code_block="""def MatchDescrip(PROJ_SECND):
                            D_Proj = {
                            ' ': " ",
                            'GCS': "GEOGRAPHIC COORDINATE SYSTEM",
                            '9000': "OTHER",
                            '0301': "STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS NORTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS NORTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS NORTH ZONE",
                            '0302': "STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS SOUTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS SOUTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, ARKANSAS SOUTH ZONE",
                            '3501': "STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA NORTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA NORTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA NORTH ZONE",
                            '3502': "STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA SOUTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA SOUTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, OKLAHOMA SOUTH ZONE",
                            '4203': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS CENTRAL ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS CENTRAL ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS CENTRAL ZONE",
                            '4202': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH CENTRAL ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH CENTRAL ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH CENTRAL ZONE",
                            '4201': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS NORTH ZONE",
                            '4204': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH CENTRAL ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH CENTRAL ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH CENTRAL ZONE",
                            '4205': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH ZONE",
                            'STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH ZONE': "STATE PLANE LAMBERT CONFORMAL CONIC, TEXAS SOUTH ZONE",
                            'UTM': "UNIVERSAL TRANSVERSE MERCATOR",
                            'UNIVERSAL TRANSVERSE MERCATOR': "UNIVERSAL TRANSVERSE MERCATOR",
                            'NP': "NP"
                            }
                            x = D_Proj[PROJ_SECND]
                            return x
                        """,
                            field_type="TEXT",
                            enforce_domains="NO_ENFORCE_DOMAINS"
                        )
                    except KeyError:
                        fname = field.name
                        error_message = arcpy.AddError(arcpy.GetMessages(2))
                        arcpy.AddMessage(f"{error_message}")
                        arcpy.AddMessage(f"The above attribute value could not be matched to a domain code for field {fname} in {dbf}.")
                if field.name == 'PROJ_UNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "PROJ_UNIT",
                        expression="MatchDescrip(!PROJ_UNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(PROJ_UNIT):
                        D_Proj_Unit = {
                        ' ': " ",
                        'FT': "Feet",
                        'Feet': "Feet",
                        'USFT': "US Survey Feet",
                        'US Survey Feet': "US Survey Feet",
                        'INTLFT': "International Feet",
                        'METER': "Meters",
                        'Meters': "Meters",
                        'DECDEG': "Decimal Degrees",
                        'Decimal Degrees': "Decimal Degrees",
                        'NP': "NP"
                        }
                        x = D_Proj_Unit[PROJ_UNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'PROJ_SUNIT':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "PROJ_SUNIT",
                        expression="MatchDescrip(!PROJ_SUNIT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(PROJ_SUNIT):
                        D_Proj_Unit = {
                        ' ': " ",
                        'FT': "Feet",
                        'Feet': "Feet",
                        'USFT': "US Survey Feet",
                        'US Survey Feet': "US Survey Feet",
                        'INTLFT': "International Feet",
                        'METER': "Meters",
                        'Meters': "Meters",
                        'DECDEG': "Decimal Degrees",
                        'Decimal Degrees': "Decimal Degrees",
                        'NP': "NP"
                        }
                        x = D_Proj_Unit[PROJ_SUNIT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'EVENT_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "EVENT_TYP",
                        expression="MatchDescrip(!EVENT_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(EVENT_TYP):
                        D_Event = {
                        '50pct': "50 Percent Chance",
                        '04pct': "4 Percent Chance",
                        '4 Percent Chance': "4 Percent Chance",
                        '02pct': "2 Percent Chance",
                        '2 Percent Chance': "2 Percent Chance",
                        '01plus': "1 Percent Plus Chance",
                        '01minus': "1 Percent Minus Chance",
                        '01pct': "1 Percent Chance",
                        '1 Percent Chance': "1 Percent Chance",
                        '0_2pct': "0.2 Percent Chance",
                        '0.2 Percent Chance': "0.2 Percent Chance",
                        '01pctfut': "1 Percent Chance Future Conditions",
                        '10pct': "10 Percent Chance",
                        '10 Percent Chance': "10 Percent Chance",
                        '20pct': "20 Percent Chance"
                        }
                        x = D_Event[EVENT_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'STRUC_FACE':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "STRUC_FACE",
                        expression="MatchDescrip(!STRUC_FACE!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(STRUC_FACE):
                        D_Struct_Face = {
                        'UP': "Upstream",
                        'Upstream': "Upstream",
                        'DN': "Downstream",
                        'Downstream': "Downstream",
                        'UNK': "Unknown",
                        'Unknown': "Unknown"
                        }
                        x = D_Struct_Face[STRUC_FACE]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'ORIENT':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "ORIENT",
                        expression="MatchDescrip(!ORIENT!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(ORIENT):
                        D_Orient = {
                        'H': "Horizontal",
                        'Horizontal': "Horizontal",
                        'V': "Vertical",
                        'Vertical': "Vertical"
                        }
                        x = D_Orient[ORIENT]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'ADJUSTED':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "ADJUSTED",
                        expression="MatchDescrip(!ADJUSTED!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(ADJUSTED):
                        D_Adjust = {
                        'L': "Left",
                        'Left': "Left",
                        'R': "Right",
                        'Right': "Right",
                        'C': "Center",
                        'Center': "Center",
                        'T': "Top",
                        'Top': "Top",
                        'M': "Middle",
                        'Middle': "Middle",
                        'B': "Bottom",
                        'Bottom': "Bottom"
                        }
                        x = D_Adjust[ADJUSTED]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'STATE':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "STATE",
                        expression="MatchDescrip(!STATE!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(STATE):
                        D_State = {
                        ' ': " ",
                        'AL': "Alabama",
                        'AK': "Alaska",
                        'AS': "American Samoa",
                        'AR': "Arkansas",
                        'Arkansas': "Arkansas",
                        'AZ': "Arizona",
                        'CA': "California",
                        'CO': "Colorado",
                        'CT': "Connecticut",
                        'DE': "Delaware",
                        'DC': "District of Columbia",
                        'FL': "Florida",
                        'GA': "Georgia",
                        'GU': "Guam",
                        'HI': "Hawaii",
                        'ID': "Idaho",
                        'IL': "Illinois",
                        'IN': "Indiana",
                        'IA': "Iowa",
                        'KS': "Kansas",
                        'KY': "Kentucky",
                        'LA': "Louisiana",
                        'Louisiana': "Louisiana",
                        'ME': "Maine",
                        'MH': "Marshall Islands",
                        'MD': "Maryland",
                        'MA': "Massachusetts",
                        'MI': "Michigan",
                        'FM': "Micronesia",
                        'MN': "Minnesota",
                        'MS': "Mississippi",
                        'MO': "Missouri",
                        'MT': "Montana",
                        'NE': "Nebraska",
                        'NV': "Nevada",
                        'NH': "New Hampshire",
                        'NJ': "New Jersey",
                        'NM': "New Mexico",
                        'New Mexico': "New Mexico",
                        'NY': "New York",
                        'NC': "North Carolina",
                        'ND': "North Dakota",
                        'MP': "Northern Mariana Islands",
                        'OH': "Ohio",
                        'OK': "Oklahoma",
                        'Oklahoma': "Oklahoma",
                        'OR': "Oregon",
                        'PW': "Palau",
                        'PA': "Pennsylvania",
                        'PR': "Puerto Rico",
                        'RI': "Rhode Island",
                        'SC': "South Carolina",
                        'SD': "South Dakota",
                        'South Dakota': "South Dakota",
                        'TN': "Tennessee",
                        'TX': "Texas",
                        'Texas': "Texas",
                        'UM': "U.S. Minor Islands",
                        'UT': "Utah",
                        'VT': "Vermont",
                        'VA': "Virginia",
                        'VI': "Virgin Islands",
                        'WA': "Washington",
                        'WV': "West Virginia",
                        'WY': "Wyoming",
                        'NP': "NP",
                        'WI': "Wisconsin"
                        }
                        x = D_State[STATE]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'REPOS_ST':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "REPOS_ST",
                        expression="MatchDescrip(!REPOS_ST!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(REPOS_ST):
                        D_State = {
                        ' ': " ",
                        'AL': "Alabama",
                        'AK': "Alaska",
                        'AS': "American Samoa",
                        'AR': "Arkansas",
                        'Arkansas': "Arkansas",
                        'AZ': "Arizona",
                        'CA': "California",
                        'CO': "Colorado",
                        'CT': "Connecticut",
                        'DE': "Delaware",
                        'DC': "District of Columbia",
                        'FL': "Florida",
                        'GA': "Georgia",
                        'GU': "Guam",
                        'HI': "Hawaii",
                        'ID': "Idaho",
                        'IL': "Illinois",
                        'IN': "Indiana",
                        'IA': "Iowa",
                        'KS': "Kansas",
                        'KY': "Kentucky",
                        'LA': "Louisiana",
                        'Louisiana': "Louisiana",
                        'ME': "Maine",
                        'MH': "Marshall Islands",
                        'MD': "Maryland",
                        'MA': "Massachusetts",
                        'MI': "Michigan",
                        'FM': "Micronesia",
                        'MN': "Minnesota",
                        'MS': "Mississippi",
                        'MO': "Missouri",
                        'MT': "Montana",
                        'NE': "Nebraska",
                        'NV': "Nevada",
                        'NH': "New Hampshire",
                        'NJ': "New Jersey",
                        'NM': "New Mexico",
                        'New Mexico': "New Mexico",
                        'NY': "New York",
                        'NC': "North Carolina",
                        'ND': "North Dakota",
                        'MP': "Northern Mariana Islands",
                        'OH': "Ohio",
                        'OK': "Oklahoma",
                        'Oklahoma': "Oklahoma",
                        'OR': "Oregon",
                        'PW': "Palau",
                        'PA': "Pennsylvania",
                        'PR': "Puerto Rico",
                        'RI': "Rhode Island",
                        'SC': "South Carolina",
                        'SD': "South Dakota",
                        'South Dakota': "South Dakota",
                        'TN': "Tennessee",
                        'TX': "Texas",
                        'Texas': "Texas",
                        'UM': "U.S. Minor Islands",
                        'UT': "Utah",
                        'VT': "Vermont",
                        'VA': "Virginia",
                        'VI': "Virgin Islands",
                        'WA': "Washington",
                        'WV': "West Virginia",
                        'WY': "Wyoming",
                        'NP': "NP",
                        'WI': "Wisconsin"
                        }
                        x = D_State[REPOS_ST]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'STATE_NM':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "STATE_NM",
                        expression="MatchDescrip(!STATE_NM!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(STATE_NM):
                        D_State = {
                        ' ': " ",
                        'AL': "Alabama",
                        'AK': "Alaska",
                        'AS': "American Samoa",
                        'AR': "Arkansas",
                        'Arkansas': "Arkansas",
                        'AZ': "Arizona",
                        'CA': "California",
                        'CO': "Colorado",
                        'CT': "Connecticut",
                        'DE': "Delaware",
                        'DC': "District of Columbia",
                        'FL': "Florida",
                        'GA': "Georgia",
                        'GU': "Guam",
                        'HI': "Hawaii",
                        'ID': "Idaho",
                        'IL': "Illinois",
                        'IN': "Indiana",
                        'IA': "Iowa",
                        'KS': "Kansas",
                        'KY': "Kentucky",
                        'LA': "Louisiana",
                        'Louisiana': "Louisiana",
                        'ME': "Maine",
                        'MH': "Marshall Islands",
                        'MD': "Maryland",
                        'MA': "Massachusetts",
                        'MI': "Michigan",
                        'FM': "Micronesia",
                        'MN': "Minnesota",
                        'MS': "Mississippi",
                        'MO': "Missouri",
                        'MT': "Montana",
                        'NE': "Nebraska",
                        'NV': "Nevada",
                        'NH': "New Hampshire",
                        'NJ': "New Jersey",
                        'NM': "New Mexico",
                        'New Mexico': "New Mexico",
                        'NY': "New York",
                        'NC': "North Carolina",
                        'ND': "North Dakota",
                        'MP': "Northern Mariana Islands",
                        'OH': "Ohio",
                        'OK': "Oklahoma",
                        'Oklahoma': "Oklahoma",
                        'OR': "Oregon",
                        'PW': "Palau",
                        'PA': "Pennsylvania",
                        'PR': "Puerto Rico",
                        'RI': "Rhode Island",
                        'SC': "South Carolina",
                        'SD': "South Dakota",
                        'South Dakota': "South Dakota",
                        'TN': "Tennessee",
                        'TX': "Texas",
                        'Texas': "Texas",
                        'UM': "U.S. Minor Islands",
                        'UT': "Utah",
                        'VT': "Vermont",
                        'VA': "Virginia",
                        'VI': "Virgin Islands",
                        'WA': "Washington",
                        'WV': "West Virginia",
                        'WY': "Wyoming",
                        'NP': "NP",
                        'WI': "Wisconsin"
                        }
                        x = D_State[STATE_NM]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'MTG_TYP':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "MTG_TYP",
                        expression="MatchDescrip(!MTG_TYP!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(MTG_TYP):
                        D_Mtg_Typ = {
                        '1000': "CCO",
                        'CCO': "CCO",
                        '1010': "Flood Risk Review",
                        '1040': "Project Discovery",
                        'Project Discovery': "Project Discovery",
                        '1050': "Resilience",
                        '1060': "Scoping",
                        'Scoping': "Scoping",
                        '9000': "Other",
                        'Other': "Other",
                        'NP': "NP"
                        }
                        x = D_Mtg_Typ[MTG_TYP]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
                if field.name == 'LOC_ACC':
                    count += 1
                    arcpy.management.CalculateField(
                        dbf,
                        "LOC_ACC",
                        expression="MatchDescrip(!LOC_ACC!)",
                        expression_type="PYTHON3",
                        code_block="""def MatchDescrip(LOC_ACC):
                        D_Mtg_Typ = {
                        'H': "High",
                        'High': "High",
                        'M': "Medium",
                        'Medium': "Medium",
                        'L': "Low",
                        'Low': "Low"
                        }
                        x = D_Mtg_Typ[LOC_ACC]
                        return x
                    """,
                        field_type="TEXT",
                        enforce_domains="NO_ENFORCE_DOMAINS"
                    )
            arcpy.AddMessage(f"Converted {count} fields in {dbf}.")


class EndStationSelect(object):
    def __init__(self):
        self.label = "End Station Select"
        self.description = "Sort and group cross section features by station number and stream name and" \
            " select the end (furthest) cross section for each named stream."
    def getParameterInfo(self):
    # Define parameters
        # Data type must be GPFeatureLayer to select in map
        fc = arcpy.Parameter(
            name='Input XS Features',
            displayName='Input XS Lines',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required'
        )
        fc.filter.list = ["Polyline"]
        params = [fc]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        arcpy.env.addOutputsToMap = True
        fc = parameters[0].valueAsText
        sedf = pd.DataFrame.spatial.from_featureclass(fc)
        # Sort by stream name and station number, group by stream name, and give the first record from each group
        fr = sedf.sort_values(['WTR_NM', 'STREAM_STN'],ascending=False).groupby('WTR_NM').head(1)
        s_array = fr[['WTR_NM', 'STREAM_STN']].values
        strms = len(s_array)
        count = 0
        arcpy.SetProgressor(
                type="STEP", 
                message=f"Selecting {strms} cross section features...",
                min_range=0,
                max_range=strms,
                step_value=1)
        for item in s_array:
            count += 1
            arcpy.SetProgressorLabel(f"Selecting feature {count} of {strms}...")
            arcpy.SetProgressorPosition()
            string = str(item)
            split = string.split("' ")
            part1 = split[0]
            name = part1[2:]
            qname = f"'{name}'"
            part2 = split[1]
            end = part2.index("]")
            station = int(float(part2[:end]))
            wc = f"WTR_NM = {qname}" + f" And STREAM_STN = {station}"
            arcpy.management.SelectLayerByAttribute(
                in_layer_or_view=fc,
                selection_type="ADD_TO_SELECTION",
                where_clause=wc,
                invert_where_clause=None
            )     
        arcpy.AddMessage(f"Selected {count} cross sections.")
        arcpy.SetProgressorLabel("Exporting new feature class...")
        arcpy.conversion.ExportFeatures(fc, "End_XS")
        arcpy.AddMessage("Exported new feature class to current workspace gdb.")


class StartStations(object):
    def __init__(self):
        self.label = "Generate Start Stations"
        self.description = "Generate points at the start (begin) vertices of each tributary stream and /"
        "attribute with stream name. *For some reason needs 'end' point location parameter although appears at starts*"
    def getParameterInfo(self):
    # Define parameters
        fd = arcpy.Parameter(
            name='Input Workspace',
            displayName='Input Workspace',
            datatype='DEWorkspace',
            direction='Input',
            parameterType='Required'
        )
        fc = arcpy.Parameter(
            name='Input Water Line Features',
            displayName='Input Water Lines',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required'
        )
        fc.filter.list = ["Polyline"]
        params = [fd, fc]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
    # Setup variables
        fd = parameters[0].valueAsText
        fc = parameters[1].valueAsText
        arcpy.env.workspace = fd  
        arcpy.env.addOutputsToMap = True
    # Dissolve water lines
        arcpy.management.Dissolve(
            in_features=fc, 
            out_feature_class="WTR_LN_Dissolve", 
            dissolve_field=["WTR_NM"])
    # Get start points from vertices
        with arcpy.EnvManager(outputZFlag="Disabled", outputMFlag="Disabled"):
            arcpy.management.FeatureVerticesToPoints(
                in_features="WTR_LN_Dissolve", 
                out_feature_class="Start_pts", 
                point_location="END")
        ptcount = arcpy.management.GetCount("Start_pts")
    # Delete duplicate points
        arcpy.management.DeleteIdentical(
            in_dataset="S_Stn_Start",
            fields="SHAPE",
            xy_tolerance=None,
            z_tolerance=0)
    # Get summary statistics for joined start points
        arcpy.analysis.Statistics(
            in_table="Start_pts",
            out_table="Start_pts_Statistics",
            statistics_fields="WTR_NM COUNT",
            case_field="WTR_NM",
            concatenation_separator="") 
    # Calculate attributes
        arcpy.management.CalculateField(
            in_table="Start_pts",
            field="START_DESC",
            expression="'Stream distance in feet above confluence with ' + $feature.WTR_NM",
            expression_type="ARCADE",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS")
        arcpy.management.CalculateField(
    in_table="Start_pts",
    field="START_ID",
    expression="CalcThis()",
    expression_type="PYTHON3",
    code_block="""Base = 100
def CalcThis():
    global Base
    Base += 1
    return Base""",
    field_type="TEXT",
    enforce_domains="NO_ENFORCE_DOMAINS")
        arcpy.management.CalculateField(
            in_table="Start_pts",
            field="LOC_ACC",
            expression="'H'",
            expression_type="ARCADE",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS")  
        arcpy.AddMessage(f"Generated and attributed {ptcount} station start points.")
    # Delete intermediate files
        arcpy.management.Delete(
            "WTR_LN_Dissolve", '')
        arcpy.AddMessage("Deleted intermediate file")


class Indx_Wtr_Features(object):
    def __init__(self):
        self.label = "Index Water Features"
        self.description = "Select major water features by name and attribute to show on FIRM Index."
        
    def getParameterInfo(self):
    # Define parameters
        fgdb = arcpy.Parameter(
            name='Input Workspace',
            displayName='Input Workspace',
            datatype='DEWorkspace',
            direction='Input',
            parameterType='Required'
        )
        wl = arcpy.Parameter(
            name='Water Lines',
            displayName='Water Lines',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required',
            multiValue = False
        )
        wl.filter.list = ["Polyline"]
        wa = arcpy.Parameter(
            name='Water Polygons',
            displayName='Water Polygons',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required',
            multiValue = False
        )
        wa.filter.list = ["Polygon"]
        params = [fgdb, wl, wa]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        fgdb = parameters[0].valueAsText
        wl = parameters[1].valueAsText
        wa = parameters[2].valueAsText
        arcpy.env.workspace = fgdb
        ## Water Lines
        # First make sure all are turned off (SHOWN_INDX = "F")
        arcpy.management.CalculateField(
            in_table=wl,
            field="SHOWN_INDX",
            expression='"F"',
            expression_type="PYTHON3",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
        )
        # Next select all not named NP
        notnp = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=wl,
            selection_type="NEW_SELECTION",
            where_clause="WTR_NM <> 'NP' And WTR_NM NOT LIKE '%UNT%'",
            invert_where_clause=None
        )
        # Next make names title case 
        arcpy.management.CalculateField(
            in_table=notnp,
            field="WTR_NM",
            expression="!WTR_NM!.title()",
            expression_type="PYTHON3",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
        )
        # Next select major names
        major = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=wl,
            selection_type="NEW_SELECTION",
            where_clause="WTR_NM LIKE '%Creek%' Or WTR_NM LIKE '%River%' Or WTR_NM LIKE '%Bayou%' Or WTR_NM LIKE '%Branch%'",
            invert_where_clause=None
        )
        # Then exclude tributaries and numbered streams
        nonum = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=major,
            selection_type="SUBSET_SELECTION",
            where_clause="WTR_NM NOT LIKE '%TRIBUTARY%' And WTR_NM NOT LIKE '%1%' And WTR_NM NOT LIKE '%2%' And WTR_NM NOT LIKE '%3%' And WTR_NM NOT LIKE '%4%' And WTR_NM NOT LIKE '%5%' And WTR_NM NOT LIKE '%6%' And WTR_NM NOT LIKE '%7%' And WTR_NM NOT LIKE '%8%' And WTR_NM NOT LIKE '%9%'",
            invert_where_clause=None
        )
        # Then exclude streams with direction
        nodir = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=nonum,
            selection_type="SUBSET_SELECTION",
            where_clause="WTR_NM NOT LIKE '%North%' And WTR_NM NOT LIKE '%East%' And WTR_NM NOT LIKE '%South%' And WTR_NM NOT LIKE '%West%'",
            invert_where_clause=None
        )
        # Then exclude unnamed streams
        named = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=nodir,
            selection_type="SUBSET_SELECTION",
            where_clause="WTR_NM NOT LIKE '%NP%' And WTR_NM NOT LIKE '%Unnamed%' And WTR_NM NOT LIKE '%UNT%'",
            invert_where_clause=None
        )
        # Lastly exclude by length
        wl_fields = []
        wlf = arcpy.ListFields(wl)
        for f in wlf:
            wl_fields.append(f.name)
        long_enough = []
        if "SHAPE_Length" in wl_fields:
            arcpy.analysis.Statistics(
                in_table=named,
                out_table=rf"{fgdb}\Length_Statistics",
                statistics_fields="SHAPE_Length SUM",
                case_field="WTR_NM",
                concatenation_separator=""
            )
            cursor = arcpy.da.SearchCursor(
            rf"{fgdb}\Length_Statistics", 
            ['OBJECTID', 'WTR_NM', 'SUM_SHAPE_Length']
            )
            for row in cursor:
                if row[2] >= 0.22:
                    long_enough.append(row[1])
                else:
                    continue
        elif "SHAPE_Leng" in wl_fields:
            arcpy.analysis.Statistics(
                in_table=named,
                out_table=rf"{fgdb}\Length_Statistics",
                statistics_fields="SHAPE_Leng SUM",
                case_field="WTR_NM",
                concatenation_separator=""
            )
            cursor = arcpy.da.SearchCursor(
            rf"{fgdb}\Length_Statistics", 
            ['OBJECTID', 'WTR_NM', 'SUM_SHAPE_Leng']
            )
            for row in cursor:
                if row[2] >= 0.22:
                    long_enough.append(row[1])
                else:
                    continue
        # arcpy.AddMessage(long_enough)
        # Turn list into tuple for valid expression
        long_enough = tuple(long_enough)
        final = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=wl,
            selection_type="NEW_SELECTION",
            where_clause=f"WTR_NM IN {long_enough}",
            invert_where_clause=None
        )
        wl_count = arcpy.management.GetCount(final)
        # Turn selected features on
        arcpy.management.CalculateField(
            in_table=named,
            field="SHOWN_INDX",
            expression='"T"',
            expression_type="PYTHON3",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
        )
        arcpy.AddMessage(f"Turned on {wl_count} water line features.")
        ## Water Polygons
        # First make sure all are turned off (SHOWN_INDX = "F")
        arcpy.management.CalculateField(
            in_table=wa,
            field="SHOWN_INDX",
            expression='"F"',
            expression_type="PYTHON3",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
        )
        # Next select named
        major = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=wa,
            selection_type="NEW_SELECTION",
            where_clause="WTR_NM NOT LIKE '%NP%' And WTR_NM NOT LIKE '%NONAME%' And WTR_NM NOT LIKE '%noname%' And WTR_NM NOT LIKE '%no name%' And WTR_NM NOT LIKE '%No Name%' And WTR_NM NOT LIKE '%Unnamed%' And WTR_NM NOT LIKE '%UNNAMED%'",
            invert_where_clause=None
        )
        # Next make names title case 
        arcpy.management.CalculateField(
            in_table=major,
            field="WTR_NM",
            expression="!WTR_NM!.title()",
            expression_type="PYTHON3",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
        )
        # Lastly exclude numbered lakes
        nonum = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=major,
            selection_type="SUBSET_SELECTION",
            where_clause="WTR_NM NOT LIKE '%1%' And WTR_NM NOT LIKE '%2%' And WTR_NM NOT LIKE '%3%' And WTR_NM NOT LIKE '%4%' And WTR_NM NOT LIKE '%5%' And WTR_NM NOT LIKE '%6%' And WTR_NM NOT LIKE '%7%' And WTR_NM NOT LIKE '%8%' And WTR_NM NOT LIKE '%9%'",
            invert_where_clause=None
        )
        wa_count = arcpy.management.GetCount(nonum)
        # Turn selected features on
        arcpy.management.CalculateField(
            in_table=nonum,
            field="SHOWN_INDX",
            expression='"T"',
            expression_type="PYTHON3",
            code_block="",
            field_type="TEXT",
            enforce_domains="NO_ENFORCE_DOMAINS"
        )
        arcpy.AddMessage(f"Turned on {wa_count} water area features.")
        

class Append_XS_Elev(object):
    def __init__(self):
        self.label = "Match & Load L_XS_Elev"
        self.description = "Select matching L_XS_Elev rows and append to working L_XS_Elev table."
        
    def getParameterInfo(self):
    # Define parameters
        fgdb = arcpy.Parameter(
            name='Input Workspace',
            displayName='Input Workspace',
            datatype='DEWorkspace',
            direction='Input',
            parameterType='Required'
        )
        xs = arcpy.Parameter(
            name='Input XS',
            displayName='Input XS',
            datatype='GPFeatureLayer',
            direction='Input',
            parameterType='Required'
        )
        xs.filter.list = ["Polyline"]
        xs_field = arcpy.Parameter(
            name='XS Join Field',
            displayName='XS Join Field',
            datatype='Field',
            direction='Input',
            parameterType='Required'
        )
        xs_elev_j = arcpy.Parameter(
            name='Join L_XS_Elev Table',
            displayName='Join L_XS_Elev Table',
            datatype='GPTableView',
            direction='Input',
            parameterType='Required'
        )
        xs_elev_i = arcpy.Parameter(
            name='Input L_XS_Elev Table',
            displayName='Input L_XS_Elev Table',
            datatype='GPTableView',
            direction='Input',
            parameterType='Required'
        )
        params = [xs, xs_field, xs_elev_j, xs_elev_i]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        xs = parameters[0].valueAsText
        xs_field = parameters[1].valueAsText
        xs_elev_j = parameters[2].valueAsText
        xs_elev_i = parameters[3].valueAsText
        # Create list of XS_LN_IDs
        xs_id_list = []
        cursor_input = arcpy.da.SearchCursor(
            rf"{xs}", 
            ['OBJECTID', f'{xs_field}']
            )
        for row in cursor_input:
            xs_id_list.append(row[1])
        # Turn list into tuple for valid expression
        xs_id_list = tuple(xs_id_list)
        # Select matching rows in Join L_XS_Elev Table
        matching = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=xs_elev_j,
            selection_type="NEW_SELECTION",
            where_clause=f"XS_LN_ID IN {xs_id_list}",
            invert_where_clause=None
        )
        count = arcpy.management.GetCount(matching)
        # Append selected rows
        arcpy.management.Append(
            f"{matching}", 
            f"{xs_elev_i}", 
            "NO_TEST"
            )
        arcpy.AddMessage(f"Appended {count} rows from Join L_XS_Elev table.")
        
