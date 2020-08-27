#!/usr/bin/env bash

unzip aoi.zip

ls -l

python3 0_Download_data.py

ls -l

python3 1_CLC_Clip.py

ls -l

python3 2_City_Area.py

ls -l

python3 3_OSM_Layers.py

ls -l

python3 4_Index_calculation.py

ls -l

