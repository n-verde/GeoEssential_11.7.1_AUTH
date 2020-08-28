# ============ HRL IMPERVIOUSNESS PROCESSING =================
# Natalia Verde, AUTh, August 2020

# script for 11.7.1 indicator

# This script processes the HRL 2015 imperviousness layer

# References:


# ============== IMPORTS =============================================
import pathlib
import requests

import ogr, osr, gdal
import rasterio.mask
import geopandas as gpd

# ================= FUNCTIONS =========================================
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
    # set CLC file name
    CLC_fileName = 'CLC2018_1,2,3,10,11.tif'  # made by NV. Only contains urban classes (1,2,3,10,11)

    # ================= MAIN PROGRAM ======================================

    volume = pathlib.Path(directory)
    shp_file_path = volume / pathlib.Path(shpName)

    # download the CLC edited image
    url = 'https://github.com/n-verde/GeoEssential_11.7.1_AUTH/raw/master/CLC2018_1%2C2%2C3%2C10%2C11.tif'
    r = requests.get(url)
    with open(str(volume / pathlib.Path(CLC_fileName)), 'wb') as f:
        f.write(r.content)
    clc_path = pathlib.Path(CLC_fileName)

    # ---------- CLC ----------
    print('Check if CLC intersects with AOI ...')

    # make sure AOI shapefile intersects CLC layer
    # create empty list to save intersecting rasters
    intersectingRasters = []

    item = clc_path
    raster = gdal.Open(str(item))

    # Get raster geometry
    transform = raster.GetGeoTransform()
    pixelWidth = transform[1]
    pixelHeight = transform[5]
    cols = raster.RasterXSize
    rows = raster.RasterYSize

    # create geometry out of raster bounds
    xLeft = transform[0]
    yTop = transform[3]
    xRight = xLeft + cols * pixelWidth
    yBottom = yTop+rows*pixelHeight
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(xLeft, yTop)
    ring.AddPoint(xLeft, yBottom)
    ring.AddPoint(xRight, yBottom)
    ring.AddPoint(xRight, yTop)
    ring.AddPoint(xLeft, yTop)
    rasterGeometry = ogr.Geometry(ogr.wkbPolygon)
    rasterGeometry.AddGeometry(ring)

    # read shapefile & get geometry & CRS
    vector = ogr.Open(str(shp_file_path))
    layer = vector.GetLayer()
    feature = layer.GetFeature(0)
    sourceprj = layer.GetSpatialRef()

    # get raster CRS & set crs transformation (to transform vector to raster crs)
    targetprj = osr.SpatialReference(wkt=raster.GetProjection())
    transform = osr.CoordinateTransformation(sourceprj, targetprj)

    # transform vector crs
    transformedVect = feature.GetGeometryRef()
    transformedVect.Transform(transform)

    # test raster for intersection with vector and save path
    if (rasterGeometry.Intersects(transformedVect)):
        print("AOI intersects with CLC ...")
        intersectingRasters.append(str(item))
    else:
        print("ERROR - AOI does not intersect with Corine Land Cover!")

    print("Clipping CLC to AOI...")

    # clip CLC to AOI
    if len(intersectingRasters)>0:
        for i in range(len(intersectingRasters)):  # loop through items in dir
            rasterPath = intersectingRasters[i]
            raster = rasterio.open(rasterPath)
            raster_crs = raster.crs

            # open shapefile with geopandas
            shapefile = gpd.read_file(str(shp_file_path))
            shapefile_crs = shapefile.crs

            # reproject to raster crs
            shapefile_reproj = shapefile.to_crs(epsg=str(raster_crs['init'])[5:])

            # get the geometry coordinates
            coords = getFeatures(shapefile_reproj)

            # clip CLC
            out_meta = raster.meta.copy()  # Copy the metadata
            epsg_code = int(raster.crs.data['init'][5:])  # Parse EPSG code
            out_img, out_transform = rasterio.mask.mask(raster, coords, crop=True)
            out_meta.update({"driver": "GTiff", "height": out_img.shape[1], "width": out_img.shape[2],
                             "transform": out_transform})
            with rasterio.open(str(volume / '2-CLC_AOI.tif'), "w", **out_meta) as dest:  # replace file with clipped one
                dest.write(out_img)

    print("done.")

if __name__ == '__main__':
    main()