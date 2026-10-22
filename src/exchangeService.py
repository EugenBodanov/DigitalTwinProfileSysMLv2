import os
import logging
import subprocess

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
        logging.info("Processing SysML files...")
        print(f">> SysML files: {data}", flush=True)
        with subprocess.Popen(
            ["sh", self.upload_script_path, *data],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        ) as process:
            lines = []
            for line in process.stdout:
                print(line, end="", flush=True)
                lines.append(line)
            returncode = process.wait()

        if returncode != 0:
            raise RuntimeError(f"SysML processing failed with exit code {returncode}")

        export_line = next(
            (line for line in lines if line.strip().startswith(EXPORT_PATH_KEY)),
            None,
        )
        if not export_line:
            raise RuntimeError(f"{EXPORT_PATH_KEY} not found in SysML converter output")

        container_path = export_line.split(":", 1)[1].strip()
        if not container_path or container_path == "NOT_FOUND":
            raise RuntimeError("SysML kernel did not produce an export file")

        local_path = os.path.join(os.path.dirname(self.upload_script_path), "export.json")

        cp_result = subprocess.run(
            ["docker", "cp", f"{self.container_name}:{container_path}", local_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if cp_result.returncode != 0:
            raise RuntimeError(f"docker cp failed: {cp_result.stderr}")

        cleanup_result = subprocess.run(
            ["docker", "exec", self.container_name, "rm", "-f", container_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if cleanup_result.returncode != 0:
            logging.warning("Could not delete container export: %s", container_path)

        logging.info("Export saved to: %s", local_path)
        return local_path
