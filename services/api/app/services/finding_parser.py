"""Normalize Prowler JSON outputs into Finding rows.

Supports common Prowler v3/v4 shapes: list of dicts, or OCSF-like nested structures.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Iterator

from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.services.fingerprint import finding_fingerprint

logger = logging.getLogger(__name__)

# Rare Prowler OCSF bug: objects joined with ``}]{`` instead of ``,{`` (see prowler #3675).
_OCSF_ARRAY_BREAK_RE = re.compile(r"\}\s*\]\s*\{")


def _compliance_snippet(rec: dict[str, Any]) -> str | None:
    um = rec.get("unmapped")
    if isinstance(um, dict):
        comp = um.get("compliance")
        if isinstance(comp, list) and comp:
            c0 = comp[0]
            if isinstance(c0, dict):
                return str(c0.get("requirements") or c0.get("name") or c0)[:255]
            return str(c0)[:255]
        if comp is not None:
            return str(comp)[:255]
    if isinstance(rec.get("compliance"), list) and rec["compliance"]:
        c0 = rec["compliance"][0]
        if isinstance(c0, dict):
            return str(c0.get("requirements", ""))[:255]
        return str(c0)[:255]
    return None


def _severity_from_value(val: Any) -> FindingSeverity:
    if val is None:
        return FindingSeverity.medium
    s = str(val).lower()
    if s in ("critical", "crit"):
        return FindingSeverity.critical
    if s in ("high",):
        return FindingSeverity.high
    if s in ("low",):
        return FindingSeverity.low
    if s in ("medium", "med", "informational", "info"):
        return FindingSeverity.medium
    return FindingSeverity.medium


_INGEST_STATUS_CODES = {"FAIL", "MANUAL"}


def _extract_from_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    """Map one raw record to normalized fields; return None to skip."""
    status_code = str(rec.get("status_code") or rec.get("StatusCode") or "").upper()
    if status_code and status_code not in _INGEST_STATUS_CODES:
        return None

    # Prowler 5+ json-ocsf: py_ocsf_models DetectionFinding uses top-level ``finding_info`` (not ``finding``).
    finfo_raw = rec.get("finding_info")
    if not isinstance(finfo_raw, dict):
        finfo_raw = rec.get("findingInfo")
    if isinstance(finfo_raw, dict):
        finfo = finfo_raw
        title = finfo.get("title") or finfo.get("desc") or ""
        uid = finfo.get("uid")
        meta = rec.get("metadata") if isinstance(rec.get("metadata"), dict) else {}
        check_id = str(
            meta.get("event_code") or meta.get("eventCode") or uid or title or "unknown"
        )
        resources = rec.get("resources") or rec.get("Resources") or []
        resource_id = ""
        region = ""
        service = ""
        if resources and isinstance(resources[0], dict):
            r0 = resources[0]
            resource_id = str(r0.get("uid") or r0.get("name") or r0.get("id") or "")
            region = str(r0.get("region") or r0.get("cloud_partition") or "")
            grp = r0.get("group")
            if isinstance(grp, dict):
                service = str(grp.get("name") or "")
            if not service:
                service = str(r0.get("type") or "unknown")
        sev = _severity_from_value(rec.get("severity"))
        desc = title or rec.get("message") or rec.get("status_detail") or rec.get("status_code")
        return {
            "check_id": check_id[:512],
            "resource_id": resource_id or check_id,
            "region": region,
            "service": service or "unknown",
            "severity": sev,
            "description": str(desc)[:8000] if desc else None,
            "compliance_framework": _compliance_snippet(rec),
            "raw_json": rec,
        }

    # OCSF-style wrapper with nested ``finding`` (older/alternate exports)
    if "finding" in rec and isinstance(rec["finding"], dict):
        f = rec["finding"]
        title = f.get("title") or f.get("desc") or ""
        uid = f.get("uid") or rec.get("finding_info", {}).get("uid")
        check_id = str(uid or title or "unknown")
        resources = rec.get("resources") or []
        resource_id = ""
        region = ""
        service = ""
        if resources and isinstance(resources[0], dict):
            r0 = resources[0]
            resource_id = str(r0.get("uid") or r0.get("name") or r0.get("id") or "")
            region = str(r0.get("region") or r0.get("cloud_partition") or "")
            service = str(r0.get("group", {}).get("name") or r0.get("type") or "")
        sev = _severity_from_value(rec.get("severity") or f.get("severity"))
        return {
            "check_id": check_id[:512],
            "resource_id": resource_id or check_id,
            "region": region,
            "service": service or "unknown",
            "severity": sev,
            "description": str(title)[:8000] if title else None,
            "compliance_framework": _compliance_snippet(rec),
            "raw_json": rec,
        }

    # Legacy / flat Prowler fields
    check_id = str(
        rec.get("check_id")
        or rec.get("CheckID")
        or rec.get("finding_uid")
        or rec.get("control")
        or "unknown"
    )
    resource_id = str(
        rec.get("resource_id")
        or rec.get("ResourceId")
        or rec.get("resource_uid")
        or rec.get("account_uid")
        or check_id
    )
    region = str(rec.get("region") or rec.get("Region") or rec.get("subdivision") or "")
    service = str(rec.get("service") or rec.get("Service") or rec.get("product", {}).get("name", "") or "unknown")
    desc = rec.get("message") or rec.get("status_extended") or rec.get("Description") or rec.get("description")
    compliance = rec.get("compliance") or rec.get("framework")
    if isinstance(compliance, dict):
        compliance = compliance.get("name")
    compliance = str(compliance)[:255] if compliance else None
    return {
        "check_id": check_id[:512],
        "resource_id": resource_id,
        "region": region,
        "service": service[:255],
        "severity": _severity_from_value(rec.get("severity") or rec.get("Status")),
        "description": str(desc)[:8000] if desc else None,
        "compliance_framework": compliance,
        "raw_json": rec,
    }


def iter_records_from_path(path: Path) -> Iterator[dict[str, Any]]:
    if path.is_file():
        yield from _iter_from_file(path)
        return
    for p in sorted(path.rglob("*.json")):
        yield from _iter_from_file(p)


def _decode_json_payload(text: str, path: Path) -> Any | None:
    """Strict JSON, then OCSF ``}]{`` repair, then multiple top-level JSON values (concatenated)."""
    text = text.lstrip("\ufeff").strip()
    if not text:
        return None
    first_err: json.JSONDecodeError | None = None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        first_err = e
    repaired = _OCSF_ARRAY_BREAK_RE.sub("},{", text)
    if repaired != text:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            first_err = first_err or e
    decoder = json.JSONDecoder()
    i, n = 0, len(text)
    values: list[Any] = []
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        try:
            val, j = decoder.raw_decode(text, i)
        except json.JSONDecodeError as e:
            logger.warning(
                "finding_parser: JSONDecodeError in %s: %s",
                path,
                first_err or e,
            )
            return None
        values.append(val)
        i = j
        while i < n and text[i] in ",\t\n\r ":
            i += 1
    if not values:
        if first_err:
            logger.warning("finding_parser: JSONDecodeError in %s: %s", path, first_err)
        return None
    if len(values) == 1:
        return values[0]
    merged: list[Any] = []
    for v in values:
        if isinstance(v, list):
            merged.extend(v)
        else:
            merged.append(v)
    return merged


def _iter_from_file(path: Path) -> Iterator[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    text = text.strip()
    if not text:
        return
    data = _decode_json_payload(text, path)
    if data is None:
        return
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
    elif isinstance(data, dict):
        # Single object or wrapper
        if "findings" in data and isinstance(data["findings"], list):
            for item in data["findings"]:
                if isinstance(item, dict):
                    yield item
        else:
            yield data


def build_findings_for_scan(scan_id: uuid.UUID, output_dir: Path, default_status: FindingStatus) -> list[Finding]:
    rows: list[Finding] = []
    seen_fp: set[str] = set()
    for rec in iter_records_from_path(output_dir):
        norm = _extract_from_record(rec)
        if not norm:
            continue
        fp = finding_fingerprint(norm["check_id"], norm["resource_id"], norm["region"])
        if fp in seen_fp:
            continue
        seen_fp.add(fp)
        rows.append(
            Finding(
                scan_id=scan_id,
                fingerprint=fp,
                check_id=norm["check_id"],
                resource_id=norm["resource_id"],
                region=norm["region"] or "*",
                service=norm["service"],
                severity=norm["severity"],
                status=default_status,
                description=norm["description"],
                compliance_framework=norm["compliance_framework"],
                raw_json=norm["raw_json"],
            )
        )
    return rows
