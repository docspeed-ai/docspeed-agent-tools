#!/usr/bin/env python3
"""Stream one authorized document to Docspeed; print only its reusable file reference.

Original Docspeed implementation using Python's standard library. No document
bytes, credentials, or raw response bodies are printed. There are no redirects,
automatic retries, alternate origins, or processing calls.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys

HOST = "api.docspeed.ai"
UPLOAD_PATH = "/api/v1/upload"
MAX_FILE_BYTES = 50 * 1024 * 1024
CHUNK_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
CONTENT_TYPES = {
    ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".tif": "image/tiff", ".tiff": "image/tiff",
    ".webp": "image/webp", ".bmp": "image/bmp", ".gif": "image/gif",
}


class UploadError(Exception):
    """A safe, user-facing failure; never include raw server/transport messages."""


def upload(path: Path) -> dict[str, str]:
    """Upload exactly one file, using the existing account-owned public contract."""
    token = os.environ.get("DOCSPEED_API_KEY", "")
    if not token or len(token) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise UploadError("Set DOCSPEED_API_KEY in the launching terminal; never pass the key as an argument.")
    filename = path.name
    content_type = CONTENT_TYPES.get(path.suffix.lower())
    if not content_type:
        raise UploadError("Use a supported PDF, PNG, JPEG, TIFF, WebP, BMP, or GIF file.")
    if not filename or any(ord(c) < 32 or ord(c) == 127 for c in filename):
        raise UploadError("The filename must not contain control characters.")
    boundary = "docspeed-" + secrets.token_hex(24)
    escaped_name = filename.replace("\\", "\\\\").replace('"', '\\"')
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{escaped_name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
    connection = None
    try:
        if not path.is_file():
            raise UploadError("Choose a readable regular file, not a device, directory, or stream.")
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise UploadError("Choose a regular file, not a device, directory, or stream.")
            if not 0 < before.st_size <= MAX_FILE_BYTES:
                raise UploadError("The file must be nonempty and at most 50 MiB.")
            # HTTPSConnection verifies the certificate and hostname by default.
            # A fixed origin and manual request prevent credential-bearing redirects.
            connection = http.client.HTTPSConnection(HOST, timeout=120)
            connection.putrequest("POST", UPLOAD_PATH)
            connection.putheader("Authorization", "Bearer " + token)
            connection.putheader("Accept", "application/json")
            connection.putheader("Content-Type", "multipart/form-data; boundary=" + boundary)
            connection.putheader("Content-Length", str(len(prefix) + before.st_size + len(suffix)))
            connection.endheaders()
            connection.send(prefix)
            remaining = before.st_size
            while remaining:
                chunk = source.read(min(CHUNK_BYTES, remaining))
                if not chunk:
                    raise UploadError("The file changed during upload; no retry was made.")
                connection.send(chunk)
                remaining -= len(chunk)
            after = os.fstat(source.fileno())
            if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
                raise UploadError("The file changed during upload; no retry was made.")
            connection.send(suffix)
            response = connection.getresponse()
            if response.status != 200:
                raise UploadError(f"Upload returned HTTP {response.status}; no redirect or retry was followed.")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise UploadError("Upload returned an oversized response; the file may have been accepted. No retry was made.")
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                raise UploadError("Upload returned invalid JSON; the file may have been accepted. No retry was made.") from None
            files = payload.get("files") if isinstance(payload, dict) else None
            if not isinstance(files, list) or len(files) != 1 or not isinstance(files[0], dict):
                raise UploadError("Upload returned an invalid file reference; no retry was made.")
            reference = files[0]
            file_id = reference.get("file_id")
            if not isinstance(file_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", file_id):
                raise UploadError("Upload returned an invalid file ID; no retry was made.")
            # Return our submitted filename, never arbitrary server-provided text.
            return {"file_id": file_id, "filename": filename}
    except UploadError:
        raise
    except (OSError, http.client.HTTPException):
        raise UploadError("Upload could not complete; its outcome may be unknown. No retry was made.") from None
    finally:
        if connection is not None:
            connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload one authorized PDF/image directly to Docspeed and print file_id + filename. Python 3.10+, no dependencies.")
    parser.add_argument("file", type=Path, help="Local file authorized for upload to https://api.docspeed.ai")
    args = parser.parse_args(argv)
    try:
        reference = upload(args.file)
    except UploadError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(reference, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
