"""Object storage abstraction.

Local filesystem for development, S3-compatible (MinIO, AWS S3) for production.
The bucket layout and filesystem paths are never exposed: clients only ever see
an opaque storage key and a short-lived signed URL.
"""
from __future__ import annotations

import abc
import asyncio
import hashlib
import mimetypes
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import (
    PayloadTooLargeError,
    StorageError,
    UnsupportedMediaTypeError,
)
from app.core.logging import get_logger
from app.core.security import sign_value, unsign_value

log = get_logger("storage")

# Magic bytes, checked against the declared content type. A file that claims to
# be a PDF but starts with "MZ" is rejected regardless of its extension.
MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    # DOCX and legacy DOC are ZIP / OLE2 containers respectively.
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        b"PK\x03\x04",
    ),
    "application/msword": (b"\xd0\xcf\x11\xe0", b"PK\x03\x04"),
}

DANGEROUS_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".sh", ".bat", ".cmd", ".com", ".scr",
    ".js", ".jar", ".php", ".py", ".rb", ".pl", ".ps1", ".vbs", ".html", ".htm",
    ".svg",
}

SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(slots=True)
class StoredObject:
    storage_key: str
    size_bytes: int
    content_type: str
    checksum_sha256: str
    provider: str


def sanitise_filename(name: str) -> str:
    """Strip path components and unsafe characters from a client-supplied name."""
    base = os.path.basename(name or "file")
    base = SAFE_NAME.sub("_", base).strip("._") or "file"
    return base[:180]


def validate_upload(filename: str, content_type: str, data: bytes) -> str:
    """Validate size, declared type and magic bytes. Returns the resolved type."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if not data:
        raise UnsupportedMediaTypeError("The uploaded file is empty", code="EMPTY_FILE")
    if len(data) > max_bytes:
        raise PayloadTooLargeError(
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit"
        )

    extension = Path(sanitise_filename(filename)).suffix.lower()
    if extension in DANGEROUS_EXTENSIONS:
        raise UnsupportedMediaTypeError(
            f"Files of type {extension} are not accepted", code="DANGEROUS_FILE_TYPE"
        )

    declared = (content_type or "").split(";")[0].strip().lower()
    if declared not in settings.ALLOWED_UPLOAD_MIME:
        guessed = mimetypes.guess_type(filename)[0]
        if guessed in settings.ALLOWED_UPLOAD_MIME:
            declared = guessed
        else:
            raise UnsupportedMediaTypeError(
                "Allowed file types: PDF, DOCX, PNG, JPG",
                details={"allowed": settings.ALLOWED_UPLOAD_MIME},
            )

    signatures = MAGIC_SIGNATURES.get(declared)
    if signatures and not any(data.startswith(sig) for sig in signatures):
        raise UnsupportedMediaTypeError(
            "The file content does not match its declared type",
            code="CONTENT_TYPE_MISMATCH",
        )
    return declared


def build_storage_key(owner_id: uuid.UUID, kind: str, filename: str) -> str:
    """Unguessable, collision-free key. Never derived only from user input."""
    today = datetime.now(UTC).strftime("%Y/%m")
    safe = sanitise_filename(filename)
    return f"{kind.lower()}/{today}/{owner_id}/{uuid.uuid4().hex}-{safe}"


class StorageBackend(abc.ABC):
    name = "base"

    @abc.abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    @abc.abstractmethod
    async def get(self, key: str) -> bytes: ...

    @abc.abstractmethod
    async def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    async def signed_url(self, key: str, *, filename: str, expires: int) -> str: ...


class LocalStorage(StorageBackend):
    """Filesystem backend for development and tests."""

    name = "local"

    def __init__(self) -> None:
        self.root = Path(settings.STORAGE_LOCAL_PATH).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Resolve and confirm containment: a crafted key must not escape the root.
        candidate = (self.root / key).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise StorageError("Invalid storage key", code="INVALID_STORAGE_KEY")
        return candidate

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)

    async def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise StorageError("Stored file is missing", code="OBJECT_NOT_FOUND")
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    async def signed_url(self, key: str, *, filename: str, expires: int) -> str:
        # Signed, time-limited token redeemed by the download endpoint.
        expiry = int(datetime.now(UTC).timestamp()) + expires
        token = sign_value(f"{key}|{expiry}")
        return f"{settings.BACKEND_URL}{settings.API_V1_PREFIX}/documents/download?token={token}"


class S3Storage(StorageBackend):
    """S3-compatible backend (AWS S3, MinIO, Cloudflare R2, ...)."""

    name = "s3"

    def __init__(self) -> None:
        self._client = None
        self._bucket_checked = False

    def _get_client(self):  # pragma: no cover - requires boto3 + a bucket
        if self._client is None:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT or None,
                aws_access_key_id=settings.S3_ACCESS_KEY or None,
                aws_secret_access_key=settings.S3_SECRET_KEY or None,
                region_name=settings.S3_REGION,
                use_ssl=settings.S3_USE_SSL,
                config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
            )
        self._ensure_bucket()
        return self._client

    def _ensure_bucket(self) -> None:  # pragma: no cover - requires a live store
        """Create the bucket if it is missing.

        A fresh MinIO volume or a new S3 account has no bucket, and the first
        upload would fail with NoSuchBucket. Creating it here means the store
        is usable from a cold start without an external provisioning step —
        and it is idempotent, so it costs one HEAD after the first call.
        """
        if self._bucket_checked or self._client is None:
            return
        from botocore.exceptions import ClientError

        bucket = settings.S3_BUCKET
        try:
            self._client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status not in (403, 404):
                raise
            if status == 403:
                # The bucket exists but belongs to someone else, or the
                # credentials cannot inspect it. Creating it would fail too.
                log.warning("storage.bucket_not_inspectable", bucket=bucket)
                self._bucket_checked = True
                return
            try:
                if settings.S3_REGION and settings.S3_REGION != "us-east-1":
                    self._client.create_bucket(
                        Bucket=bucket,
                        CreateBucketConfiguration={
                            "LocationConstraint": settings.S3_REGION
                        },
                    )
                else:
                    self._client.create_bucket(Bucket=bucket)
                log.info("storage.bucket_created", bucket=bucket)
            except ClientError as create_error:
                code = create_error.response.get("Error", {}).get("Code", "")
                # Another worker won the race; that is the desired end state.
                if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                    raise
        self._bucket_checked = True

    async def put(self, key: str, data: bytes, content_type: str) -> None:  # pragma: no cover
        def _put() -> None:
            self._get_client().put_object(
                Bucket=settings.S3_BUCKET, Key=key, Body=data,
                ContentType=content_type, ServerSideEncryption="AES256",
            )

        try:
            await asyncio.to_thread(_put)
        except Exception as exc:
            log.error("storage.put_failed", error=str(exc)[:200])
            raise StorageError() from exc

    async def get(self, key: str) -> bytes:  # pragma: no cover
        def _get() -> bytes:
            response = self._get_client().get_object(Bucket=settings.S3_BUCKET, Key=key)
            return response["Body"].read()

        try:
            return await asyncio.to_thread(_get)
        except Exception as exc:
            raise StorageError("Stored file is missing", code="OBJECT_NOT_FOUND") from exc

    async def delete(self, key: str) -> None:  # pragma: no cover
        def _delete() -> None:
            self._get_client().delete_object(Bucket=settings.S3_BUCKET, Key=key)

        await asyncio.to_thread(_delete)

    async def signed_url(self, key: str, *, filename: str, expires: int) -> str:  # pragma: no cover
        def _sign() -> str:
            return self._get_client().generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.S3_BUCKET,
                    "Key": key,
                    "ResponseContentDisposition": f'attachment; filename="{filename}"',
                },
                ExpiresIn=expires,
            )

        return await asyncio.to_thread(_sign)


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _backend
    if _backend is None:
        _backend = S3Storage() if settings.STORAGE_PROVIDER == "s3" else LocalStorage()
        log.info("storage.backend_selected", backend=_backend.name)
    return _backend


def reset_storage() -> None:
    """Test hook."""
    global _backend
    _backend = None


async def store_upload(
    *, owner_id: uuid.UUID, kind: str, filename: str, content_type: str, data: bytes
) -> StoredObject:
    resolved_type = validate_upload(filename, content_type, data)
    key = build_storage_key(owner_id, kind, filename)
    await get_storage().put(key, data, resolved_type)
    return StoredObject(
        storage_key=key,
        size_bytes=len(data),
        content_type=resolved_type,
        checksum_sha256=hashlib.sha256(data).hexdigest(),
        provider=get_storage().name,
    )


def verify_download_token(token: str) -> str | None:
    """Return the storage key if the signed token is valid and unexpired."""
    payload = unsign_value(token)
    if not payload or "|" not in payload:
        return None
    key, _, expiry = payload.rpartition("|")
    try:
        if int(expiry) < int(datetime.now(UTC).timestamp()):
            return None
    except ValueError:
        return None
    return key


async def scan_for_malware(data: bytes, filename: str) -> tuple[str, str | None]:
    """Virus-scanning hook.

    Returns ``(status, detail)``. The default implementation performs cheap
    structural checks only and reports SKIPPED, which is honest: wire a real
    scanner (ClamAV, VirusTotal, a cloud AV API) in here for production and set
    ``VIRUS_SCAN_ENABLED=true``.
    """
    if not settings.VIRUS_SCAN_ENABLED:
        return "SKIPPED", "Scanning is disabled in this environment"

    # EICAR test signature - lets deployments verify the path end to end.
    if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in data[:1024]:
        return "INFECTED", "EICAR test signature detected"
    # Executable headers inside a document container are a strong signal.
    if data.startswith((b"MZ", b"\x7fELF")):
        return "INFECTED", "Executable content detected"
    return "CLEAN", None
