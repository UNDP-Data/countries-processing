#!/bin/bash

echo 'publishing gdal'
eval  $(cat ./.env_gdal | sed 's/^/export /')
envsubst < gdal_tmpl.yml > gdal.yml
az container delete --resource-group undpdpbppssdganalyticsgeo --name gdal --yes
az container create --resource-group undpdpbppssdganalyticsgeo --file gdal.yml
rm gdal.yml