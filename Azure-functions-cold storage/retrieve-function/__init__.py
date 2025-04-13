# retrieval_function/__init__.py

import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

STORAGE_ACCOUNT_URL = "https://<your-storage-account>.blob.core.windows.net"
BLOB_CONTAINER = "<your-blob-container-name>"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Retrieval function triggered.")

    blob_path = req.params.get("path")  # e.g., "archive/2025-01-01/123.json"
    if not blob_path:
        return func.HttpResponse("Missing 'path' parameter", status_code=400)

    try:
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(account_url=STORAGE_ACCOUNT_URL, credential=credential)
        container_client = blob_service_client.get_container_client(BLOB_CONTAINER)
        blob_client = container_client.get_blob_client(blob_path)

        blob_data = blob_client.download_blob().readall()
        return func.HttpResponse(blob_data, mimetype="application/json", status_code=200)

    except Exception as e:
        logging.error(f"Retrieval failed: {e}")
        return func.HttpResponse("Failed to retrieve blob", status_code=500)
