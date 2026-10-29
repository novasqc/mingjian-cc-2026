"""Stable lastmod dates for generated pages without editorial date metadata.

The manifest binds a date to the complete generated HTML bytes (including links
and structured data). It is build state, not a publication log. Keep it with the
generated site. Article dates remain the responsibility of editorial metadata.

On first adoption, existing HTML and sitemap must be a consistent checked-out
pair. Their association cannot be reconstructed from files after an unrecorded
partial build. Save this migrated baseline BEFORE overwriting any HTML. Later
builds compare to the saved hashes, even when a previous build stopped midway.
Missing dates are left unknown; corrupt manifests are rebaselined without dates.
No filesystem mtime, Git history, network, or newest article date is used.
"""

from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import xml.etree.ElementTree as ET


_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def valid_date(value):
    """Accept valid sitemap dates/timestamps, not arbitrary XML text."""
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        return False
    try:
        if "T" in value:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            date.fromisoformat(value)
    except ValueError:
        return False
    return True


def lastmod_xml(value):
    return "<lastmod>%s</lastmod>\n" % value if valid_date(value) else ""


class PageLastmods:
    """Capture before rendering; resolve after rendering; save before sitemap.

    An entirely new page without a previous fingerprint starts with no inferred
    lastmod. The first later observed content change gives it a known date.
    """

    def __init__(self, root, paths, domain, build_date=None, warn=None):
        self.root = Path(root)
        self.state_path = self.root / "build" / "sitemap-state.json"
        self.build_date = build_date or date.today().isoformat()
        if not valid_date(self.build_date):
            raise ValueError("Invalid build date")
        self.warn = warn or (lambda message: print(message, file=sys.stderr))
        self.pages = {}
        existing, corrupt = self._read_state()
        previous_dates = {} if corrupt else self._read_sitemap(domain)
        for path in sorted(set(paths)):
            parts = PurePosixPath(path)
            if parts.is_absolute() or ".." in parts.parts or "\\" in path:
                raise ValueError("Unsafe sitemap path: %r" % path)
            entry = existing.get(path)
            if self._valid_entry(entry):
                self.pages[path] = dict(entry)
            else:
                # A corrupt entry cannot safely bind the current HTML to an old
                # sitemap date: those files might come from a partial build.
                if path in existing:
                    self.warn("Invalid sitemap state for %s; date omitted" % path)
                digest = self._hash(path)
                previous = previous_dates.get(path) if path not in existing else None
                self.pages[path] = {
                    "sha256": digest,
                    "lastmod": previous if digest else None,
                }

    @staticmethod
    def _valid_entry(entry):
        if not isinstance(entry, dict) or set(entry) != {"sha256", "lastmod"}:
            return False
        digest, modified = entry["sha256"], entry["lastmod"]
        if digest is None:
            return modified is None
        return (isinstance(digest, str) and bool(_HASH.fullmatch(digest))
                and (modified is None or valid_date(modified)))

    def _read_state(self):
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("pages"), dict):
                raise ValueError("unrecognized schema")
            return data["pages"], False
        except FileNotFoundError:
            return {}, False
        except (ValueError, UnicodeError) as exc:
            self.warn("Invalid sitemap manifest; dates omitted while rebaselining: %s" % exc)
            return {}, True

    def _read_sitemap(self, domain):
        try:
            tree = ET.parse(self.root / "sitemap.xml")
        except FileNotFoundError:
            return {}
        except (ET.ParseError, UnicodeError) as exc:
            self.warn("Invalid existing sitemap; no historical dates inferred: %s" % exc)
            return {}
        dates = {}
        prefix = domain.rstrip("/") + "/"
        for node in tree.findall(_NS + "url"):
            url = node.findtext(_NS + "loc", "")
            modified = node.findtext(_NS + "lastmod")
            if url.startswith(prefix) and valid_date(modified):
                dates[url[len(prefix):]] = modified
        return dates

    def _hash(self, path):
        try:
            return hashlib.sha256((self.root / path).read_bytes()).hexdigest()
        except FileNotFoundError:
            return None

    def resolve(self, path):
        """Resolve only a captured path, after its final HTML has been written."""
        entry = self.pages[path]
        digest = self._hash(path)
        if digest is None:
            # A missing generated page is an audit failure, not a new date.
            return None
        if entry["sha256"] is not None and digest != entry["sha256"]:
            entry["lastmod"] = self.build_date
        entry["sha256"] = digest
        return entry["lastmod"]

    def save(self):
        """Atomically persist; do not touch the file on a no-op build."""
        payload = (json.dumps({"version": 1, "pages": self.pages}, ensure_ascii=False,
                              sort_keys=True, indent=2) + "\n").encode("utf-8")
        try:
            if self.state_path.read_bytes() == payload:
                return
        except FileNotFoundError:
            pass
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".sitemap-state-", dir=self.state_path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
            os.replace(temporary, self.state_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
