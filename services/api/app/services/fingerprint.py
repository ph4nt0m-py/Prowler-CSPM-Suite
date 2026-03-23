import hashlib


def finding_fingerprint(check_id: str, resource_id: str, region: str) -> str:
    """Stable key: check_id + resource_id + region (empty region normalized to '*')."""
    c = check_id.strip()
    r = resource_id.strip()
    reg = region.strip() if region and region.strip() else "*"
    raw = f"{c}|{r}|{reg}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
