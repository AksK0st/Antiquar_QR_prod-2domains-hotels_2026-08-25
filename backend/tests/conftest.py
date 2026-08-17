import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# config.py instantiates Settings at import time, so provide deterministic test values
# before test modules import application modules.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("POSTGRES_DB", "antiquar_test")
os.environ.setdefault("POSTGRES_USER", "antiquar_test")
os.environ.setdefault("POSTGRES_PASSWORD", "test-database-password")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "test-app")
os.environ.setdefault("MINIO_SECRET_KEY", "test-storage-password")
os.environ.setdefault("MINIO_BUCKET", "antiquar-test")
os.environ.setdefault("PUBLIC_BASE_URL", "http://localhost:8080")
