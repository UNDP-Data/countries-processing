import dotenv
from urllib.parse import urlparse
import os
from azure.storage.blob.aio import ContainerClient
from osgeo import gdal, gdalconst, ogr, osr
import logging
import asyncio
import json
import sys

from concurrent.futures import ThreadPoolExecutor, as_completed


def get_container_client(sas_url=None):
    assert sas_url is not None, f'sas_url is required to upload/download data from AZ blob container'
    try:
        return ContainerClient.from_container_url(sas_url)
    except Exception as e:
        logger.error(f'failed to create an azure.storage.blob.ContainerClient object from {sas_url}')
        raise


def read_countries(path):
    with open(path) as f:
        d = json.load(f)
        countries = []
        for g, gc in d.items():
            countries += gc
    return countries


def compute_layer(signed_blob_path=None, lid=None, clist=None, countries_geojson_path=None):
    logger.debug(f'computing countries for layer {lid}')
    ds = ogr.Open(signed_blob_path)
    layer = ds.GetLayer()
    countries_ds = ogr.Open(countries_geojson_path)
    cl = countries_ds.GetLayer()
    r = [lid]
    for country_code in clist:
        cl.SetAttributeFilter(f'ISO3CD = "{country_code}"')
        for feat in cl:
            geom = feat.GetGeometryRef()
            minX, maxX, minY, maxY = geom.GetEnvelope()
            layer.SetSpatialFilterRect(minX, minY, maxX, maxY)
            # layer.SetSpatialFilter(geom)
            has = True if layer.GetFeatureCount() > 0 else False

            r.append(str(has))
            if cl.GetFeatureCount() > 1:
                break
        cl.SetAttributeFilter(None)
        cl.ResetReading()
        layer.SetSpatialFilter(None)
        layer.ResetReading()
    logger.info(f'finished computing {lid} {len(r)} ')
    return r


async def list_blobs(container_sas_url=None, countries_geojson_path=None, countries_json_path=None, name_prefix=None, n_proc_parallel = 15):
    clist = read_countries(countries_json_path)
    print(len(clist))
    countries_ds = ogr.Open(countries_geojson_path)
    cl = countries_ds.GetLayer()
    cnames = list()
    for i, c in enumerate(clist):
        cl.SetAttributeFilter(f'ISO3CD = "{c}"')
        if cl.GetFeatureCount() > 0:
            cc = cl.GetNextFeature().GetField('ROMNAM')
            cnames.append(cc)

    cl.SetAttributeFilter(None)
    cl.ResetReading()
    m = 'metadata.json'
    failed = dict()
    rfailed = list()
    layers = dict()
    with open('sids_country_data.csv', 'w') as fp:
        with ThreadPoolExecutor(max_workers=n_proc_parallel) as executor:
            fp.write(f'{",".join(["AGGREGATION", "LAYERID"] + cnames)}\n')

            async with ContainerClient.from_container_url(container_sas_url) as container:
                blobs_list = container.list_blobs(name_starts_with=name_prefix, timeout=300)
                parsed = urlparse(container.url)

                async for blob in blobs_list:
                    if blob.name.endswith(m):
                        path, metafname = os.path.split(blob.name)
                        logger.info(f'found layer {blob.name}')
                        sunit, lid = path.split('_')
                        blob_full_path = os.path.join(f'{parsed.scheme}://{parsed.netloc}{parsed.path}', path,
                                                      '0/0/0.pbf')
                        signed_blob_path = f'MVT:{blob_full_path}{container._query_str}'
                        layers[lid] = signed_blob_path
                        if len(layers) == n_proc_parallel:
                            futures = {}
                            logger.info(f'processing {n_proc_parallel} files ')
                            for u, v in layers.items():
                                kwargs = dict(signed_blob_path=v, lid=u, clist=clist,
                                              countries_geojson_path=countries_geojson_path)
                                futures[executor.submit(compute_layer, **kwargs)] = lid
                            for future in as_completed(futures):
                                lid = futures[future]
                                # retrieve the result
                                try:
                                    result = future.result(timeout=5)
                                    result.insert(0, sunit)
                                    l = ','.join(result)
                                    fp.write(f'{l}\n')
                                    fp.flush()
                                except Exception as e:
                                    logger.error(f'{lid} failed with {e}')
                                    failed[lid] = layers[lid], e

                            layers = dict()
            if layers:
                futures = {}
                logger.info(f'processing {n_proc_parallel} files ')
                for u, v in layers.items():
                    kwargs = dict(signed_blob_path=v, lid=u, clist=clist, countries_geojson_path=countries_geojson_path)
                    futures[executor.submit(compute_layer, **kwargs)] = lid
                for future in as_completed(futures):
                    lid = futures[future]
                    # retrieve the result
                    try:
                        result = future.result(timeout=5)

                        l = ','.join(result)
                        fp.write(f'{l}\n')
                        fp.flush()
                    except Exception as e:
                        logger.error(f'{lid} failed with {e}')
                        failed[lid] = layers[lid], e

                layers = dict()
            if failed:
                futures = {}
                logger.info(f'processing {n_proc_parallel} files ')
                for lid, v in failed.items():
                    url, err = v
                    kwargs = dict(signed_blob_path=url, lid=lid, clist=clist,
                                  countries_geojson_path=countries_geojson_path)
                    futures[executor.submit(compute_layer, **kwargs)] = lid
                for future in as_completed(futures):
                    lid = futures[future]
                    # retrieve the result
                    try:
                        result = future.result(timeout=5)
                        l = ','.join(result)
                        fp.write(f'{l}\n')
                        fp.flush()
                    except Exception as e:
                        logger.error(f'{lid} failed with {e}')
                        rfailed.append(lid, failed[lid])

    print(rfailed)


if __name__ == '__main__':
    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    sas_url = dotenv.get_key('.env', 'SIDS_DATA_CONTAINER')
    parsed = urlparse(sas_url)
    # AZURE_SAS and AZURE_STORAGE_SAS_TOKEN
    azure_storage_account = parsed.netloc.split('.')[0]
    azure_sas_token = parsed.query

    os.environ['AZURE_STORAGE_ACCOUNT'] = azure_storage_account
    os.environ['AZURE_STORAGE_SAS_TOKEN'] = azure_sas_token
    os.environ['AZURE_SAS'] = azure_sas_token
    # GDAL suff
    os.environ['CPL_TMPDIR'] = '/tmp'
    os.environ['GDAL_CACHEMAX'] = '1000'
    os.environ['VSI_CACHE'] = 'TRUE'
    os.environ['VSI_CACHE_SIZE'] = '5000000'  # 5 MB (per file-handle)
    os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'TRUE'
    os.environ['GDAL_HTTP_MERGE_CONSECUTIVE_RANGES'] = 'YES'
    os.environ['GDAL_HTTP_MULTIPLEX'] = 'YES'
    os.environ['GDAL_HTTP_VERSION'] = '2'
    os.environ['GDAL_HTTP_TIMEOUT'] = '3600'  # secs
    #
    os.environ['GDAL_HTTP_UNSAFESSL'] = 'YES'
    azlogger = logging.getLogger('azure.core.pipeline.policies.http_logging_policy')
    azlogger.setLevel(logging.WARNING)
    countries_geojson = 'uncountries3857.gpkg'
    countries_json = 'sidsCodes.json'
    name_prefix = sys.argv[1]
    n_proc_parallel = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    asyncio.run(list_blobs(container_sas_url=sas_url,
                           countries_geojson_path=countries_geojson,
                           countries_json_path=countries_json,
                           name_prefix=name_prefix,
                           n_proc_parallel=n_proc_parallel))