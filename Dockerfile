# Natalia Verde, AUTh, August 2020

#### Use latest Ubuntu
FROM ubuntu:eoan

LABEL maintainer="nverde@topo.auth.gr"

# Update base container install
RUN apt-get update
RUN apt-get upgrade -y

RUN apt-get update && apt-get install -y --no-install-recommends apt-utils

# install pip3
RUN apt-get install -y python3-pip

# install numpy BEFORE GDAL (otherwise raster array won't work)
RUN pip3 install numpy==1.19.1

# Install GDAL dependencies
RUN apt-get install -y libgdal-dev locales

# Ensure locales configured correctly
RUN locale-gen en_US.UTF-8
ENV LC_ALL='en_US.utf8'

# Set python aliases for python3
RUN echo 'alias python=python3' >> ~/.bashrc
RUN echo 'alias pip=pip3' >> ~/.bashrc

# Update C env vars so compiler can find gdal
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# This will install latest version of GDAL
RUN pip3 install GDAL==2.4.2

# install wget
RUN apt-get install -y \
	wget

# Update
RUN pip3 install --upgrade pip

# Install other libs

RUN apt-get update && apt-get install -y \
    unzip

RUN pip3 install pathlib==1.0.1 \
				pandas==0.25 \
				geopandas==0.8.1 \
				matplotlib==3.0.2 \
				Pillow==5.4.1 \
				Glymur==0.8.16 \
				satpy==0.12.0 \
				pyorbital==1.5.0 \
				rasterio==1.0.18 \
				setuptools==41.2 \
				utm-zone==1.0.1 \
				opencv-contrib-python-headless==4.4.0.42 \
				libtiff==0.4.2 \
				requests==2.7.0 \
				geojson==2.5.0

RUN mkdir volume

# To save your container as a docker image, open a new terminal and:
# 1. build the dockerfile to an image with tag "nverde/11.7.1:0.1"
# 2. push the image to dockerhub: by typing in the cmd "docker push nverde/11.7.1:0.1"

# works!