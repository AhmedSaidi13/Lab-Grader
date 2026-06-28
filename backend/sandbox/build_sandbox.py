#!/usr/bin/env python3
"""
build_sandbox.py
────────────────
Builds the c-sandbox Docker image using the Python Docker SDK.
"""

import sys
import docker

SANDBOX_IMAGE = "c-sandbox:latest"
DOCKERFILE    = "Dockerfile.sandbox"
BUILD_PATH    = "/sandbox"


def get_client():
    """Connect to Docker daemon via socket (most reliable in containers)."""
    for base_url in [
        "unix:///var/run/docker.sock",
        "tcp://host.docker.internal:2375",
        "tcp://localhost:2375",
    ]:
        try:
            c = docker.DockerClient(base_url=base_url, timeout=120)
            c.ping()
            print(f">>> Connected via {base_url}", flush=True)
            return c
        except Exception as e:
            print(f">>> {base_url} failed: {e}", flush=True)

    print("ERROR: Cannot connect to Docker daemon", flush=True)
    sys.exit(1)


def main():
    print(">>> Connecting to Docker daemon...", flush=True)
    client = get_client()

    # Show Docker info
    info = client.info()
    print(f">>> Docker version: {client.version()['Version']}", flush=True)
    print(f">>> OS: {info.get('OSType', 'unknown')}", flush=True)

    # Remove old image
    print(">>> Removing old sandbox image...", flush=True)
    try:
        client.images.remove(SANDBOX_IMAGE, force=True)
        print(">>> Old image removed.", flush=True)
    except docker.errors.ImageNotFound:
        print(">>> No old image, continuing.", flush=True)
    except Exception as e:
        print(f">>> Warning: {e}", flush=True)

    # Build image
    print(f">>> Building {SANDBOX_IMAGE}...", flush=True)
    try:
        image, logs = client.images.build(
            path       = BUILD_PATH,
            dockerfile = DOCKERFILE,
            tag        = SANDBOX_IMAGE,
            rm         = True,
            nocache    = True,
            platform   = "linux/amd64",
        )
        for chunk in logs:
            if "stream" in chunk:
                line = chunk["stream"].rstrip()
                if line:
                    print(f"  {line}", flush=True)
            elif "error" in chunk:
                print(f"ERROR: {chunk['error']}", flush=True)
                sys.exit(1)

        print(f">>> Built: {image.short_id}", flush=True)

    except docker.errors.BuildError as e:
        print(f"ERROR: Build failed: {e}", flush=True)
        for line in e.build_log:
            if "stream" in line:
                print(f"  {line['stream'].rstrip()}", flush=True)
            elif "error" in line:
                print(f"  ERROR: {line['error']}", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Verify
    img = client.images.get(SANDBOX_IMAGE)
    cfg = img.attrs.get("Config", {})
    print(f">>> Entrypoint: {cfg.get('Entrypoint')}", flush=True)
    print(f">>> Cmd:        {cfg.get('Cmd')}", flush=True)

    # Smoke test
    print(">>> Smoke test: gcc --version...", flush=True)
    try:
        out = client.containers.run(
            image      = SANDBOX_IMAGE,
            command    = ["gcc", "--version"],
            remove     = True,
            entrypoint = [],
        )
        print(f">>> {out.decode().split(chr(10))[0]}", flush=True)
    except Exception as e:
        print(f"ERROR: Smoke test failed: {e}", flush=True)
        sys.exit(1)

    print(">>> Sandbox image ready!", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()