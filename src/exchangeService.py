import os
import logging
import subprocess
import sys

EXPORT_PATH_KEY = "Export path:"


class ExchangeService:
    def __init__(self, upload_script_path: str, file_path: str):
        self.upload_script_path = upload_script_path
        self.file_path = file_path
        self.container_name = os.getenv("SYSML_KERNEL_CONTAINER", "sysml-kernel-container")

    def read_sysml_files(self):
        if not os.path.isdir(self.file_path):
            logging.error("SysML input directory does not exist: %s", self.file_path)
            return []

        return sorted([
            os.path.join(self.file_path, f)
            for f in os.listdir(self.file_path)
            if f.endswith(".sysml")
        ])

    def sendToApi(self, data: list[str]) -> str:
        logging.info("Uploading SysML files to the API...")
        print(f">> Uploading files: {data}", flush=True)
        result = subprocess.run(
            ["sh", self.upload_script_path, *data],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
        )
        if result.returncode != 0:
            logging.error("STDOUT: %s", result.stdout)
            logging.error("STDERR: %s", result.stderr)
            sys.exit(1)

        logging.info("Full STDOUT: %s", result.stdout)

        export_line = next(
            (line for line in result.stdout.splitlines() if line.strip().startswith(EXPORT_PATH_KEY)),
            None,
        )
        if not export_line:
            logging.error("%s not found in SysML kernel output", EXPORT_PATH_KEY)
            sys.exit(1)

        container_path = export_line.split(":", 1)[1].strip()
        if not container_path or container_path == "NOT_FOUND":
            logging.error("SysML kernel did not produce an export file")
            sys.exit(1)

        local_path = os.path.join(os.path.dirname(self.upload_script_path), "export.json")

        cp_result = subprocess.run(
            ["docker", "cp", f"{self.container_name}:{container_path}", local_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if cp_result.returncode != 0:
            logging.error("docker cp failed: %s", cp_result.stderr)
            sys.exit(1)

        logging.info(f"Export saved to: {local_path}")
        return local_path
