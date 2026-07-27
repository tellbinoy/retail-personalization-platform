from google.cloud import storage
from src.config import PROJECT_ID

def upload_file(local_file, bucket_name, blob_name):
    try:
        print("Entry - upload_file")
        print(f"local_file {local_file}")
        print(f"bucket_name {bucket_name}")
        print(f"blob_name {blob_name}")
        client = storage.Client(project=PROJECT_ID)
    except Exception as e:
        raise Exception(
            "GCS Storage Client authentication failed. \n"
            "Go to terminal and then run the below line\n\n"
            "gcloud auth application-default login\n\n"
        ) from e
    bucket = client.bucket(bucket_name) #which bucket to put (root like)
    blob = bucket.blob(blob_name) #folder_path/file_name.extension
    blob.upload_from_filename(local_file)
    print("Exit - upload_file")
