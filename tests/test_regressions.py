import base64
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "open-image"
SCRIPT_PATH = SKILL_ROOT / "scripts" / "open_image.py"
PNG_BYTES = b"\x89PNG\r\n\x1a\nexample"


def load_client():
    spec = importlib.util.spec_from_file_location("copy_lumenverba_client", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载副本客户端脚本")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def mock_json_response(payload, status=200, headers=None):
    response = MagicMock()
    response.__enter__.return_value = response
    response.status = status
    response.headers = headers or {"Content-Type": "application/json"}
    response.read.return_value = json.dumps(payload).encode("utf-8")
    return response


class ResultCountRegressionTests(unittest.TestCase):
    def test_extra_images_are_all_delivered_and_marked_partial(self):
        client = load_client()
        returned = [Path("C:/generated/first.png"), Path("C:/generated/extra.png")]
        stdout = StringIO()
        stderr = StringIO()

        with tempfile.TemporaryDirectory() as directory:
            result_file = (Path(directory) / "result.json").resolve()
            with patch.object(client, "generate", return_value=returned):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = client.main([
                        "generate",
                        "--prompt", "测试",
                        "--count", "1",
                        "--result-file", str(result_file),
                    ])
            receipt = json.loads(result_file.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue().splitlines(), [str(path) for path in returned])
        self.assertIn("超出请求数量", stderr.getvalue())
        self.assertEqual(receipt["paths"], [str(path) for path in returned])
        self.assertTrue(any("超出请求数量" in error for error in receipt["errors"]))

    def test_fewer_images_are_all_delivered_and_marked_partial(self):
        client = load_client()
        returned = [Path("C:/generated/only.png")]
        stdout = StringIO()
        stderr = StringIO()

        with tempfile.TemporaryDirectory() as directory:
            result_file = (Path(directory) / "result.json").resolve()
            with patch.object(client, "generate", return_value=returned):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = client.main([
                        "generate",
                        "--prompt", "测试",
                        "--count", "2",
                        "--result-file", str(result_file),
                    ])
            receipt = json.loads(result_file.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue().splitlines(), [str(returned[0])])
        self.assertIn("批次项 2 失败", stderr.getvalue())
        self.assertEqual(receipt["paths"], [str(returned[0])])
        self.assertEqual(receipt["status"], "partial")


class RetryRegressionTests(unittest.TestCase):
    def test_retry_reuses_the_same_request_fields(self):
        client = load_client()
        response = mock_json_response({})
        failures = [
            client.urllib.error.URLError(client.ssl.SSLError("private TLS detail")),
            response,
        ]

        with patch.object(client, "_open_url", side_effect=failures) as urlopen:
            with redirect_stderr(StringIO()):
                client._send("GET", "https://api.lumenverba.cc/v1/tasks/task-1", {"X-Test": "value"})

        first_call, second_call = urlopen.call_args_list
        first_request = first_call.args[0]
        second_request = second_call.args[0]
        self.assertEqual(first_request.full_url, second_request.full_url)
        self.assertEqual(first_request.get_method(), second_request.get_method())
        self.assertEqual(first_request.data, second_request.data)
        self.assertEqual(dict(first_request.header_items()), dict(second_request.header_items()))
        self.assertEqual(first_call.kwargs, second_call.kwargs)

    def test_real_retry_notice_is_written_to_the_receipt(self):
        client = load_client()
        encoded = base64.b64encode(PNG_BYTES).decode("ascii")
        accepted = mock_json_response({}, status=202, headers={"Location": "/v1/tasks/task-1"})
        completed = mock_json_response({"data": [{"b64_json": encoded}]})
        first_error = client.urllib.error.URLError(client.ssl.SSLError("private TLS detail"))
        stdout = StringIO()
        stderr = StringIO()

        with tempfile.TemporaryDirectory() as directory:
            result_file = (Path(directory) / "result.json").resolve()
            with patch.dict(os.environ, {"OPEN_IMAGE_API_KEY": "test-key", "OPEN_IMAGE_BASE_URL": "https://api.lumenverba.cc/v1"}, clear=True):
                with patch.object(client, "_open_url", side_effect=[accepted, first_error, completed]):
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        exit_code = client.main([
                            "generate",
                            "--prompt", "测试",
                            "--output-dir", directory,
                            "--result-file", str(result_file),
                        ])
            receipt = json.loads(result_file.read_text(encoding="utf-8"))

        notice = "RETRY_NOTICE: 首次调用失败：TLS 连接失败；已自动重试 1 次。"
        self.assertEqual(exit_code, 0)
        self.assertIn(notice, stderr.getvalue())
        self.assertEqual(receipt["errors"], [notice])


class CommandModeReceiptTests(unittest.TestCase):
    def test_edit_text_and_batch_write_success_receipts(self):
        client = load_client()
        modes = ("edit", "text", "batch")

        with tempfile.TemporaryDirectory() as directory:
            for mode in modes:
                with self.subTest(mode=mode):
                    result_file = (Path(directory) / f"{mode}.json").resolve()
                    returned = [Path(directory) / f"{mode}.png"]
                    if mode == "edit":
                        command = [
                            "edit", "--prompt", "测试", "--reference", "C:/reference.png",
                            "--result-file", str(result_file),
                        ]
                        target = "edit"
                        value = returned
                    elif mode == "text":
                        command = [
                            "text", "--text", "测试", "--description", "测试",
                            "--result-file", str(result_file),
                        ]
                        target = "generate"
                        value = returned
                    else:
                        command = [
                            "batch", "--prompt", "first", "--prompt", "second",
                            "--result-file", str(result_file),
                        ]
                        target = "generate_batch"
                        value = [client.BatchItemResult(path=returned[0]), client.BatchItemResult(path=returned[0])]

                    with patch.object(client, target, return_value=value):
                        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                            exit_code = client.main(command)
                    receipt = json.loads(result_file.read_text(encoding="utf-8"))

                    self.assertEqual(exit_code, 0)
                    self.assertEqual(receipt["status"], "success")
                    self.assertEqual(receipt["exit_code"], 0)


class SkillContractTests(unittest.TestCase):
    def test_skill_requires_all_returned_images_on_count_mismatch(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("无论多于还是少于预期，都不得丢弃已返回的图片", content)
        self.assertIn("数量异常只影响状态和诊断，不得造成路径截断", content)


if __name__ == "__main__":
    unittest.main()
