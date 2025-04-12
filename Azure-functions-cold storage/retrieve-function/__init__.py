import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    doc_id = req.params.get('doc_id')
    if not doc_id:
        return func.HttpResponse("Missing 'doc_id' query parameter.", status_code=400)

    try:
        blob_service_client = BlobServiceClient(
            account_url=os.getenv("BLOB_ACCOUNT_URL"),
            credential=DefaultAzureCredential()
        )

        blob_client = blob_service_client.get_blob_client(
            container=os.getenv("BLOB_CONTAINER_NAME"),
            blob=f"{doc_id}.json"
        )

        if not blob_client.exists():
            return func.HttpResponse("Document not found.", status_code=404)

        data = blob_client.download_blob().readall()
        return func.HttpResponse(data, mimetype="application/json")

    except Exception as e:
        return func.HttpResponse(f"Error retrieving document: {str(e)}", status_code=500)
