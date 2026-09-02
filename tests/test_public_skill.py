import base64
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "open-image"
SCRIPT_PATH = SKILL_ROOT / "scripts" / "open_image.py"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
PUBLIC_FILES = (ROOT / "README.md", SKILL_ROOT / "SKILL.md", SCRIPT_PATH)
EXPECTED_STABLE_VERSION = "v1.0.0"
PNG_BYTES = b"\x89PNG\r\n\x1a\nexample"


def load_public_client():
    spec = importlib.util.spec_from_file_location("public_lumenverba_client", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载公开客户端脚本")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PublicSkillPrivacyTests(unittest.TestCase):
    def test_public_files_do_not_include_this_machine_path_or_key_assignment(self):
        forbidden_paths = {str(Path.home()), str(ROOT)}
        for path in PUBLIC_FILES:
            content = path.read_text(encoding="utf-8")
            for forbidden in forbidden_paths:
                self.assertNotIn(forbidden, content, f"公开文件泄露了本机路径: {path}")
            self.assertNotIn("OPEN_IMAGE_API_KEY" + "=", content, f"公开文件包含密钥赋值: {path}")

    def test_tracked_public_text_has_no_machine_specific_paths(self):
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        machine_path_patterns = (
            r"(?i)[a-z]:[\\/]+users[\\/]+[^\\/\s`\"']+",
            r"(?i)(?<!https:)(?<!http:)/users/[^/\s`\"']+",
            r"(?i)/home/[^/\s`\"']+",
        )
        for raw_path in result.stdout.decode("utf-8").split("\0"):
            if not raw_path:
                continue
            relative = Path(raw_path)
            if relative.parts[0] == "tests":
                continue
            if relative.suffix.lower() not in {".md", ".py", ".yml", ".yaml"} and relative.name != "LICENSE":
                continue
            content = (ROOT / relative).read_text(encoding="utf-8")
            for pattern in machine_path_patterns:
                with self.subTest(path=raw_path, pattern=pattern):
                    self.assertIsNone(re.search(pattern, content))


class PortableClientTests(unittest.TestCase):
    def test_text_arguments_preserve_shell_sensitive_characters(self):
        client = load_public_client()

        arguments = client._parser().parse_args([
            "text",
            "--text",
            "“夏日$特惠” O'Reilly `test`",
            "--description",
            '海报包含 "ASCII quotes" 与 $price',
        ])

        self.assertEqual(arguments.text, "“夏日$特惠” O'Reilly `test`")
        self.assertEqual(arguments.description, '海报包含 "ASCII quotes" 与 $price')

    def test_settings_reads_custom_url_and_new_key(self):
        client = load_public_client()

        with patch.dict(
            os.environ,
            {
                "OPEN_IMAGE_API_KEY": "test-key",
                "OPEN_IMAGE_BASE_URL": "https://api.example.com/v1/",
            },
            clear=True,
        ):
            settings = client.Settings.from_environment()

        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.base_url, "https://api.example.com/v1")

    def test_settings_rejects_missing_url_and_key_together(self):
        client = load_public_client()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPEN_IMAGE_BASE_URL.*OPEN_IMAGE_API_KEY"):
                client.Settings.from_environment()

    def test_cli_base_url_overrides_environment_and_accepts_both_positions(self):
        client = load_public_client()

        with patch.dict(
            os.environ,
            {
                "OPEN_IMAGE_API_KEY": "test-key",
                "OPEN_IMAGE_BASE_URL": "https://env.example/v1",
            },
            clear=True,
        ):
            before = client._parser().parse_args(
                ["--base-url", "https://cli.example/v1/", "generate", "--prompt", "测试"]
            )
            after = client._parser().parse_args(
                ["generate", "--base-url", "https://cli.example/v1/", "--prompt", "测试"]
            )
            self.assertEqual(before.base_url, "https://cli.example/v1/")
            self.assertEqual(after.base_url, "https://cli.example/v1/")
            self.assertEqual(client.Settings.from_environment(before.base_url).base_url, "https://cli.example/v1")

    def test_settings_requires_https_default_port_and_clean_url(self):
        client = load_public_client()
        for value in (
            "http://api.example.com/v1",
            "https://api.example.com:8443/v1",
            "https://user:pass@api.example.com/v1",
            "https://api.example.com/v1?token=secret",
            "https://api.example.com/v1#fragment",
        ):
            with self.subTest(value=value):
                with patch.dict(
                    os.environ,
                    {"OPEN_IMAGE_API_KEY": "test-key", "OPEN_IMAGE_BASE_URL": value},
                    clear=True,
                ):
                    with self.assertRaisesRegex(ValueError, "API 地址"):
                        client.Settings.from_environment()

    def test_relative_task_location_uses_custom_base_namespace(self):
        client = load_public_client()
        settings = client.Settings("test-key", "https://api.example.com/custom")

        self.assertEqual(
            client._task_location({"Location": "/custom/tasks/task-1"}, settings),
            "https://api.example.com/custom/tasks/task-1",
        )

    def test_absolute_task_location_is_rejected_even_when_same_origin(self):
        client = load_public_client()
        settings = client.Settings("test-key", "https://api.example.com/custom")

        with self.assertRaisesRegex(RuntimeError, "不安全的任务地址"):
            client._task_location({"Location": "https://api.example.com/custom/tasks/task-1"}, settings)

    def test_missing_key_is_rejected(self):
        client = load_public_client()

        with patch.dict(os.environ, {"OPEN_IMAGE_BASE_URL": "https://api.example.com/v1"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPEN_IMAGE_API_KEY"):
                client.Settings.from_environment()

    def test_creation_network_error_is_not_retried(self):
        client = load_public_client()

        with patch.object(client, "_open_url", side_effect=client.urllib.error.URLError("TLS EOF")) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "TLS 连接失败.*生成状态未知.*未自动重试"):
                client._send("POST", "https://api.lumenverba.cc/v1/images/generations", {})

        self.assertEqual(urlopen.call_count, 1)

    def test_text_prompt_requires_verbatim_readable_text(self):
        client = load_public_client()

        prompt = client.build_text_prompt("夏日特惠", "柠檬汽水海报", "zh-CN", "center", "粗体无衬线")

        self.assertIn('"夏日特惠"', prompt)
        self.assertIn("逐字准确", prompt)
        self.assertIn("清晰可读", prompt)

    def test_read_network_error_retries_once(self):
        client = load_public_client()
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.read.return_value = b"{}"
        first_error = client.urllib.error.URLError(client.ssl.SSLError("private TLS detail"))
        stderr = StringIO()

        with patch.object(client, "_open_url", side_effect=[first_error, response]) as urlopen:
            with redirect_stderr(stderr):
                status, _, body = client._send(
                    "GET",
                    "https://api.lumenverba.cc/v1/tasks/task-1",
                    {},
                )

        self.assertEqual(status, 200)
        self.assertEqual(body, b"{}")
        self.assertEqual(urlopen.call_count, 2)
        self.assertIn("RETRY_NOTICE:", stderr.getvalue())

    def test_read_body_tls_error_retries_once(self):
        client = load_public_client()
        first_response = MagicMock()
        first_response.__enter__.return_value = first_response
        first_response.status = 200
        first_response.headers = {"Content-Type": "application/json"}
        first_response.read.side_effect = client.ssl.SSLError("private TLS detail")
        second_response = MagicMock()
        second_response.__enter__.return_value = second_response
        second_response.status = 200
        second_response.headers = {"Content-Type": "application/json"}
        second_response.read.return_value = b"{}"

        with patch.object(
            client,
            "_open_url",
            side_effect=[first_response, second_response],
        ) as urlopen:
            with redirect_stderr(StringIO()):
                status, _, body = client._send(
                    "GET",
                    "https://api.lumenverba.cc/v1/tasks/task-1",
                    {},
                )

        self.assertEqual(status, 200)
        self.assertEqual(body, b"{}")
        self.assertEqual(urlopen.call_count, 2)

    def test_creation_body_connection_error_is_not_retried(self):
        client = load_public_client()
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.read.side_effect = ConnectionResetError("private connection detail")

        with patch.object(client, "_open_url", return_value=response) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "生成状态未知.*创建请求未自动重试"):
                client._send(
                    "POST",
                    "https://api.lumenverba.cc/v1/images/generations",
                    {},
                )

        self.assertEqual(urlopen.call_count, 1)

    def test_read_timeout_is_not_retried(self):
        client = load_public_client()

        with patch.object(
            client,
            "_open_url",
            side_effect=client.urllib.error.URLError(TimeoutError("private timeout")),
        ) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "网络连接超时.*未自动重试"):
                client._send("GET", "https://api.lumenverba.cc/v1/tasks/task-1", {})

        self.assertEqual(urlopen.call_count, 1)

    def test_authorization_is_not_forwarded_to_a_redirect_target(self):
        client = load_public_client()
        redirected_authorizations: list[str | None] = []

        class TargetHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                redirected_authorizations.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, format, *args):
                pass

        target_server = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
        target_thread = threading.Thread(target=target_server.serve_forever)
        target_thread.start()

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{target_server.server_port}/result")
                self.end_headers()

            def log_message(self, format, *args):
                pass

        redirect_server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        redirect_thread = threading.Thread(target=redirect_server.serve_forever)
        redirect_thread.start()
        try:
            with self.assertRaisesRegex(RuntimeError, "读取图像服务.*未自动重试"):
                client._send(
                    "GET",
                    f"http://127.0.0.1:{redirect_server.server_port}/start",
                    {"Authorization": "Bearer secret"},
                )
        finally:
            redirect_server.shutdown()
            redirect_server.server_close()
            redirect_thread.join()
            target_server.shutdown()
            target_server.server_close()
            target_thread.join()

        self.assertEqual(redirected_authorizations, [])

    def test_network_error_categories_do_not_expose_raw_error_text(self):
        client = load_public_client()

        self.assertEqual(client._network_error_category(client.socket.gaierror(-2, "secret-dns-host")), "DNS 解析失败")
        self.assertEqual(client._network_error_category(client.ssl.SSLError("private TLS detail")), "TLS 连接失败")
        self.assertEqual(client._network_error_category(ConnectionRefusedError("private endpoint")), "连接被拒绝")
        self.assertEqual(client._network_error_category(TimeoutError("private timeout")), "网络连接超时")
        self.assertEqual(client._network_error_category("proxy credentials unavailable"), "代理连接失败")
        self.assertEqual(client._network_error_category("internal host message"), "网络连接失败")

    def test_defaults_are_used_for_a_generation_payload(self):
        client = load_public_client()

        payload = client.build_generation_request("海鸥在码头吃薯条")

        self.assertEqual(payload["model"], "gpt-image-2")
        self.assertEqual(payload["size"], "auto")
        self.assertEqual(payload["quality"], "medium")
        self.assertEqual(payload["n"], 1)
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["partial_images"], 1)

    def test_gpt_image_2_accepts_auto_and_flexible_sizes(self):
        client = load_public_client()
        valid_sizes = (
            "auto",
            "1024x640",
            "1536x512",
            "1280x768",
            "1024x1024",
            "1536x1024",
            "1024x1536",
            "2048x1152",
            "2048x2048",
            "3840x2160",
            "2160x3840",
        )

        for size in valid_sizes:
            with self.subTest(size=size):
                payload = client.build_generation_request("测试", size=size)
                self.assertEqual(payload["size"], size)

    def test_gpt_image_2_accepts_official_quality_values(self):
        client = load_public_client()

        for quality in ("low", "medium", "high", "auto"):
            with self.subTest(quality=quality):
                payload = client.build_generation_request("测试", quality=quality)
                self.assertEqual(payload["quality"], quality)

    def test_custom_sizes_enforce_official_constraints(self):
        client = load_public_client()
        invalid_sizes = (
            ("1024", "WIDTHxHEIGHT"),
            ("1024X1024", "WIDTHxHEIGHT"),
            ("0x1024", "大于 0"),
            ("1025x1024", "16"),
            ("3856x1024", "3840"),
            ("2048x512", "3:1"),
            ("1024x512", "655,360"),
            ("3840x2176", "8,294,400"),
        )

        for size, message in invalid_sizes:
            with self.subTest(size=size):
                with self.assertRaisesRegex(ValueError, message):
                    client.build_generation_request("测试", size=size)

    def test_rejects_non_gpt_image_2_models_and_nonofficial_quality(self):
        client = load_public_client()

        for model in ("gpt-image-1", "gpt-image-1.5", "unknown"):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, "不支持的模型"):
                    client.build_generation_request("测试", model=model)

        for quality in ("standard", "ultra"):
            with self.subTest(quality=quality):
                with self.assertRaisesRegex(ValueError, "不支持的质量"):
                    client.build_generation_request("测试", quality=quality)

    def test_every_command_accepts_the_same_flexible_size(self):
        client = load_public_client()
        commands = (
            ["generate", "--prompt", "测试", "--size", "1280x768"],
            ["edit", "--prompt", "测试", "--reference", "reference.png", "--size", "1280x768"],
            ["text", "--text", "测试", "--description", "海报", "--size", "1280x768"],
            ["batch", "--prompt", "一", "--prompt", "二", "--size", "1280x768"],
        )

        for argv in commands:
            with self.subTest(command=argv[0]):
                self.assertEqual(client._parser().parse_args(argv).size, "1280x768")

    def test_generation_count_is_limited_to_ten(self):
        client = load_public_client()

        arguments = client._parser().parse_args(["generate", "--prompt", "同一提示词"])
        self.assertEqual(arguments.count, 1)
        self.assertEqual(client.build_generation_request("同一提示词", count=10)["n"], 10)
        for invalid in (0, 11):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "生成数量必须在 1 到 10 之间"):
                    client.build_generation_request("同一提示词", count=invalid)

    def test_experimental_size_warns_once_without_changing_success_receipt(self):
        client = load_public_client()
        returned = [Path("C:/generated/experimental.png")]
        stderr = StringIO()

        with tempfile.TemporaryDirectory() as directory:
            result_file = Path(directory) / "result.json"
            with patch.object(client, "generate", return_value=returned):
                with redirect_stdout(StringIO()), redirect_stderr(stderr):
                    exit_code = client.main([
                        "generate",
                        "--prompt",
                        "测试",
                        "--size",
                        "2048x2048",
                        "--result-file",
                        str(result_file),
                    ])
            receipt = json.loads(result_file.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue().count("WARNING: 实验分辨率"), 1)
        self.assertEqual(receipt["status"], "success")
        self.assertEqual(receipt["errors"], [])

    def test_auto_and_regular_sizes_do_not_warn(self):
        client = load_public_client()
        returned = [Path("C:/generated/regular.png")]

        for size in ("auto", "2048x1152"):
            stderr = StringIO()
            with self.subTest(size=size):
                with patch.object(client, "generate", return_value=returned):
                    with redirect_stdout(StringIO()), redirect_stderr(stderr):
                        exit_code = client.main([
                            "generate",
                            "--prompt",
                            "测试",
                            "--size",
                            size,
                        ])
                self.assertEqual(exit_code, 0)
                self.assertNotIn("实验分辨率", stderr.getvalue())

    def test_generation_prompt_is_passed_through_verbatim(self):
        client = load_public_client()
        prompt = "  保留 $price 与 `code`，不要改写。\n"

        self.assertEqual(client.build_generation_request(prompt)["prompt"], prompt)

    def test_missing_key_is_rejected(self):
        client = load_public_client()

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPEN_IMAGE_API_KEY"):
                client.Settings.from_environment()

    def test_text_prompt_requires_verbatim_readable_text(self):
        client = load_public_client()

        prompt = client.build_text_prompt("夏日特惠", "柠檬汽水海报", "zh-CN", "center", "粗体无衬线")

        self.assertIn('"夏日特惠"', prompt)
        self.assertIn("逐字准确", prompt)
        self.assertIn("清晰可读", prompt)

    def test_sse_final_image_is_saved_as_png(self):
        client = load_public_client()
        encoded = base64.b64encode(PNG_BYTES).decode("ascii")
        response = (
            'data: {"type":"image_generation.partial_image","b64_json":"partial"}\n\n'
            f'data: {{"type":"image_generation.completed","b64_json":"{encoded}"}}\n\n'
        ).encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            result = client.save_response_image(response, "text/event-stream", Path(directory))

            self.assertEqual(result.read_bytes(), PNG_BYTES)
            self.assertEqual(result.suffix, ".png")

    def test_json_response_saves_every_returned_image(self):
        client = load_public_client()
        encoded = base64.b64encode(PNG_BYTES).decode("ascii")
        response = json.dumps({"data": [{"b64_json": encoded}, {"b64_json": encoded}]}).encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            results = client.save_response_images(response, "application/json", Path(directory))

        self.assertEqual(len(results), 2)
        self.assertNotEqual(results[0], results[1])

    def test_sse_response_ignores_partials_and_saves_all_completed_images(self):
        client = load_public_client()
        encoded = base64.b64encode(PNG_BYTES).decode("ascii")
        response = (
            'data: {"type":"image_generation.partial_image","b64_json":"partial"}\n\n'
            f'data: {{"type":"image_generation.completed","b64_json":"{encoded}"}}\n\n'
            f'data: {{"type":"image_generation.completed","b64_json":"{encoded}"}}\n\n'
        ).encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            results = client.save_response_images(response, "text/event-stream", Path(directory))

        self.assertEqual(len(results), 2)

    def test_count_command_outputs_successes_and_reports_missing_images(self):
        client = load_public_client()
        returned = [Path("C:/generated/first.png")]
        stdout = StringIO()
        stderr = StringIO()

        with patch.object(client, "generate", return_value=returned):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = client.main(["generate", "--prompt", "同一提示词", "--count", "2"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue().splitlines(), [str(returned[0])])
        self.assertIn("批次项 2 失败", stderr.getvalue())

    def test_batch_starts_every_prompt_before_any_item_finishes(self):
        client = load_public_client()
        started = threading.Barrier(3)
        release = threading.Event()

        def fake_generate(prompt, model, size, quality, count, output_dir):
            started.wait(timeout=2)
            release.wait(timeout=2)
            return [Path(f"C:/generated/{prompt}.png")]

        with patch.object(client, "generate", side_effect=fake_generate):
            with ThreadPoolExecutor(max_workers=1) as harness:
                future = harness.submit(client.generate_batch, ["first", "second"], None, None, None, Path("output"))
                started.wait(timeout=2)
                release.set()
                results = future.result(timeout=2)

        self.assertEqual([item.path.name for item in results], ["first.png", "second.png"])
        self.assertTrue(all(item.error is None for item in results))

    def test_batch_preserves_successes_when_one_prompt_fails(self):
        client = load_public_client()

        def fake_generate(prompt, model, size, quality, count, output_dir):
            if prompt == "first":
                raise RuntimeError("模拟失败")
            return [Path("C:/generated/second.png")]

        with patch.object(client, "generate", side_effect=fake_generate):
            results = client.generate_batch(["first", "second"], None, None, None, Path("output"))

        self.assertEqual(results[0].error, "模拟失败")
        self.assertEqual(results[1].path, Path("C:/generated/second.png"))

    def test_batch_requires_two_to_four_prompts(self):
        client = load_public_client()
        for prompts in (["only"], ["1", "2", "3", "4", "5"]):
            with self.subTest(prompts=prompts):
                with self.assertRaisesRegex(ValueError, "批量提示词数量必须在 2 到 4 之间"):
                    client.generate_batch(prompts, None, None, None, Path("output"))

    def test_batch_cli_outputs_success_paths_and_numbered_errors(self):
        client = load_public_client()
        results = [
            client.BatchItemResult(error="模拟失败"),
            client.BatchItemResult(path=Path("C:/generated/second.png")),
        ]
        stdout = StringIO()
        stderr = StringIO()

        with patch.object(client, "generate_batch", return_value=results):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = client.main(["batch", "--prompt", "first", "--prompt", "second"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue().splitlines(), [str(Path("C:/generated/second.png"))])
        self.assertIn("批次项 1 失败: 模拟失败", stderr.getvalue())

    def test_edit_request_contains_each_reference_image(self):
        client = load_public_client()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.png"
            second = Path(directory) / "second.png"
            first.write_bytes(PNG_BYTES)
            second.write_bytes(PNG_BYTES)

            body, content_type = client.build_edit_request("保留人物姿势", [first, second], "gpt-image-2", "1024x1024", "medium")

        self.assertIn(b'name="image[]"; filename="first.png"', body)
        self.assertIn(b'name="image[]"; filename="second.png"', body)
        self.assertIn("multipart/form-data", content_type)

    def test_edit_request_contains_the_requested_count(self):
        client = load_public_client()
        with tempfile.TemporaryDirectory() as directory:
            reference = Path(directory) / "reference.png"
            reference.write_bytes(PNG_BYTES)
            body, _ = client.build_edit_request("保持主体", [reference], None, None, None, count=4)

        self.assertIn(b'name="n"\r\n\r\n4\r\n', body)

    def test_response_url_is_downloaded_as_png(self):
        client = load_public_client()
        response = json.dumps({"data": [{"url": "https://example.test/image.png"}]}).encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(client, "_send", return_value=(200, {"Content-Type": "image/png"}, PNG_BYTES)) as send:
                result = client.save_response_image(response, "application/json", Path(directory), client.Settings("test-key", "https://api.lumenverba.cc/v1"))

            self.assertEqual(result.read_bytes(), PNG_BYTES)
            self.assertEqual(send.call_args.args[:2], ("GET", "https://example.test/image.png"))

    def test_accepted_task_is_polled_until_png_is_ready(self):
        client = load_public_client()
        encoded = base64.b64encode(PNG_BYTES).decode("ascii")
        pending = json.dumps({"status": "processing"}).encode("utf-8")
        completed = json.dumps({"status": "completed", "data": [{"b64_json": encoded}]}).encode("utf-8")

        responses = [
            (202, {"Location": "/v1/tasks/task-1"}, b""),
            (200, {"Content-Type": "application/json"}, pending),
            (200, {"Content-Type": "application/json"}, completed),
        ]
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(client, "_send", side_effect=responses) as send:
                with patch.object(client.time, "sleep") as sleep:
                    result = client._request_image(
                        "/images/generations",
                        b"{}",
                        "application/json",
                        client.Settings("test-key", "https://api.lumenverba.cc/v1"),
                        Path(directory),
                    )

            self.assertEqual(result.read_bytes(), PNG_BYTES)

        self.assertEqual(send.call_args_list[1].args[:2], ("GET", "https://api.lumenverba.cc/v1/tasks/task-1"))
        self.assertEqual(send.call_count, 3)
        sleep.assert_called_once_with(1)

    def test_accepted_task_rejects_an_insecure_location(self):
        client = load_public_client()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(client, "_send", return_value=(202, {"Location": "http://private.test/task"}, b"")):
                with self.assertRaisesRegex(RuntimeError, "不安全的任务地址"):
                    client._request_image(
                        "/images/generations",
                        b"{}",
                        "application/json",
                        client.Settings("test-key", "https://api.lumenverba.cc/v1"),
                        Path(directory),
                    )

    def test_accepted_task_rejects_external_https_location(self):
        client = load_public_client()

        with self.assertRaisesRegex(RuntimeError, "不安全的任务地址"):
            client._task_location(
                {"Location": "https://attacker.example/v1/tasks/task-1"},
                client.Settings("test-key", "https://api.lumenverba.cc/v1"),
            )

    def test_task_location_rejects_untrusted_url_shapes(self):
        client = load_public_client()
        invalid_locations = (
            "//api.lumenverba.cc/v1/tasks/task-1",
            "https://api.lumenverba.cc:444/v1/tasks/task-1",
            "https://api.lumenverba.cc:0/v1/tasks/task-1",
            "https://user@api.lumenverba.cc/v1/tasks/task-1",
            "https://api.lumenverba.cc/v1/tasks/task-1#fragment",
            "https://api.lumenverba.cc/private/task-1",
            "https://api.lumenverba.cc/v1/%2e%2e/private/task-1",
            "https://api.lumenverba.cc/v1/%2F..%2Fprivate/task-1",
        )

        for location in invalid_locations:
            with self.subTest(location=location):
                with self.assertRaisesRegex(RuntimeError, "不安全的任务地址"):
                    client._task_location(
                        {"Location": location},
                        client.Settings("test-key", "https://api.lumenverba.cc/v1"),
                    )

    def test_rejects_non_https_generated_image_url(self):
        client = load_public_client()
        response = json.dumps({"data": [{"url": "file:///private.png"}]}).encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "必须使用 HTTPS"):
                client.save_response_image(response, "application/json", Path(directory), client.Settings("test-key", "https://api.lumenverba.cc/v1"))

    def test_rejects_relative_and_oversized_reference_images(self):
        client = load_public_client()
        with tempfile.TemporaryDirectory() as directory:
            relative = Path("reference.png")
            with self.assertRaisesRegex(ValueError, "存在的绝对路径"):
                client.build_edit_request("测试", [relative], None, None, None)

            oversized = Path(directory) / "oversized.png"
            oversized.write_bytes(PNG_BYTES + b"x" * (10 * 1024 * 1024))
            with self.assertRaisesRegex(ValueError, "文件过大"):
                client.build_edit_request("测试", [oversized.resolve()], None, None, None)


class PackagedSkillTests(unittest.TestCase):
    def test_documentation_declares_the_runtime_and_versioned_install_contract(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for content in (readme, skill):
            self.assertIn("OPEN_IMAGE_BASE_URL", content)

        for expected in (
            "--output-dir",
            "load_workspace_dependencies",
            "/tree/v1.0.0/skills/open-image",
                        "v1.0.0",
        ):
            self.assertIn(expected, readme + skill)

    def test_documentation_declares_request_retry_boundaries(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for content in (readme, skill):
            self.assertIn("创建请求不会自动重试", content)
            self.assertIn("读取请求", content)
            self.assertIn("最多自动重试 1 次", content)

    def test_repository_includes_mit_license(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertIn("MIT License", license_text)
        self.assertIn("Copyright (c) 2026 yixixi-yahaha", license_text)

    def test_release_metadata_agrees_on_stable_version(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn(EXPECTED_STABLE_VERSION, readme)
        self.assertIn(EXPECTED_STABLE_VERSION, skill)
        self.assertEqual(
            {EXPECTED_STABLE_VERSION},
            set(re.findall(r"v\d+\.\d+\.\d+", readme + skill)),
        )

    def test_ci_workflow_enforces_the_offline_release_gate(self):
        workflow = CI_WORKFLOW.read_text(encoding="utf-8")

        for expected in (
            "windows-latest",
            "ubuntu-latest",
            '"3.11"',
            '"3.14"',
            "python -m unittest discover -s tests -v",
            "python -m unittest discover -v",
            "python -m compileall -q skills tests",
            "open_image.py --help",
            "open_image.py generate --help",
            "open_image.py edit --help",
            "open_image.py text --help",
            "open_image.py batch --help",
            "git diff-tree --check --root --no-commit-id -r HEAD",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, workflow)

        self.assertNotIn("secrets.", workflow)

    def test_readme_documents_clean_uninstall(self):
        content = (ROOT / "README.md").read_text(encoding="utf-8")

        for expected in (
            "## 干净卸载",
            "请卸载 open-image 技能",
            '[Environment]::SetEnvironmentVariable("OPEN_IMAGE_API_KEY", $null, "User")',
            "Remove-Item Env:OPEN_IMAGE_API_KEY",
            "不要显示密钥",
            "不要删除生成的图片或修改其他环境变量",
            "完全退出并重新打开 Codex",
        ):
            self.assertIn(expected, content)

    def test_skill_forbids_inline_python_and_documents_safe_quoting(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for expected in (
            "不得使用 `python -c`",
            "`text --text --description`",
            "PowerShell",
            "单引号写成两个单引号",
        ):
            self.assertIn(expected, content)

    def test_skill_documents_fast_batch_workflow(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for expected in (
            "`--count 1..10`",
            "每批最多 4 项",
            "`batch`",
            "整批生成授权",
            "原样传递",
            "不得进行视觉检查",
            "成功图片",
            "批次项",
            "自动重试 1 次",
            "RETRY_NOTICE:",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, content)

        for forbidden in (
            "多个不同素材不批量提交",
            "主体、场景、风格、构图、光线、准确文字和限制补足提示词",
            "还应视觉检查结果",
            "逐项确认和生成",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_readme_documents_batch_commands_and_limit(self):
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        for expected in (
            "--count",
            "batch --prompt",
            "最多 10 张",
            "2 至 4 个 `--prompt`",
            "并发生成上限为 4 张",
            "部分失败",
        ):
            self.assertIn(expected, content)

    def test_skill_documents_network_recovery_after_an_unknown_state(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for expected in (
            "生成状态未知",
            "自动重试 1 次",
            "RETRY_NOTICE:",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, content)

        for forbidden in ("回复“允许联网”", "重新发送该请求"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)

    def test_skill_documents_secure_first_use_and_all_modes(self):
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for expected in (
            "generate",
            "edit",
            "text",
            "gpt-image-2",
            "auto",
            "medium",
            "Read-Host",
            "AsSecureString",
            "SetEnvironmentVariable",
            "完全退出并重新打开 Codex",
        ):
            self.assertIn(expected, content)

    def test_documentation_declares_flexible_gpt_image_2_sizes(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        for content in (readme, skill):
            for expected in (
                "gpt-image-2",
                "auto",
                "medium",
                "3840",
                "16",
                "3:1",
                "655,360",
                "8,294,400",
                "3,686,400",
                "https://developers.openai.com/api/docs/guides/image-generation#size-and-quality-options",
            ):
                with self.subTest(expected=expected):
                    self.assertIn(expected, content)
            self.assertNotIn("`standard`", content)
            self.assertNotIn("`gpt-image-1`", content)
            self.assertNotIn("`gpt-image-1.5`", content)

        for preset in (
            "1024x1024",
            "1536x1024",
            "1024x1536",
            "2048x2048",
            "2048x1152",
            "3840x2160",
            "2160x3840",
        ):
            with self.subTest(preset=preset):
                self.assertIn(preset, skill)
