#1. create virtual env using pipenv
```bash
pipenv --python 3
```
#2. install dotnev and azure blob storage
```
pipenv install python-dotenv azure-storage-blob
#pipenv run pip install python-dotenv azure-storage-blob
```
#3. install GDAL [assumes GDAL bin is already installed on the machine]
```
gdalinfo --version

GDALV=$(gdalinfo --version |  awk -F' ' '{print substr($2, 1, length($2)-1)}')

pipenv install gdal==$GDALV
#pipenv run pip install gdal==$GDALV

```