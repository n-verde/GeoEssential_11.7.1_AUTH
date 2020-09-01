# ============ CITY AREA EXTRACTION =================
# Natalia Verde, AUTh, August 2020

# script for 11.7.1 indicator

# This script finds the city extent based on the UN instructions, and by combining HRL imperviousness with CLC land use

# References:
# https://www.neonscience.org/mask-raster-py
# https://github.com/jgomezdans/eoldas_ng_observations/blob/master/eoldas_ng_observations/eoldas_observation_helpers.py#L29
# https://stackoverflow.com/questions/36964875/sum-of-8-neighbors-in-2d-array
# https://github.com/Ciaran1981/geospatial-learn/blob/b4c62705e0f9f6a69698109a49d4d2589d3c2e64/geospatial_learn/raster.py

# ============== IMPORTS =============================================
import pathlib
import copy
import sys

import numpy as np
import math
import rasterio
from rasterio.mask import mask
import gdal
import cv2
from scipy.ndimage import convolve
import ogr
import osr
import geopandas as gpd

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


def reproject_image_to_master (master,slave):
    """This function reprojects an image (``slave``) to
    match the extent, resolution and projection of another
    (``master``) using GDAL. The newly reprojected image
    is a GDAL VRT file for efficiency. A different spatial
    resolution can be chosen by specifyign the optional
    ``res`` parameter. The function returns the new file's
    name.
    Parameters
    -------------
    master: str
        A filename (with full path if required) with the
        master image (that that will be taken as a reference)
    slave: str
        A filename (with path if needed) with the image
        that will be reprojected
    res: float, optional
        The desired output spatial resolution, if different
        to the one in ``master``.
    Returns
    ----------
    The reprojected filename
    """
    slave_ds = gdal.Open(slave)
    slave_proj = slave_ds.GetProjection()
    data_type = slave_ds.GetRasterBand(1).DataType
    n_bands = slave_ds.RasterCount

    master_ds = gdal.Open(master)
    master_proj = master_ds.GetProjection()
    master_geotrans = master_ds.GetGeoTransform()
    w = master_ds.RasterXSize
    h = master_ds.RasterYSize

    dst_filename = slave.replace( ".tif", "_resampled.tif" )
    dst_ds = gdal.GetDriverByName('GTiff').Create(dst_filename,
                                                w, h, n_bands, data_type)
    dst_ds.SetGeoTransform(master_geotrans)
    dst_ds.SetProjection(master_proj)

    gdal.ReprojectImage(slave_ds, dst_ds, slave_proj,
                         master_proj, gdal.GRA_NearestNeighbour)

    message = "reprojected CLC to match HRL"

    return message


def rescaleToUnint8(im):
    min = np.amin(im)
    max = np.amax(im)

    if (min < 0):  # if image contains negative values, turn to positive
        im = np.add(im, abs(min))
        max = max + abs(min)  # also change new max
    np.float32(im)
    norm = np.divide(im, max)  # normalize data to 0-1
    scaled = np.multiply(norm, 255)  # now scale to 255
    rescaled = np.uint8(scaled)

    return rescaled


def polygonize(inRas, outPoly, outField=None, mask=True, band=1, filetype="ESRI Shapefile"):
    """
    Lifted straight from the cookbook and gdal func docs.
    http://pcjericks.github.io/py-gdalogr-cookbook
    Parameters
    -----------

    inRas : string
            the input image


    outPoly : string
              the output polygon file path

    outField : string (optional)
             the name of the field containing burnded values
    mask : bool (optional)
            use the input raster as a mask
    band : int
           the input raster band

    """

    options = []
    src_ds = gdal.Open(inRas)
    if src_ds is None:
        print('Unable to open %s' % inRas)
        sys.exit(1)

    try:
        srcband = src_ds.GetRasterBand(band)
    except RuntimeError as e:
        # for example, try GetRasterBand(10)
        print('Band ( %i ) not found')
        print(e)
        sys.exit(1)
    if mask == True:
        maskband = src_ds.GetRasterBand(band)
        options.append('-mask')
    else:
        mask = False
        maskband = None

    srs = osr.SpatialReference()
    srs.ImportFromWkt( src_ds.GetProjectionRef() )

    #
    #  create output datasource
    #
    dst_layername = outPoly
    drv = ogr.GetDriverByName(filetype)
    dst_ds = drv.CreateDataSource(dst_layername)
    dst_layer = dst_ds.CreateLayer(dst_layername, srs=srs)

    if outField is None:
        dst_fieldname = 'DN'
        fd = ogr.FieldDefn(dst_fieldname, ogr.OFTInteger)
        dst_layer.CreateField(fd)
        dst_field = dst_layer.GetLayerDefn().GetFieldIndex(dst_fieldname)

    else:
        dst_field = dst_layer.GetLayerDefn().GetFieldIndex(outField)

    gdal.Polygonize(srcband, maskband, dst_layer, dst_field,
                    callback=gdal.TermProgress)
    dst_ds.FlushCache()

    srcband = None
    src_ds = None
    dst_ds = None

def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

def main():

    # ================= SETTINGS =========================================
    # specify directory (volume conected via docker)
    directory = ''
    # specify AOI in the form of a shapefile
    shpName = 'aoi.shp'
    # specify HRL imperviousness mosaicked + clipped layer (to AOI)
    hrlName = '1-HRL_AOI.tif'
    # specify CLC clipped layer (to AOI)
    clcName = '2-CLC_AOI.tif'

    # ================= MAIN PROGRAM ======================================
    volume = pathlib.Path(directory)
    shp_file_path = volume / pathlib.Path(shpName)
    hrl_path = volume / pathlib.Path(hrlName)
    clc_path = volume / pathlib.Path(clcName)

    clc = raster2array(str(clc_path))
    hrl = raster2array(str(hrl_path))
    HRLpixelSize = round(hrl[1]['transform'][0])

    print("Masking areas in CLC that do not belong to urban areas ...")

    # mask (with 0) classes that are not of interest
    # keep classes 1,2,3,10,11
    clc_urban = copy.copy(clc[0])
    clc_urban = np.where((clc[0]<=3),clc_urban,0)
    clc_urban = np.where((clc[0]==10),clc[0],clc_urban)
    clc_urban = np.where((clc[0]==11),clc[0],clc_urban)

    profile = clc[1]

    # export processed CLC raster with urban classes
    with rasterio.open(str(volume / '3-CLC_AOI_urban.tif') , 'w', **profile) as dst:
        dst.write_band(1, clc_urban)

    print("done.")

    print("Masking HRL imperviousness layer, based on CLC urban areas ...")

    reproject_image_to_master(str(hrl_path),str(volume / '3-CLC_AOI_urban.tif'))
    clc_res = raster2array(str(volume / '3-CLC_AOI_urban') + '_resampled.tif')

    clc_hrl_urban = copy.copy(clc_res[0])
    clc_hrl_urban = np.where((clc_res[0]!=0),hrl[0],0)
    clc_hrl_urban = np.where((clc_hrl_urban!=0),1,0)
    clc_hrl_urban = clc_hrl_urban.astype('uint8')

    profile = hrl[1]

    # export processed CLC raster with urban classes
    with rasterio.open(str(volume / '4-CLC_HRL_AOI_urban.tif') , 'w', **profile) as dst:
        dst.write_band(1, clc_hrl_urban)

    del clc_urban, hrl

    print("done.")

    """"
    Assess the level of urban-ness for each of the resultant built-up pixels. 
    Place a 1-km2 circle around each built-up pixel and calculate the share of pixels in the circle that are also built-up.
    If >=50% of the pixels in the circle are built-up, the pixel is classified as Urban. If >=25% and <50% of the pixels in
    the circle are built-up, the pixel is classified as Suburban. If <25% of the pixels in the circle are built-up, the 
    pixel is classified as Rural.
    Combine contiguous urban and suburban pixels to form an urban cluster of the built-up area.
    """

    print("Finding level of urban-ness with walking window and UN instructions ...")

    # kernel according to UN instructions should be 1km2 in area
    # the kernel is always a square so with basic trigonometry we can find the size of the kernel
    # A = πr^2 and r^2 + r^2 = a^2
    r = math.sqrt(1/math.pi) # km
    aKm = math.sqrt(math.pow(r,2)+math.pow(r,2)) # km
    a = aKm * 1000 # m


    # create a kernel of 1km in x pixels
    # eg. 1km is 50 pixels in the 20m-pixel size of HRL
    kernelSize = int(a/HRLpixelSize)
    kernel = np.ones((kernelSize,kernelSize),np.uint32)

    # cast img to np.uint32
    img32 = clc_hrl_urban.astype(np.uint32)

    # do the convolution to get neighborhood sum
    c = convolve(img32, kernel, mode='constant')

    # get >=25% threshold for built-up image
    # eg. in the binary built-up image, 100% built-up means neighborhood sum for each pixel = 2500
    #       >=25% means sum 2500/4 >= 625
    #       so threshold to 625 to get urban cluster
    perc100 = kernelSize*kernelSize
    percLarger25 = perc100/4
    thresh = copy.copy(c)
    thresh[thresh < int(round(percLarger25))] = 0
    del c, img32

    print("done.")

    print("Finding city extents ...")

    # for city area (urban cluster) by combining contiguous pixels and find largest area in AOI
    # use openCV + gdal

    # to get outer boundary only:
    # 1) first threshold

    thresh8 = rescaleToUnint8(thresh)
    ret, th = cv2.threshold(thresh8,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    # invert values because with threshold city turns up as 0
    th_inv = copy.copy(th)
    th_inv[th_inv==255] = 5
    th_inv[th_inv==0] = 1
    th_inv[th_inv==5] = 0
    th_inv = th_inv.astype('uint8')
    profile['dtype'] = th_inv.dtype
    with rasterio.open(str(volume / '5-thres.tif') , 'w', **profile) as dst:
        dst.write_band(1, th_inv)
    del th

    # polygonize boundaries with gdal

    raster_path = str(volume / '5-thres.tif')
    shapefile_path = str(volume / '6-polygonized.shp')

    doit = polygonize(raster_path, shapefile_path)

    print("done.")

    print("Finding basic urban cluster (largest city area in AOI) ...")

    # find largest polygon in shapefile --->

    shp = gpd.read_file(shapefile_path)

    # find largest poly in multipolygons
    city = max(shp['geometry'], key=lambda a: a.area)

    # export
    city_gdf = gpd.GeoDataFrame(crs=shp.crs, geometry=[city])
    exportString = volume / pathlib.Path('7-bounds.shp')
    city_gdf.to_file(str(exportString))

    print("done.")

    print("Finding built-up area of urban cluster ...")

    # clip HRL/CLC to city area to get urban cluster

    raster = rasterio.open(str(volume / '4-CLC_HRL_AOI_urban.tif'))
    raster_crs = raster.crs
    coords = getFeatures(city_gdf)

    # clip HRL built-up area to city extension
    out_meta = raster.meta.copy()  # Copy the metadata
    epsg_code = int(raster.crs.data['init'][5:])  # Parse EPSG code
    out_img, out_transform = rasterio.mask.mask(raster, coords, crop=True)
    out_meta.update({"driver": "GTiff", "height": out_img.shape[1], "width": out_img.shape[2],
                     "transform": out_transform})
    with rasterio.open(str(volume / pathlib.Path('8-URBAN_CLUSTER_BUA.tif')), "w", **out_meta) as dest:  # replace file with clipped one
        dest.write(out_img)

    print("done.")

if __name__ == '__main__':
    main()