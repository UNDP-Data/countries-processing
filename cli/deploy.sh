for prefix in 'admin0' 'admin1' 'admin2' 'hex-10km' 'hex-5km' 'hex-1km' 'hex-10km-ocean' 'grid-10km' 'grid-5km' 'grid-1km' 'grid-10km-ocean'; do
  echo 'publishing' $prefix
  export PREFIX=$prefix
  eval $(cat ./.env | sed 's/^/export /')
  envsubst < manifest.tpl.yml > manifest.yml
  az container delete --resource-group undpdpbppssdganalyticsgeo --name cproc-$PREFIX --yes
  az container create --resource-group undpdpbppssdganalyticsgeo --file manifest.yml

  rm manifest.yml

done


#docker container prune -f && docker image prune -af && docker compose build
#docker push undpgeohub.azurecr.io/sids-data-pipeline


