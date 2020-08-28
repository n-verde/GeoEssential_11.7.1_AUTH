# ============ HRL IMPERVIOUSNESS PROCESSING =================
# Natalia Verde, AUTh, August 2020, nverde@topo.auth.gr
# Asterios Tselepis, AUTh, astselepis@topo.auth.gr

# script for 11.7.1 indicator

# This script downloads the HRL 2018 imperviousness layer from a WMS layer

# References:


# ============== IMPORTS =============================================
import pathlib
import os, urllib, ssl
import warnings

import geopandas as gpd

def main():

    # ================= SETTINGS =========================================
    # specify directory (volume conected via docker)
    directory = ''
    # specify AOI in the form of a shapefile
    shpName = 'aoi.shp'

    # ================= MAIN PROGRAM ======================================
    volume = pathlib.Path(directory)
    shp_file_path = volume / pathlib.Path(shpName)

    # open shapefile with geopandas
    shapefile = gpd.read_file(str(shp_file_path))
    # transform to EPSG:4326 CRS because that's what OSM uses
    shapefile_transformed = shapefile.to_crs(epsg=3035)

    # get the bounding box in EPSG:3035 (for meters)
    bboxArray = shapefile_transformed.total_bounds

    # create area string from bounding box to pass in WMS query
    # Left, bottom, right, top
    boundingBox = (bboxArray[0],bboxArray[1],bboxArray[2],bboxArray[3])

    ########################################

    # download from ArcGIS rest services WMS

    # https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLandPublic/HRL_ImperviousnessDensity_2018/ImageServer
    # https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer


    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
        getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context

    # ArcGIS Configuration parameteres (settings)
    ArcGISserver = {"url": "https://image.discomap.eea.europa.eu",  # Image server
                    "bboxSR": 3035,  # bbox CRS
                    "imageSR": 3035,  # exported image CRS
                    "Imperviousness2018": "GioLandPublic/HRL_ImperviousnessDensity_2018/ImageServer"
                    }

    def get_shape_from_rest(xmin, ymin, xmax, ymax, pixelSize, filename, service_name):

        # ARCGIS REST service has a limit of 4000 pixels. If pixelSize requires more than 4000 pixels, lower the resolution
        width = round((xmax-xmin)/pixelSize)
        height = round((ymax-ymin)/pixelSize)
        if ((width > 4000) or (height > 4000)):
            pixelSize = 20  # try for 20m pixel size
            width = round((xmax - xmin) / pixelSize)
            height = round((ymax - ymin) / pixelSize)
            print("Changed pixel size from 10m to 20m because of WMS request size limitation ...")
            if ((width > 4000) or (height > 4000)):
                pixelSize = 30  # try for 30m pixel size
                width = round((xmax - xmin) / pixelSize)
                height = round((ymax - ymin) / pixelSize)
                print("Changed pixel size from 10m to 30m because of WMS request size limitation ...")
                if ((width > 4000) or (height > 4000)):
                    # UN instructions require pixel size <= 30m (Landsat imagery equivalent)
                    print("ERROR: Area is too large for WMS request. Choose a smaller area.")
                    return

        # Parameters
        ArcGIS_server_url = ArcGISserver['url']
        Servicename = ArcGISserver[service_name]
        bboxSR = ArcGISserver['bboxSR']
        widthpixels = width
        heightpixels = height
        imageSR = ArcGISserver['imageSR']

        # secured url
        url = ArcGIS_server_url + '/arcgis/rest/services/' + Servicename + '/exportImage?'

        params = "bbox=" + str(xmin) + "%2C" + str(ymin) + "%2C" + str(xmax) + "%2C" + str(ymax) + "&bboxSR=" + str(bboxSR) \
                 + "&size=" + str(widthpixels) + "%2C" + str(heightpixels) + "&imageSR=" + str(imageSR) + \
                 "&time=&format=tiff&pixelType=UNKNOWN&noData=&noDataInterpretation=esriNoDataMatchAny&interpolation=+RSP_BilinearInterpolation&compression=&compressionQuality=&bandIds=&mosaicRule=&renderingRule=&f=image"

        response = urllib.request.urlopen(url+params)

        #Check service status
        if response.status != 200:
            warnings.warn("Server is not responding")
            # return status 0 - server error
            status = 0
            return (status)

        ResponseObj = response.read()

        out = open(str(directory / pathlib.Path(filename + '.tif')), "wb")
        out.write(ResponseObj)
        out.close()

    print("Getting HRL Imperviousness 2018 from WMS for ΑΟΙ ...")

    # run the function to get Imperviousness density 2018 for the AOI
    # TAKE 20m SPATIAL RESOLUTION INSTEAD OF 10m BECAUSE OTHERWISE WMS CRASHES FOR LARGE AREAS (4000 PIXEL LIMIT)
    get_shape_from_rest(bboxArray[0], bboxArray[1], bboxArray[2], bboxArray[3], 10, "1-HRL_AOI", "Imperviousness2018")

    print("done.")


if __name__ == '__main__':
    main()