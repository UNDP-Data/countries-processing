
eval $(cat .env | sed 's/^/export /')
envsubst < manifest.tpl.yml > manifest.yml
cat manifest.yml

#docker container prune -f && docker image prune -af && docker compose build
#docker push undpgeohub.azurecr.io/sids-data-pipeline

az container delete --resource-group undpdpbppssdganalyticsgeo --name cproc-$PREFIX --yes
az container create --resource-group undpdpbppssdganalyticsgeo --file manifest.yml
