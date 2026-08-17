from minio import Minio
from urllib3 import PoolManager, Retry, Timeout

from config import settings


MINIO_BUCKET = settings.minio_bucket

_http_client = PoolManager(
    timeout=Timeout(
        connect=settings.minio_connect_timeout_seconds,
        read=settings.minio_read_timeout_seconds,
    ),
    retries=Retry(
        total=2,
        connect=2,
        read=1,
        backoff_factor=0.2,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD", "PUT", "DELETE"}),
    ),
)

minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key.get_secret_value(),
    secret_key=settings.minio_secret_key.get_secret_value(),
    secure=settings.minio_secure,
    http_client=_http_client,
)
