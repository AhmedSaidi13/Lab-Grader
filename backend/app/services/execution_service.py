"""
execution_service.py
────────────────────
Passes source code to the sandbox by writing it inline via shell,
bypassing all tmpfs/put_archive issues.

Strategy:
  1. Start container with a writable /tmp (not tmpfs)
  2. Use exec_run to write the source file via 'cat > /tmp/file.c << EOF'
  3. Compile and run from /tmp
  4. Remove container
"""

import io
import os
import time
import base64
import shutil
import tempfile
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import docker
from docker.errors import ImageNotFound

from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

COMPILE_TIMEOUT_S = 30
RUN_TIMEOUT_S     = 10


# ── Data structures ───────────────────────────────────────────

@dataclass
class CompileResult:
    success:     bool
    output:      str
    duration_ms: float


@dataclass
class RunResult:
    success:     bool
    stdout:      str
    stderr:      str
    exit_code:   int
    duration_ms: float
    timed_out:   bool


@dataclass
class ExecutionResult:
    compile: CompileResult
    runs:    list[RunResult] = field(default_factory=list)


# ── Docker client ─────────────────────────────────────────────

def _get_docker_client() -> docker.DockerClient:
    errors = []
    for base_url in [
        "unix:///var/run/docker.sock",
        "tcp://host.docker.internal:2375",
        "tcp://localhost:2375",
    ]:
        try:
            client = docker.DockerClient(base_url=base_url, timeout=60)
            client.ping()
            logger.debug("Docker connected via %s", base_url)
            return client
        except Exception as e:
            errors.append(f"{base_url}: {e}")
    raise RuntimeError("Cannot connect to Docker:\n" + "\n".join(errors))


# ── Sandbox image check ───────────────────────────────────────

def ensure_sandbox_image() -> None:
    client = _get_docker_client()
    try:
        img = client.images.get(settings.SANDBOX_IMAGE)
        logger.info("Sandbox image found: %s", img.short_id)
    except ImageNotFound:
        raise RuntimeError(
            f"Sandbox image '{settings.SANDBOX_IMAGE}' not found. "
            "Run: docker build --platform linux/amd64 "
            "-f backend/sandbox/Dockerfile.sandbox "
            "-t c-sandbox:latest backend/sandbox/"
        )


# ── Container start/stop ──────────────────────────────────────

def _start_container(client: docker.DockerClient):
    """
    Start a sandbox container with a writable /tmp.
    NO tmpfs — regular writable layer so put_archive and
    exec_run can both access the same files.
    """
    container = client.containers.run(
        image         = settings.SANDBOX_IMAGE,
        command       = ["sleep", "120"],   # auto-dies after 2 min max
        detach        = True,
        network_mode  = "none",
        mem_limit     = "128m",
        memswap_limit = "128m",
        nano_cpus     = 500_000_000,
        pids_limit    = 64,
        security_opt  = ["no-new-privileges"],
        cap_drop      = ["ALL"],
        # NO tmpfs — use regular writable container layer
        working_dir   = "/tmp",
        entrypoint    = [],
        user          = "root",   # start as root so we can write files
    )

    # Wait until running
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        container.reload()
        if container.status == "running":
            logger.debug("Container %s running", container.short_id)
            return container
        time.sleep(0.1)

    container.remove(force=True)
    raise RuntimeError("Container did not start in time")


def _stop_container(container) -> None:
    try:
        container.remove(force=True)
    except Exception as e:
        logger.warning("Could not remove container %s: %s",
                       getattr(container, 'short_id', '?'), e)


# ── Write file into container via base64 ─────────────────────

def _write_file_to_container(
    container,
    content_bytes: bytes,
    dest_path:     str,
) -> None:
    """
    Write arbitrary bytes into a running container by passing
    base64-encoded content through exec_run shell command.
    This works regardless of tmpfs/overlay/volume configuration.
    """
    b64 = base64.b64encode(content_bytes).decode("ascii")

    # Write in chunks to avoid ARG_MAX limits
    chunk_size  = 4000
    chunks      = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]

    # First chunk: create file
    result = container.exec_run(
        cmd   = ["/bin/bash", "-c",
                 f"printf '%s' '{chunks[0]}' > {dest_path}.b64"],
        user  = "root",
        demux = True,
    )
    if result.exit_code != 0:
        raise RuntimeError(
            f"Failed to start writing {dest_path}: "
            + (result.output[1] or b"").decode(errors="replace")
        )

    # Subsequent chunks: append
    for chunk in chunks[1:]:
        result = container.exec_run(
            cmd   = ["/bin/bash", "-c",
                     f"printf '%s' '{chunk}' >> {dest_path}.b64"],
            user  = "root",
            demux = True,
        )
        if result.exit_code != 0:
            raise RuntimeError(f"Failed to append chunk to {dest_path}")

    # Decode base64 to final file
    result = container.exec_run(
        cmd   = ["/bin/bash", "-c",
                 f"base64 -d {dest_path}.b64 > {dest_path} && rm {dest_path}.b64"],
        user  = "root",
        demux = True,
    )
    if result.exit_code != 0:
        stderr = (result.output[1] or b"").decode(errors="replace")
        raise RuntimeError(f"base64 decode failed for {dest_path}: {stderr}")

    # Verify file exists and has content
    verify = container.exec_run(
        cmd   = ["/bin/bash", "-c",
                 f"test -f {dest_path} && wc -c < {dest_path}"],
        user  = "root",
        demux = True,
    )
    size_str = (verify.output[0] or b"").decode().strip()
    logger.debug("Written %s bytes to container:%s", size_str, dest_path)

    if verify.exit_code != 0 or size_str == "0":
        raise RuntimeError(
            f"File {dest_path} is missing or empty after write"
        )


# ── Core execution ────────────────────────────────────────────

def _exec(container, cmd: list[str], user: str = "root") -> tuple[int, str, str]:
    """Run a command in the container. Returns (exit_code, stdout, stderr)."""
    result = container.exec_run(
        cmd   = cmd,
        user  = user,
        demux = True,
    )
    stdout = (result.output[0] or b"").decode("utf-8", errors="replace")
    stderr = (result.output[1] or b"").decode("utf-8", errors="replace")
    return result.exit_code, stdout, stderr


def _exec_shell(container, shell_cmd: str, user: str = "root") -> tuple[int, str, str]:
    """Run a shell command string in the container."""
    return _exec(container, ["/bin/bash", "-c", shell_cmd], user=user)


# ── Public: compile ───────────────────────────────────────────

def compile_c_file(source_path: Path) -> CompileResult:
    if not source_path.exists():
        return CompileResult(
            success     = False,
            output      = f"File not found on API server: {source_path}",
            duration_ms = 0.0,
        )

    source_name   = source_path.name
    binary_name   = source_name.replace(".c", "")
    source_bytes  = source_path.read_bytes()
    src_in_cont   = f"/tmp/{source_name}"
    bin_in_cont   = f"/tmp/{binary_name}"

    client    = _get_docker_client()
    container = None

    try:
        container = _start_container(client)

        # Write source into container
        _write_file_to_container(container, source_bytes, src_in_cont)

        # Compile
        t0 = time.monotonic()
        exit_code, stdout, stderr = _exec(
            container,
            ["gcc", "-Wall", "-Wextra", "-O0", "-std=c11",
             src_in_cont, "-o", bin_in_cont, "-lm"],
        )
        duration_ms = (time.monotonic() - t0) * 1000
        output      = (stdout + stderr).strip()
        success     = exit_code == 0

        logger.info("Compile '%s': %s in %.0fms",
                    source_name, "OK" if success else "FAILED", duration_ms)

        return CompileResult(
            success     = success,
            output      = output or ("Compilation successful" if success else "Unknown error"),
            duration_ms = duration_ms,
        )

    finally:
        if container:
            _stop_container(container)


# ── Public: compile + run ─────────────────────────────────────

def run_c_binary(
    source_path: Path,
    stdin_input: Optional[str] = None,
    timeout_s:   int           = RUN_TIMEOUT_S,
) -> RunResult:
    if not source_path.exists():
        return RunResult(
            success=False, stdout="", stderr=f"File not found: {source_path}",
            exit_code=-1, duration_ms=0.0, timed_out=False,
        )

    source_name  = source_path.name
    binary_name  = source_name.replace(".c", "")
    source_bytes = source_path.read_bytes()
    src_in_cont  = f"/tmp/{source_name}"
    bin_in_cont  = f"/tmp/{binary_name}"
    stdin_in_cont= "/tmp/stdin.txt"

    client    = _get_docker_client()
    container = None

    try:
        container = _start_container(client)

        # Write source
        _write_file_to_container(container, source_bytes, src_in_cont)

        # Write stdin file if provided
        if stdin_input is not None:
            _write_file_to_container(
                container,
                stdin_input.encode("utf-8"),
                stdin_in_cont,
            )

        # Compile
        ce, cs, cerr = _exec(
            container,
            ["gcc", "-Wall", "-O0", "-std=c11",
             src_in_cont, "-o", bin_in_cont, "-lm"],
        )
        if ce != 0:
            return RunResult(
                success=False, stdout="",
                stderr=(cs + cerr).strip(),
                exit_code=ce, duration_ms=0.0, timed_out=False,
            )

        # Make binary executable
        _exec_shell(container, f"chmod +x {bin_in_cont}")

        # Run
        if stdin_input is not None:
            run_cmd = f"timeout {timeout_s} {bin_in_cont} < {stdin_in_cont}"
        else:
            run_cmd = f"timeout {timeout_s} {bin_in_cont}"

        t0 = time.monotonic()
        exit_code, stdout, stderr = _exec_shell(container, run_cmd)
        duration_ms = (time.monotonic() - t0) * 1000
        timed_out   = exit_code == 124 or "__TIMEOUT__" in stderr

        logger.info(
            "Run '%s': exit=%d timed_out=%s %.0fms stdout=%r",
            source_name, exit_code, timed_out, duration_ms,
            stdout.strip()[:50],
        )

        return RunResult(
            success     = exit_code == 0,
            stdout      = stdout.strip(),
            stderr      = stderr.strip(),
            exit_code   = exit_code,
            duration_ms = duration_ms,
            timed_out   = timed_out,
        )

    finally:
        if container:
            _stop_container(container)


# ── Full test pipeline ────────────────────────────────────────

def run_c_file_with_tests(
    source_path:        Path,
    test_cases:         list[dict],
    timeout_per_test_s: int = RUN_TIMEOUT_S,
) -> ExecutionResult:
    compile_result = compile_c_file(source_path)
    if not compile_result.success:
        return ExecutionResult(compile=compile_result, runs=[])

    runs: list[RunResult] = []
    for tc in test_cases:
        result = run_c_binary(
            source_path = source_path,
            stdin_input = tc.get("input") or None,
            timeout_s   = tc.get("timeout_seconds", timeout_per_test_s),
        )
        runs.append(result)

    return ExecutionResult(compile=compile_result, runs=runs)


# ── Health check ──────────────────────────────────────────────

def sandbox_health_check() -> dict:
    import textwrap
    hello_c = textwrap.dedent("""\
        #include <stdio.h>
        int main(void) {
            printf("SANDBOX_OK\\n");
            return 0;
        }
    """)
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        src = tmp_dir / "health_check.c"
        src.write_text(hello_c)
        result = run_c_binary(src)
        ok = result.success and "SANDBOX_OK" in result.stdout
        return {
            "healthy":     ok,
            "stdout":      result.stdout,
            "stderr":      result.stderr,
            "exit_code":   result.exit_code,
            "duration_ms": result.duration_ms,
        }
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return {"healthy": False, "error": str(exc)}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)