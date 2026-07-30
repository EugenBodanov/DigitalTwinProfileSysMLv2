from __future__ import annotations

import base64
import os
from pathlib import Path
import re
import sys
import time
from uuid import uuid4

from jupyter_client import BlockingKernelClient

RUNTIME_DIR = Path(
    os.getenv(
        "SYSML_KERNEL_RUNTIME_DIR",
        "/home/sysml/.local/share/jupyter/runtime",
    )
)
EXPORT_PATH = Path(os.getenv("SYSML_EXPORT_PATH", "/home/sysml/export.json"))
KERNEL_READY_TIMEOUT_SECONDS = int(os.getenv("SYSML_KERNEL_READY_TIMEOUT", "120"))
COMMAND_TIMEOUT_SECONDS = int(os.getenv("SYSML_COMMAND_TIMEOUT", "600"))
EXPORT_DATA_PATTERN = re.compile(r"""base64,([^"']+)""")


def latest_connection_file(timeout: int) -> Path:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        connection_files = list(RUNTIME_DIR.glob("kernel-*.json"))
        if connection_files:
            return max(connection_files, key=lambda path: path.stat().st_mtime)
        time.sleep(0.5)

    raise TimeoutError(
        f"No kernel connection file appeared in {RUNTIME_DIR} within {timeout} seconds"
    )


def connect_to_kernel() -> BlockingKernelClient:
    connection_file = latest_connection_file(KERNEL_READY_TIMEOUT_SECONDS)
    client = BlockingKernelClient()
    client.load_connection_file(str(connection_file))
    client.start_channels()
    client.wait_for_ready(timeout=KERNEL_READY_TIMEOUT_SECONDS)
    return client


def save_export_from_message(message: dict) -> None:
    data = message.get("content", {}).get("data", {})
    html = data.get("text/html", "")
    match = EXPORT_DATA_PATTERN.search(html)
    if not match:
        return

    decoded = base64.b64decode(match.group(1)).decode("utf-8")
    EXPORT_PATH.write_text(decoded, encoding="utf-8")
    print(">> Export saved", flush=True)


def run_command(client: BlockingKernelClient, command: str, timeout: int) -> None:
    message_id = client.execute(command)
    deadline = time.monotonic() + timeout

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"SysML kernel command timed out after {timeout} seconds")

        message = client.get_iopub_msg(timeout=remaining)
        if message.get("parent_header", {}).get("msg_id") != message_id:
            continue

        message_type = message.get("header", {}).get("msg_type")
        if message_type in ("execute_result", "display_data"):
            save_export_from_message(message)
        elif message_type == "error":
            content = message.get("content", {})
            error_name = content.get("ename", "KernelError")
            error_value = content.get("evalue", "Unknown SysML kernel error")
            raise RuntimeError(f"{error_name}: {error_value}")
        elif (
            message_type == "status"
            and message.get("content", {}).get("execution_state") == "idle"
        ):
            return


def run_task() -> None:
    raw_content = os.environ.get("SYSML_CONTENT", "")
    if not raw_content.strip():
        raise ValueError("SYSML_CONTENT is empty")

    EXPORT_PATH.unlink(missing_ok=True)
    package_name = f"GeneratedExport_{uuid4().hex}"
    client = connect_to_kernel()

    try:
        print(f">> Generate Export Container: {package_name}", flush=True)
        wrapped_content = f"package {package_name} {{\n{raw_content}\n}}"
        run_command(client, wrapped_content, COMMAND_TIMEOUT_SECONDS)

        print(f">> Export package '{package_name}'...", flush=True)
        run_command(client, f"%export {package_name}", COMMAND_TIMEOUT_SECONDS)
    finally:
        client.stop_channels()

    if not EXPORT_PATH.is_file():
        raise RuntimeError("The SysML kernel completed without producing an export")

    print(">> Export finished", flush=True)
    print(f"\nExport path: {EXPORT_PATH}", flush=True)


def main() -> int:
    try:
        run_task()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
