import dotenv
import asyncio
import logging
from urllib.parse import urlparse
import os
from azure.storage.blob.aio import ContainerClient
#sids_sas_url = dotenv.get_key('./cli/.env', 'SIDS_CONTAINER')
sids_sas_url = dotenv.get_key('.env', 'SIDS_CONTAINER')

logger = logging.getLogger()



async def upload_file(container_client_instance=None, src=None, dst_blob_name=None,  overwrite=False, max_concurrency=8):

    """
    Async upload a local file to Azure container.
    Do not use directly. This function is meant to be used inside a loop where many files
    are uploaded asynchronously
    :param container_client_instance: instance of azure.storage.blob.aio.ContainerClient
    :param src: str, the path of the file
    :param dst_blob_name: str, the name of the uploaded blob. The file content will be stored in AZ under this name
    :param overwrite: bool, default=False, flag to force uploading an existing file
    :param max_concurrency, default = 8, maximum number of parallel connections to use when the blob size exceeds 64MB

    :return: None
    """

    parsed_src_url = urlparse(src)

    if not dst_blob_name:
        _, dst_blob_name = os.path.split(parsed_src_url.path)

    assert dst_blob_name not in [None, '', ' '], f'Invalid destination blob name {dst_blob_name}'


    with open(src, 'rb') as data:
        blob_client = await container_client_instance.upload_blob(name=dst_blob_name, data=data,
                                                                  blob_type='BlockBlob', overwrite=overwrite,
                                                                  max_concurrency=max_concurrency)
        logger.debug(f'{src} was uploaded as {dst_blob_name}')
        return blob_client, src


if __name__ == '__main__':
    async def azup(fname=None, container_sas_url=None):
        async with ContainerClient.from_container_url(container_sas_url) as container:
            print(f'connected')
            await upload_file(
                container_client_instance=container,
                src=fname,
                dst_blob_name=f'cntr/{fname}',
                overwrite=True
            )

    fname='country_data.csv'
    with open(fname, 'w') as o:
        o.write('HAHA')
    asyncio.run(azup(
        fname=fname,
        container_sas_url=sids_sas_url
    ))