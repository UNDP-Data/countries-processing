FROM osgeo/gdal:ubuntu-small-3.6.0 as gdal

RUN apt-get update \
    && apt-get -y install python3-pip

RUN apt-get -y install python3-pip
RUN python3 -m pip install -U pip
RUN python3 -m pip install azure-storage-blob aiohttp
RUN mkdir /opt/sidscountriesproc
WORKDIR /opt/sidscountriesproc

COPY . .

ENTRYPOINT ["python3", "check_countries.py"]

CMD ["admin0"]

