import os
import zipfile
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
RAW_CONTAINER = "raw"


def extract_zip(zip_path: str, extract_to: str) -> None:
    """Extract a zip file to a local directory."""
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_to)
    print(f"Extracted to {extract_to}")


def upload_folder_to_blob(local_folder: str, blob_prefix: str) -> None:
    """
    Upload all files in a local folder to Azure Blob Storage
    under the raw container with the given prefix.
    """
    client = BlobServiceClient.from_connection_string(CONN_STR)
    container = client.get_container_client(RAW_CONTAINER)

    files = list(Path(local_folder).rglob("*"))
    files = [f for f in files if f.is_file()]

    print(f"Uploading {len(files)} files to blob/{blob_prefix}/...")
    for file_path in tqdm(files):
        # Preserve folder structure inside blob
        relative = file_path.relative_to(local_folder)
        blob_name = f"{blob_prefix}/{relative}"

        with open(file_path, "rb") as data:
            container.upload_blob(name=blob_name, data=data, overwrite=True)

    print("Upload complete.")


def version_snapshot(blob_prefix: str, version_tag: str) -> None:
    """
    Write a small manifest file to blob storage recording
    what version of data was uploaded and when.
    """
    import datetime
    client = BlobServiceClient.from_connection_string(CONN_STR)
    container = client.get_container_client(RAW_CONTAINER)

    manifest = (
        f"version: {version_tag}\n"
        f"uploaded_at: {datetime.datetime.utcnow().isoformat()}\n"
        f"prefix: {blob_prefix}\n"
        f"source: https://github.com/mdeff/fma\n"
    )
    container.upload_blob(
        name=f"{blob_prefix}/_manifest_{version_tag}.txt",
        data=manifest.encode(),
        overwrite=True
    )
    print(f"Manifest written for version {version_tag}")


if __name__ == "__main__":
    # Step 1: Extract zips locally first
    extract_zip("downloads/fma_small.zip", "data/raw/fma_small")
    extract_zip("downloads/fma_metadata.zip", "data/raw/fma_metadata")

    # Step 2: Upload to Azure
    upload_folder_to_blob("data/raw/fma_metadata", "fma_metadata")
    # Audio is large — upload selectively or just metadata for now
    upload_folder_to_blob("data/raw/fma_small", "fma_small")

    # Step 3: Version snapshot
    version_snapshot("fma_metadata", "v1.0")
    version_snapshot("fma_small", "v1.0")