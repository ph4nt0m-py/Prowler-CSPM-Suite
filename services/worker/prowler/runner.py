"""Run Prowler inside Docker with a fixed argv allowlist (no shell, no user-controlled flags)."""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ProwlerAwsOptions(BaseModel):
    """Validated scan options passed to Prowler CLI."""

    regions: list[str] = Field(default_factory=list)

    @field_validator("regions")
    @classmethod
    def validate_regions(cls, v: list[str]) -> list[str]:
        for r in v:
            if not re.match(r"^[a-z0-9-]+$", r, re.I):
                raise ValueError(f"Invalid region: {r!r}")
        return v


def _docker_bin() -> str:
    """Resolve docker CLI path (Celery workers may have a minimal PATH without /usr/bin)."""
    override = os.environ.get("DOCKER_BIN", "").strip()
    if override:
        return override
    w = shutil.which("docker")
    if w:
        return w
    for candidate in ("/usr/local/bin/docker", "/usr/bin/docker", "/bin/docker"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(
        "docker CLI not found. Rebuild the worker image (static client in /usr/local/bin/docker) or set DOCKER_BIN."
    )


def _env_args(aws_env: dict[str, str]) -> list[str]:
    out: list[str] = []
    for k, v in aws_env.items():
        if k.startswith("AWS_") and v is not None:
            out.extend(["-e", f"{k}={v}"])
    return out


def _prowler_docker_cmd(
    *,
    host_output_dir: Path,
    aws_env: dict[str, str],
    image: str,
    options: ProwlerAwsOptions,
) -> list[str]:
    host_output_dir.mkdir(parents=True, exist_ok=True)
    # Share the worker's volumes with the Prowler sibling container so both
    # see the same named Docker volume for /data/scans.  A plain bind-mount
    # (``-v /data/scans/…:/output``) is resolved by the *host* Docker daemon,
    # which points to a different location than the named volume the worker uses.
    worker_cid = socket.gethostname()
    container_output = str(host_output_dir)
    cmd: list[str] = [
        _docker_bin(),
        "run",
        "--rm",
        "--user",
        "0:0",
        "--volumes-from",
        worker_cid,
        *_env_args(aws_env),
        image,
        "aws",
        # Prowler exits 3 when any check FAILs (expected). We only fail the pipeline on real errors.
        # https://docs.prowler.com/user-guide/cli/tutorials/misc#disable-exit-code-3
        "--ignore-exit-code-3",
        "-M",
        "json-ocsf",
        "--output-directory",
        container_output,
    ]
    for reg in options.regions:
        cmd.extend(["--region", reg])
    return cmd


def run_prowler_aws(
    *,
    image: str,
    host_output_dir: Path,
    aws_env: dict[str, str],
    options: ProwlerAwsOptions | None = None,
    on_log_chunk: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """Run Prowler in Docker. If ``on_log_chunk`` is set, stream stdout/stderr and flush batches (~1s / 8KiB)."""
    options = options or ProwlerAwsOptions()
    cmd = _prowler_docker_cmd(host_output_dir=host_output_dir, aws_env=aws_env, image=image, options=options)

    if on_log_chunk is None:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=86400,
        )
        log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return proc.returncode, log

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    full_parts: list[str] = []
    pending: list[str] = []
    last_flush = time.monotonic()
    flush_bytes = 8192
    flush_sec = 1.0

    def flush() -> None:
        nonlocal pending, last_flush
        if not pending:
            return
        on_log_chunk("".join(pending))
        pending.clear()
        last_flush = time.monotonic()

    def kill_proc() -> None:
        try:
            proc.kill()
        except OSError:
            pass

    timer = threading.Timer(86400.0, kill_proc)
    timer.daemon = True
    timer.start()
    assert proc.stdout is not None
    try:
        while True:
            chunk = proc.stdout.read(4096)
            if chunk:
                full_parts.append(chunk)
                pending.append(chunk)
                pending_len = sum(len(p) for p in pending)
                if pending_len >= flush_bytes or time.monotonic() - last_flush >= flush_sec:
                    flush()
            if not chunk:
                proc.wait()
                flush()
                break
    finally:
        timer.cancel()

    rc = proc.returncode if proc.returncode is not None else -1
    full_log = "".join(full_parts)
    return rc, full_log


def run_prowler_aws_subprocess_no_docker(
    *,
    host_output_dir: Path,
    aws_env: dict[str, str],
    options: ProwlerAwsOptions | None = None,
) -> tuple[int, str]:
    """Fallback for hosts where Prowler is installed locally (not used in Docker worker by default)."""
    options = options or ProwlerAwsOptions()
    host_output_dir.mkdir(parents=True, exist_ok=True)
    out_path = str(host_output_dir.resolve())
    env = {**os.environ, **aws_env}
    cmd: list[str] = [
        "prowler",
        "aws",
        "--ignore-exit-code-3",
        "-M",
        "json-ocsf",
        "--output-directory",
        out_path,
    ]
    for reg in options.regions:
        cmd.extend(["--region", reg])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=86400, env=env)
    log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, log
