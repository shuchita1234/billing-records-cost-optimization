import datetime
import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
import os
import json

def main(mytimer: func.TimerRequest) -> None:
    logging.info('Archival function started')

    cosmos_url = os.getenv("COSMOS_URL")
    cosmos_db_name = os.getenv("COSMOS_DB")
    cosmos_container_name = os.getenv("COSMOS_CONTAINER")
    blob_url = os.getenv("BLOB_ACCOUNT_URL")
    blob_container_name = os.getenv("BLOB_CONTAINER_NAME")

    credential = DefaultAzureCredential()
    
    # Cosmos DB client
    cosmos_client = CosmosClient(cosmos_url, credential=credential)
    container = cosmos_client.get_database_client(cosmos_db_name).get_container_client(cosmos_container_name)

    # Blob client
    blob_service_client = BlobServiceClient(account_url=blob_url, credential=credential)
    blob_container = blob_service_client.get_container_client(blob_container_name)

    threshold_date = datetime.datetime.utcnow() - datetime.timedelta(days=90)
    query = f"SELECT * FROM c WHERE c._ts < {int(threshold_date.timestamp())}"

    for doc in container.query_items(query=query, enable_cross_partition_query=True):
        doc_id = doc['id']
        blob_name = f"{doc_id}.json"
        blob_container.upload_blob(blob_name, data=json.dumps(doc), overwrite=True)
        container.delete_item(doc_id, partition_key=doc['partitionKey'])

    logging.info('Archival function completed.')
