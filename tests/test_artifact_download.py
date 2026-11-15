from __future__ import annotations

import io
import tempfile
import threading
import time
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import importlib.util
import sys

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "download_github_workflow_artifact.py"
SPEC = importlib.util.spec_from_file_location("download_github_workflow_artifact", SCRIPT_PATH)
ARTIFACT_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ARTIFACT_MODULE
SPEC.loader.exec_module(ARTIFACT_MODULE)

ArtifactDownloadError = ARTIFACT_MODULE.ArtifactDownloadError
_rate_limit_delay = ARTIFACT_MODULE._rate_limit_delay
download_artifact = ARTIFACT_MODULE.download_artifact
safe_extract = ARTIFACT_MODULE.safe_extract


def make_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("reports/checkpoint.json", '{"status":"verified"}')
    return buffer.getvalue()


class Handler(BaseHTTPRequestHandler):
    attempts = 0
    error_codes = [502, 403]
    archive_bytes = make_zip()

    def do_GET(self):
        if self.path == "/repos/org/repo/actions/artifacts/42/zip":
            Handler.attempts += 1
            error_index = Handler.attempts - 1
            if error_index < len(Handler.error_codes):
                status = Handler.error_codes[error_index]
                body = (
                    b'{"message":"API rate limit exceeded for installation"}'
                    if status == 403 else b'{"message":"temporary artifact service error"}'
                )
                self.send_response(status)
                if status == 403:
                    self.send_header("X-RateLimit-Reset", str(int(time.time())))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(302)
            self.send_header("Location", "/artifact-blob")
            self.end_headers()
            return
        if self.path == "/artifact-blob":
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(Handler.archive_bytes)))
            self.end_headers()
            self.wfile.write(Handler.archive_bytes)
            return
        self.send_error(404)

    def log_message(self, *_):
        pass


class GitHubArtifactDownloadTests(unittest.TestCase):
    def setUp(self):
        Handler.attempts = 0
        Handler.error_codes = [502, 403]
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.api_base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_rate_limited_artifact_download_retries_and_extracts(self):
        sleeps = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = download_artifact(
                "org/repo",
                42,
                root / "checkpoint.zip",
                "test-token",
                max_wait_seconds=10,
                api_base_url=self.api_base,
                sleep_fn=sleeps.append,
            )
            safe_extract(archive, root / "unpacked")
            self.assertEqual(Handler.attempts, 3)
            self.assertEqual(len(sleeps), 2)
            content = (root / "unpacked/reports/checkpoint.json").read_text()
            self.assertEqual(content, '{"status":"verified"}')

    def test_delay_prefers_retry_after_and_bounds_wait(self):
        self.assertEqual(
            _rate_limit_delay({"Retry-After": "7"}, "", 1, time.time()),
            7.0,
        )
        self.assertEqual(
            _rate_limit_delay({"X-RateLimit-Reset": "100"}, "", 1, 100),
            5.0,
        )

    def test_rejects_unsafe_zip_paths(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../escape.txt", "not allowed")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "unsafe.zip"
            archive_path.write_bytes(buffer.getvalue())
            with self.assertRaisesRegex(ArtifactDownloadError, "unsafe ZIP member"):
                safe_extract(archive_path, Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
