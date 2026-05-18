"""S3/MinIO storage para artefatos capturados.

A configuração é totalmente opcional: se ``S3_BUCKET`` não estiver setado, o
worker continua persistindo o HTML em ``cases.raw_html``. Quando configurado,
os HTMLs vão para o bucket e ``cases.artifact_key`` referencia o objeto.
"""

from __future__ import annotations

from functools import lru_cache

import boto3
from botocore.client import Config
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    endpoint: str | None = Field(default=None, validation_alias="S3_ENDPOINT")
    region: str = Field(default="us-east-1", validation_alias="S3_REGION")
    bucket: str | None = Field(default=None, validation_alias="S3_BUCKET")
    access_key: str | None = Field(default=None, validation_alias="S3_ACCESS_KEY")
    secret_key: str | None = Field(default=None, validation_alias="S3_SECRET_KEY")


class S3Storage:
    def __init__(self, bucket: str, client) -> None:  # type: ignore[no-untyped-def]
        self.bucket = bucket
        self.client = client

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
        )

    def get_bytes(self, key: str) -> bytes:
        resp = self.client.get_object(Bucket=self.bucket, Key=key)
        body = resp["Body"]
        try:
            return body.read()
        finally:
            body.close()

    def list_keys(self, prefix: str) -> list[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        out: list[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []) or []:
                out.append(obj["Key"])
        return out

    def delete_key(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


@lru_cache
def get_storage() -> S3Storage | None:
    s = StorageSettings()
    if not s.bucket:
        return None
    client = boto3.client(
        "s3",
        endpoint_url=s.endpoint,
        region_name=s.region,
        aws_access_key_id=s.access_key,
        aws_secret_access_key=s.secret_key,
        config=Config(signature_version="s3v4"),
    )
    return S3Storage(bucket=s.bucket, client=client)
