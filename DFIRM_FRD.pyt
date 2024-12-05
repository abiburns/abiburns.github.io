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
        self.tools = [Remove_Add_SpatialIndex, MatchCodes, EndStationSelect, StartStations]


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

class MatchCodes(object):
    def __init__(self):
        self.label = "Codes to Descriptions"
        self.description = "Convert input feature classes to shapefiles," \
        " then iterate through the shapefiles and replace domain codes with their matching descriptions."

    def getParameterInfo(self):
        # Define parameters
        folder = arcpy.Parameter(
            name='Output Folder',
            displayName='Output Folder',
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
        arcpy.AddMessage("Converting to shapefile (NOTE: May need to increase field length).")
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
                        if str([VEL_UNIT]) in D_Velocity_Units:
                            x = D_Velocity_Units[VEL_UNIT]
                            return x
                        else:
                            return [VEL_UNIT]
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
            arcpy.AddMessage(f"Converted {count} fields in {shp}.")


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
        fc.filter.list = ["Line"]
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
            arcpy.SetProgressorLabel("Selecting feature {0} of {1}...".format(count, strms))
            arcpy.SetProgressorPosition()
            string = str(item)
            split = string.split("' ")
            part1 = split[0]
            name = part1[2:]
            qname = "'{0}'".format(name)
            part2 = split[1]
            end = part2.index("]")
            station = int(float(part2[:end]))
            wc = "WTR_NM = {0}".format(qname) + " And STREAM_STN = {0}".format(station)
            arcpy.management.SelectLayerByAttribute(
                in_layer_or_view=fc,
                selection_type="ADD_TO_SELECTION",
                where_clause=wc,
                invert_where_clause=None
            )     
        arcpy.AddMessage("Selected {0} cross sections.".format(count))
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
        fc.filter.list = ["Line"]
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
        ptcoint = arcpy.management.GetCount("Start_pts")
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
    code_block="""Base = 0
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
        arcpy.AddMessage("Generated and attributed {0} station start points.".format(ptcoint))
                