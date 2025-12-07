import mimetypes

import boto3
from botocore.config import Config
from flask import current_app
from flask_login import current_user


def get_s3_client():
    s3_config = Config(
        retries={"max_attempts": 3, "mode": "standard"},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
        s3={"addressing_style": "path"},
        signature_version="s3v4",
    )

    return boto3.client(
        "s3",
        endpoint_url=current_app.config["S3_ENDPOINT_URL"],
        aws_access_key_id=current_app.config["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["S3_SECRET_KEY"],
        region_name="us-east-1",
        config=s3_config,
    )


def generate_presigned_url(key, expiration=3600):
    s3_client = get_s3_client()
    bucket = current_app.config["S3_BUCKET_NAME"]

    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiration,
    )

    return presigned_url


def upload_to_s3(file, filename, content_type=None):
    s3 = get_s3_client()
    bucket = current_app.config["S3_BUCKET_NAME"]

    if content_type is None:
        guessed, _ = mimetypes.guess_type(filename)
        content_type = guessed or "application/octet-stream"

    file_content = file.read()
    file.seek(0)

    key = f"notes/{current_user.id}/{filename}"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_content,
        ContentType=content_type,
    )

    return key
