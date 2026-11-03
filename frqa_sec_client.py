"""Small, explicit SEC downloader with caching and fair-access throttling.

No credentials are accepted. The caller must supply a declared User-Agent with
an organization/project name and monitored contact email before network use.
"""

from __future__ import annotations

import json
import gzip
import hashlib
import re
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


# Filing extension schemas import the SEC's official taxonomy host directly.
SEC_HOSTS = {"data.sec.gov", "www.sec.gov", "xbrl.sec.gov"}
CIK_RE = re.compile(r"^\d{1,10}$")
ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)
NON_CONTACT_MARKERS = {"example.com", "example.org", "example.net"}


class SecClient:
    """Rate-limited downloader for explicitly addressed official SEC resources."""

    def __init__(
        self,
        *,
        user_agent: str,
        cache_dir: Path,
        requests_per_second: float = 2.0,
        timeout_seconds: float = 30.0,
    ) -> None:
        email_match = EMAIL_RE.search(user_agent)
        email_domain = email_match.group(1).lower() if email_match else ""
        lowered_user_agent = user_agent.lower()
        if (
            not email_match
            or len(user_agent.strip()) < 8
            or email_domain in NON_CONTACT_MARKERS
            or "noreply" in lowered_user_agent
            or "placeholder" in lowered_user_agent
        ):
            raise ValueError("user_agent must identify the project/organization and a contact email")
        if not 0 < requests_per_second <= 10:
            raise ValueError("requests_per_second must be in (0, 10]")
        self.user_agent = user_agent
        self.cache_dir = Path(cache_dir)
        self.interval = 1.0 / requests_per_second
        self.timeout_seconds = timeout_seconds
        self._last_request = 0.0
        self.last_fetch_metadata: dict[str, Any] = {}

    def _cache_target(self, cache_key: str) -> Path:
        key_path = Path(cache_key)
        if (
            not cache_key.strip()
            or key_path.is_absolute()
            or any(part in {".", ".."} for part in key_path.parts)
        ):
            raise ValueError("cache_key must be a relative path inside cache_dir")
        cache_root = self.cache_dir.resolve()
        target = (cache_root / key_path).resolve()
        try:
            target.relative_to(cache_root)
        except ValueError as exc:
            raise ValueError("cache_key escapes cache_dir") from exc
        return target

    @staticmethod
    def submissions_url(cik: str) -> str:
        if not CIK_RE.fullmatch(str(cik)):
            raise ValueError("invalid CIK")
        return f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"

    @staticmethod
    def companyfacts_url(cik: str) -> str:
        if not CIK_RE.fullmatch(str(cik)):
            raise ValueError("invalid CIK")
        return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"

    @staticmethod
    def archive_url(cik: str, accession: str, filename: str) -> str:
        if not CIK_RE.fullmatch(str(cik)) or not ACCESSION_RE.fullmatch(accession):
            raise ValueError("invalid CIK or accession")
        if not filename or "/" in filename or "\\" in filename or filename in {".", ".."}:
            raise ValueError("filename must be a single archive filename")
        return (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{accession.replace('-', '')}/{filename}"
        )

    def fetch(self, url: str, *, cache_key: str, force: bool = False) -> bytes:
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.hostname not in SEC_HOSTS:
            raise ValueError("only HTTPS requests to official SEC hosts are allowed")
        target = self._cache_target(cache_key)
        metadata_path = target.with_name(f"{target.name}.metadata.json")
        if target.exists() and not force:
            body = target.read_bytes()
            if metadata_path.is_file():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                retrieval_status = "recorded_at_network_fetch"
            else:
                metadata = {"retrieved_at": None}
                retrieval_status = "legacy_cache_timestamp_not_recorded"
            self.last_fetch_metadata = {
                **metadata,
                "cache_status": "cache_hit",
                "retrieval_time_status": retrieval_status,
            }
            return body
        delay = self.interval - (time.monotonic() - self._last_request)
        if delay > 0:
            time.sleep(delay)
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json, application/xml, text/xml, */*",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                final_url = urlparse(response.geturl())
                if final_url.scheme != "https" or final_url.hostname not in SEC_HOSTS:
                    raise RuntimeError("SEC request redirected outside the allowed official hosts")
                body = response.read()
                encoding = (response.headers.get("Content-Encoding") or "").lower()
                if encoding == "gzip":
                    body = gzip.decompress(body)
                elif encoding == "deflate":
                    body = zlib.decompress(body)
        except HTTPError as exc:
            if exc.code in {403, 429}:
                raise RuntimeError(
                    "SEC access was rate-limited; stop the run and retry later with a lower rate"
                ) from exc
            raise
        finally:
            self._last_request = time.monotonic()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.part")
        temporary.write_bytes(body)
        temporary.replace(target)
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        metadata = {
            "url": url,
            "retrieved_at": retrieved_at,
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
        }
        metadata_temporary = metadata_path.with_name(f".{metadata_path.name}.part")
        metadata_temporary.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        metadata_temporary.replace(metadata_path)
        self.last_fetch_metadata = {
            **metadata,
            "cache_status": "network_fetch",
            "retrieval_time_status": "recorded_at_network_fetch",
        }
        return body

    def fetch_json(self, url: str, *, cache_key: str, force: bool = False) -> dict[str, Any]:
        return json.loads(self.fetch(url, cache_key=cache_key, force=force))
