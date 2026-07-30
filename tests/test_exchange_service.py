import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from src.exchangeService import ExchangeService


class ExchangeServiceTests(unittest.TestCase):
    def test_read_sysml_files_returns_only_sorted_sysml_files(self):
        with tempfile.TemporaryDirectory() as directory:
            input_dir = Path(directory)
            (input_dir / "second.sysml").write_text("", encoding="utf-8")
            (input_dir / "first.sysml").write_text("", encoding="utf-8")
            (input_dir / "ignored.txt").write_text("", encoding="utf-8")

            service = ExchangeService("upload.sh", directory)

            self.assertEqual(
                service.read_sysml_files(),
                [
                    str(input_dir / "first.sysml"),
                    str(input_dir / "second.sysml"),
                ],
            )

    def test_read_sysml_files_returns_empty_for_missing_directory(self):
        service = ExchangeService("upload.sh", "missing-input-directory")

        with self.assertLogs(level="ERROR"):
            self.assertEqual(service.read_sysml_files(), [])

    def test_send_to_api_copies_export_from_configured_container(self):
        upload_result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=">> Export finished\nExport path: /home/sysml/export.json\n",
            stderr="",
        )
        copy_result = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"SYSML_KERNEL_CONTAINER": "custom-kernel"}),
            patch(
                "src.exchangeService.subprocess.run",
                side_effect=[upload_result, copy_result],
            ) as run,
        ):
            upload_script = str(Path(directory) / "uploadSysml.sh")
            service = ExchangeService(upload_script, directory)

            export_path = service.sendToApi(["model.sysml"])

        self.assertEqual(export_path, str(Path(directory) / "export.json"))
        self.assertEqual(
            run.call_args_list[1].args[0],
            [
                "docker",
                "cp",
                "custom-kernel:/home/sysml/export.json",
                str(Path(directory) / "export.json"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
