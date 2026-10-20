import argparse
from pathlib import Path
from urllib.parse import urlparse

from google.cloud import storage
from google.api_core.exceptions import Conflict, NotFound

from pipeline_config import load_pipeline_config


def _parse_gs_uri(bucket_uri: str) -> str:
    parsed = urlparse(bucket_uri)
    if parsed.scheme != "gs" or not parsed.netloc or parsed.path.strip("/"):
        raise ValueError("gcs.bucket_uri must be a bucket-only URI such as gs://bucket-name")
    return parsed.netloc


def ensure_bucket(client: storage.Client, bucket_name: str, location: str) -> storage.Bucket:
    """Return the bucket, creating it in the configured region when absent."""
    bucket = client.bucket(bucket_name)
    try:
        bucket.reload()
        return bucket
    except NotFound:
        bucket.location = location
        try:
            return client.create_bucket(bucket, location=location)
        except Conflict:
            bucket.reload()
            return bucket


def upload_policy_to_gcs(
    local_path: str | Path,
    config_path: str | Path = "pipeline_config.yaml",
) -> str:
    """Upload one local policy PDF to the configured GCS object."""
    config = load_pipeline_config(config_path)
    source = Path(local_path)
    if not source.is_file():
        raise FileNotFoundError(f"Policy file not found: {source}")
    if source.suffix.lower() != ".pdf":
        raise ValueError("The policy upload pipeline accepts PDF files only")

    bucket_name = _parse_gs_uri(config.gcs.bucket_uri)
    client = storage.Client(project=config.project_id)
    bucket = ensure_bucket(client, bucket_name, config.region)
    blob = bucket.blob(config.gcs.object_name)
    upload_kwargs = {"content_type": "application/pdf"}
    if not config.gcs.overwrite_existing:
        upload_kwargs["if_generation_match"] = 0
    blob.upload_from_filename(str(source), **upload_kwargs)
    return f"gs://{bucket_name}/{config.gcs.object_name}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a loan policy PDF to GCS.")
    parser.add_argument("local_path", type=Path)
    parser.add_argument("--config", type=Path, default=Path("pipeline_config.yaml"))
    args = parser.parse_args()
    uri = upload_policy_to_gcs(args.local_path, args.config)
    print(f"Uploaded policy document: {uri}")


if __name__ == "__main__":
    main()