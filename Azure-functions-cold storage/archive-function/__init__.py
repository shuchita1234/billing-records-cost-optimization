# archival_function/__init__.py

import datetime
import json
import logging
import time
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.cosmos import CosmosClient

# Constants
COSMOS_DB_URL = "<your-cosmos-db-account-uri>"
DATABASE_NAME = "<your-db-name>"
CONTAINER_NAME = "<your-container-name>"
BLOB_CONTAINER = "<your-blob-container-name>"
STORAGE_ACCOUNT_URL = "https://<your-storage-account>.blob.core.windows.net"
MAX_RETRIES = 5

def main(mytimer: func.TimerRequest) -> None:
    logging.info("Archival function started.")

    credential = DefaultAzureCredential()
    cosmos_client = CosmosClient(COSMOS_DB_URL, credential)
    db = cosmos_client.get_database_client(DATABASE_NAME)
    container = db.get_container_client(CONTAINER_NAME)

    blob_service_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)
    blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER)

    cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=90)).isoformat()

    query = f"SELECT * FROM c WHERE c.createdAt < '{cutoff_date}'"
    old_items = list(container.query_items(query=query, enable_cross_partition_query=True))

    for item in old_items:
        item_id = item.get('id')
        partition_key = item.get('partitionKey') or item_id
        blob_name = f"archive/{item['createdAt'][:10]}/{item_id}.json"
        blob_data = json.dumps(item).encode('utf-8')

        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                blob_client = blob_container_client.get_blob_client(blob_name)
                blob_client.upload_blob(
                    blob_data,
                    overwrite=True,
                    content_settings=ContentSettings(content_type='application/json'),
                    standard_blob_tier="Cool"
                )
                success = True
                logging.info(f"[{item_id}] Upload succeeded on attempt {attempt}")
                break
            except Exception as e:
                logging.warning(f"[{item_id}] Upload attempt {attempt} failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

        if success:
            try:
                container.delete_item(item=item_id, partition_key=partition_key)
                logging.info(f"[{item_id}] Deleted from Cosmos DB")
            except Exception as e:
                logging.error(f"[{item_id}] Upload succeeded but deletion failed: {e}")
        else:
            logging.error(f"[{item_id}] Archival failed after {MAX_RETRIES} attempts. Skipping deletion.")
