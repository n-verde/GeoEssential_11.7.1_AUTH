# ============ FIND CITY PUBLIC OPEN SPACES =================
# Natalia Verde, AUTh, August 2020

# script for 11.7.1 indicator

# This script calculates the final index

# References:
# https://www.programcreek.com/python/example/101827/gdal.RasterizeLayer

# ============== IMPORTS =============================================
import pathlib
import os
import sys

import rasterio
from rasterio.mask import mask
import numpy as np
import geopandas as gpd
import gdal
import ogr

# ================= SETTINGS =========================================
# specify directory (volume conected via docker)
# HRL tiles for all europe exist in this folder
directory = 'volume'

# ================= FUNCTIONS =========================================

def raster2array(geotif_file):
    bands = 0
    dataset = rasterio.open(geotif_file)
    meta = dataset.meta
    profile = dataset.profile

    bands = meta['count']
    noDataValue = dataset.nodatavals

    if bands == 1:
        raster = dataset.read(1)

        # raster = raster[::-1] #inverse array because Python is column major
        return raster, profile

    elif bands > 1:
        print('More than one band ... need to modify function for case of multiple bands')

def Feature_to_Raster(input_shp, output_tiff,
                      cellsize, field_name=False, NoData_value=-9999):
    """
    Converts a shapefile into a raster
    """

    # Input
    inp_driver = ogr.GetDriverByName('ESRI Shapefile')
    inp_source = inp_driver.Open(input_shp, 0)
    inp_lyr = inp_source.GetLayer()
    inp_srs = inp_lyr.GetSpatialRef()

    # Extent
    x_min, x_max, y_min, y_max = inp_lyr.GetExtent()
    x_ncells = int((x_max - x_min) / cellsize)
    y_ncells = int((y_max - y_min) / cellsize)

    # Output
    out_driver = gdal.GetDriverByName('GTiff')
    if os.path.exists(output_tiff):
        out_driver.Delete(output_tiff)
    out_source = out_driver.Create(output_tiff, x_ncells, y_ncells,
                                   1, gdal.GDT_Byte)

    out_source.SetGeoTransform((x_min, cellsize, 0, y_max, 0, -cellsize))
    out_source.SetProjection(inp_srs.ExportToWkt())
    out_lyr = out_source.GetRasterBand(1)
    out_lyr.SetNoDataValue(NoData_value)

    # Rasterize
    if field_name:
        gdal.RasterizeLayer(out_source, [1], inp_lyr,
                            options=["ATTRIBUTE={0}".format(field_name)])
    else:
        gdal.RasterizeLayer(out_source, [1], inp_lyr, burn_values=[1])

    # Save and/or close the data sources
    inp_source = None
    out_source = None

    # Return
    return output_tiff

def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

# ================= MAIN PROGRAM ======================================

volume = pathlib.Path(directory)
urb_bua_path = volume / pathlib.Path('8-URBAN_CLUSTER_BUA.tif')

# ================= ================= =================

# 1. calculate total surface of open public space + land allocated to streets

# =================
# 1.1 reproject urban_aggl to match OSM files
urban_aggl_path =  volume / pathlib.Path('7-bounds.shp')
open_areas_path =  volume / pathlib.Path('9-osm_open_areas.shp')
roads_path =  volume / pathlib.Path('10-osm_roads.shp')

urban_aggl = gpd.read_file(str(urban_aggl_path))
open_areas = gpd.read_file(str(open_areas_path))
# reproject urban agglomeration to same projection as open areas
urban_aggl = urban_aggl.to_crs(open_areas.crs)
# urban_aggl = urban_aggl.assign(VALUE=1)
urban_aggl.to_file(str(urban_aggl_path)) # replace file

# =================
# 1.2 Turn all shapefiles to raster

print("Turning layers to raster ...")

rasterized = Feature_to_Raster(str(urban_aggl_path), (str(urban_aggl_path)[0:-4] + '.tif'), 1)
print("done urban area file")

rasterized = Feature_to_Raster(str(open_areas_path), (str(open_areas_path)[0:-4] + '.tif'), 1)
print("done OSM open areas file")

rasterized = Feature_to_Raster(str(roads_path), (str(roads_path)[0:-4] + '.tif'), 1)
print("done OSM roads file")

print("done.")

# =================
# 1.3 Mask to urban extent

print("Masking to urban extent ...")

coords = getFeatures(urban_aggl)

# open areas
raster = rasterio.open(str(open_areas_path)[0:-4] + '.tif')
out_meta = raster.meta.copy()  # Copy the metadata
open_areas_ext, out_transform = rasterio.mask.mask(raster, coords, crop=True)
out_meta.update({"driver": "GTiff", "height": open_areas_ext.shape[1], "width": open_areas_ext.shape[2],
                 "transform": out_transform})
# with rasterio.open(str(volume / pathlib.Path('test.tif')), "w", **out_meta) as dest:  # replace file with clipped one
#     dest.write(open_areas_ext)

# land allocated to streets
raster = rasterio.open(str(roads_path)[0:-4] + '.tif')
out_meta = raster.meta.copy()  # Copy the metadata
roads_ext, out_transform = rasterio.mask.mask(raster, coords, crop=True)
out_meta.update({"driver": "GTiff", "height": roads_ext.shape[1], "width": open_areas_ext.shape[2],
                 "transform": out_transform})
# with rasterio.open(str(volume / pathlib.Path('test.tif')), "w", **out_meta) as dest:  # replace file with clipped one
#     dest.write(roads_ext)

# =================
# 1.4 calculate total surface of open areas and roads in urban agglomeration

print("Calculating areas ...")

# ALSO CREATE A TEXT FILE TO SAVE PRINTS!
sys.stdout = open(str(directory / pathlib.Path('11-results.txt')), 'w')

# count pixels that are =1

# open areas
open_areas_pixels_sum = np.sum(open_areas_ext[0])
open_areas_area = open_areas_pixels_sum / (1000*1000) # pixel size = 20m, calculate in square km
print("TOTAL AREA OF OPEN AREAS: {x} square km".format(x=open_areas_area))

# roads (land allocated to streets)
LAS_pixels_sum = np.sum(roads_ext[0])
LAS_area = LAS_pixels_sum / (1000*1000) # pixel size = 20m, calculate in square km
print("TOTAL AREA OF LAND ALLOCATED TO STREETS: {x} square km".format(x=LAS_area))

# ================= ================= =================

# 2. calculate total surface of built-up area of the urban agglomeration

# read raster as np array
urb_bua = raster2array(str(urb_bua_path))
urb_bua[0][urb_bua[0]!=1] = 0 # change the values because rasterio reads it as uint8
# count pixels that are =1
bua_pixels_sum = np.sum(urb_bua[0])
bua_area = (bua_pixels_sum * (20 * 20)) / (1000*1000) # pixel size = 20m, calculate in square km

print("TOTAL BUILT-UP AREA OF URBAN AGGLOMERATION: {x} square km".format(x=bua_area))

# ================= ================= =================

# 3 calculate final index

i = ((open_areas_area + LAS_area) / bua_area) * 100

print("Value for SDG indicator 11.7.1: {v} %".format(v=i))

print("----------")
print("----------")
print("Successfully finished process for SDG indicator 11.7.1 calculation.")
print("----------")
print("----------")

sys.stdout.close()