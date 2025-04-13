# archival_function/__init__.py

import datetime
import json
import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.cosmos import CosmosClient, PartitionKey

# Constants
COSMOS_DB_URL = "<your-cosmos-db-account-uri>"
DATABASE_NAME = "<your-db-name>"
CONTAINER_NAME = "<your-container-name>"
BLOB_CONTAINER = "<your-blob-container-name>"
STORAGE_ACCOUNT_URL = "https://<your-storage-account>.blob.core.windows.net"

def main(mytimer: func.TimerRequest) -> None:
    logging.info("Archival function started.")

    credential = DefaultAzureCredential()

    # Cosmos DB client
    cosmos_client = CosmosClient(COSMOS_DB_URL, credential)
    db = cosmos_client.get_database_client(DATABASE_NAME)
    container = db.get_container_client(CONTAINER_NAME)

    # Blob storage client
    blob_service_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)
    blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER)

    # Cutoff date: 3 months ago
    cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=90)).isoformat()

    query = f"SELECT * FROM c WHERE c.createdAt < '{cutoff_date}'"
    old_items = list(container.query_items(query=query, enable_cross_partition_query=True))

    for item in old_items:
        item_id = item.get('id')
        partition_key = item.get('partitionKey') or item_id  # adjust if needed
        blob_name = f"archive/{item['createdAt'][:10]}/{item_id}.json"

        try:
            # Upload to Blob Storage
            blob_data = json.dumps(item).encode('utf-8')
            blob_client = blob_container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                blob_data,
                overwrite=True,
                content_settings=ContentSettings(content_type='application/json'),
                standard_blob_tier="Cool"
            )

            # Safe delete from Cosmos DB
            container.delete_item(item=item_id, partition_key=partition_key)
            logging.info(f"Archived and deleted item {item_id}")
        except Exception as e:
            logging.error(f"Failed for item {item_id}: {e}")
