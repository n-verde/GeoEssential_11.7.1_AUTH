# ============ OSM PROCESSING =================
# Natalia Verde, AUTh, August 2020

# script for 11.7.1 indicator

# This script downloads OSM layers for an AOI and intersects with existing geospatial data

# References:
# https://www.youtube.com/watch?v=WmCLQCohL3k
# https://janakiev.com/blog/openstreetmap-with-python-and-overpass-api/
# http://overpass-turbo.eu/
# https://stackoverflow.com/questions/36774049/merging-a-list-of-polygons-to-multipolygons
# https://stackoverflow.com/questions/34549767/how-to-calculate-the-center-of-the-bounding-box

# ============== IMPORTS =============================================
import pathlib
import requests
import geojson
import geopandas as gpd
import shapely.geometry
import shapely.wkt
from shapely.ops import cascaded_union
import utm_zone
import pyproj
from shapely.ops import transform


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
    shapefile_transformed = shapefile.to_crs(epsg=4326)

    # get the bounding box
    bbox = shapefile_transformed.total_bounds

    # find in which utm zone AOI is (will be used later for buffer)
    shapefile.to_file(str(volume / pathlib.Path(shpName)) + '.geojson', driver='GeoJSON') # export shp as geojson
    geojson_aoi_path = str(volume / pathlib.Path(shpName)) + '.geojson'
    with open(geojson_aoi_path) as f:
        gj = geojson.load(f) # read geojson
    utm_epsg_code = utm_zone.epsg(gj) # find geojson utm epsg code

    # ---------- DO THE QUERY TO GET OPEN AREAS OSM DATA ----------
    # Overpass API uses a custom query language to define queries
    overpass_url = "http://overpass-api.de/api/interpreter"

    # create area string from bounding box to pass in Overpass API
    areaString =  str(bbox[1]) + "," \
                + str(bbox[0]) + "," \
                + str(bbox[3]) + "," \
                + str(bbox[2])

    # create query string
    # search for more tags here: https://taginfo.openstreetmap.org/tags
    # and here: https://wiki.openstreetmap.org/wiki/Map_Features
    queryString = '''
    [out:json];
    (way["natural"="shingle"]({s});
     rel["natural"="shingle"]({s});
     
     way["natural"="sand"]({s});
     rel["natural"="sand"]({s});
     
     way["natural"="beach"]({s});
     rel["natural"="beach"]({s});
     
     way["leisure"="park"]({s});
     rel["leisure"="park"]({s});
     
     way["leisure"="playground"]({s});
     rel["leisure"="playground"]({s});
     
     way["leisure"="garden"]({s});
     rel["leisure"="garden"]({s});
     
     way["leisure"="nature_reserve"]({s});
     rel["leisure"="nature_reserve"]({s});
    
     way["place"="square"]({s});
     rel["place"="square"]({s});
     
     way["landuse"="recreation_ground"]({s});
     rel["landuse"="recreation_ground"]({s});
     
     way["landuse"="cemetery"]({s});
     rel["landuse"="cemetery"]({s});
    );
    out geom;
    '''.format(s=areaString)

    print('Querying for open areas in OSM ...')

    overpass_query = queryString
    response = requests.get(overpass_url,
                            params={'data': overpass_query})
    data = response.json()


    # Collect polygons into list
    polygons = []
    for element in data['elements']:
        if ((element['type'] == 'way') or (element['type'] == 'rel')) :
            lon_list = []
            lat_list = []
            for point in element['geometry']:
                lon = point['lon']
                lat = point['lat']
                lon_list.append(lon)
                lat_list.append(lat)
            if (len(lon_list)<3):
                continue
            else:
                poly_geom = shapely.geometry.Polygon(zip(lon_list, lat_list)) # create polygon geometry
                polygons.append(poly_geom) # add polygon to list

    # POLYGONS ----
    union = cascaded_union(polygons)
    multi_polygon = gpd.GeoDataFrame(crs='epsg:4326', geometry=[union])
    # reproject to UTM
    multi_polygon_utm = multi_polygon.to_crs('epsg:' + str(utm_epsg_code))  # utm epsg code for AOI)
    # export OSM polygons
    exportString = volume / pathlib.Path('9-osm_open_areas.shp')
    multi_polygon_utm.to_file(str(exportString))

    print("done.")

    # ---------- DO THE QUERY TO GET LAS OSM DATA ----------

    queryString = '''
    [out:json];
    (
     way["highway"="primary"]({s});
     rel["highway"="primary"]({s});
     
     way["highway"="secondary"]({s});
     rel["highway"="secondary"]({s});
     
     way["highway"="tertiary"]({s});
     rel["highway"="tertiary"]({s});
     
     way["highway"="unclassified"]({s});
     rel["highway"="unclassified"]({s});
     
     way["highway"="residential"]({s});
     rel["highway"="residential"]({s});
     
     way["highway"="primary_link"]({s});
     rel["highway"="primary_link"]({s});
     
     way["highway"="secondary_link"]({s});
     rel["highway"="secondary_link"]({s});
     
     way["highway"="tertiary_link"]({s});
     rel["highway"="tertiary_link"]({s});
     
     way["highway"="living_street"]({s});
     rel["highway"="living_street"]({s});
     
     way["highway"="service"]({s});
     rel["highway"="service"]({s});
     
     way["highway"="pedestrian"]({s});
     rel["highway"="pedestrian"]({s});
     
     way["highway"="road"]({s});
     rel["highway"="road"]({s});
     
     way["highway"="corridor"]({s});
     rel["highway"="corridor"]({s});
    
     way["highway"="pedestrian"]({s});
     rel["highway"="pedestrian"]({s});
    
     way["highway"="footway"]({s});
     rel["highway"="footway"]({s});
    
     way["highway"="steps"]({s});
     rel["highway"="steps"]({s});
    
     way["highway"="path"]({s});
     rel["highway"="path"]({s});
    
     way["traffic_calming"="island"]({s});
     rel["traffic_calming"="island"]({s});
    
     way["cycleway"="lane"]({s});
     rel["cycleway"="lane"]({s});
    
     way["cycleway"="track"]({s});
     rel["cycleway"="track"]({s});
    );
    out geom;
    '''.format(s=areaString)

    print('Querying for streets in OSM ...')

    overpass_query = queryString
    response = requests.get(overpass_url,
                            params={'data': overpass_query})
    data = response.json()

    print("done.")

    print('Buffering road network in order to find land allocated to streets ...')

    # in order to apply buffer to road network, must reproject to projected CRS
    s = 'epsg:' + str(utm_epsg_code)  # utm epsg code for AOI
    projectToUTM = pyproj.Transformer.from_proj(
        pyproj.Proj('epsg:4326'),  # OSM coordinate system
        pyproj.Proj(s))  # utm coordinate system
    projectToWGS = pyproj.Transformer.from_proj( # reproject to OSM CRS
        pyproj.Proj(s),  # utm coordinate system
        pyproj.Proj('epsg:4326'))  # OSM coordinate system

    # Collect roads into list and buffer to get width
    polygons = []
    for element in data['elements']:
        if ((element['type'] == 'way') or (element['type'] == 'rel')):
            lon_list = []
            lat_list = []
            for point in element['geometry']:
                lon = point['lon']
                lat = point['lat']
                lon_list.append(lon)
                lat_list.append(lat)
            for tag in element['tags']:
                if tag == 'lanes': # for roads which 'lanes' are known, and thus approx. width can be calculated
                    lanes = element['tags']['lanes']
                    width = lanes * 3
                else:  # otherwise, assume roads have one lane
                    width = 3

                line_geom = shapely.geometry.LineString(zip(lon_list, lat_list))

                # in order to apply buffer to road network, must reproject to projected CRS
                line_geom_trans = transform(projectToUTM.transform, line_geom)  # apply projection
                buff = line_geom_trans.buffer(width) # in meters
                buff_trans = transform(projectToWGS.transform, buff)  # apply projection
                polygons.append(buff_trans)  # add polygon to list

    # POLYGONS ----
    union = cascaded_union(polygons)
    multi_polygon = gpd.GeoDataFrame(crs='epsg:4326', geometry=[union])
    multi_polygon_utm = multi_polygon.to_crs('epsg:' + str(utm_epsg_code))  # utm epsg code for AOI)
    # export OSM polygons
    exportString = volume / pathlib.Path('10-osm_roads.shp')
    multi_polygon_utm.to_file(str(exportString))

    print("done.")

if __name__ == '__main__':
    main()