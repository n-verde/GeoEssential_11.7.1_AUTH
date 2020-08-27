#!/usr/bin/env bash

unzip aoi.zip

# ls -l

python3 0_Download_data.py

python3 1_CLC_Clip.py

# ls -l

python3 2_City_Area.py

python3 3_OSM_Layers.py

python3 4_Index_calculation.py
