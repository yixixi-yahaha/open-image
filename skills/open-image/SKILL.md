---
name: open-image
description: Generate images through a configurable OpenAI-compatible API.
version: 1.0.2
author: yixixi-yahaha (yixixi-yahaha), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Image Generation, OpenAI Compatible, Configurable API]
    related_skills: []
---

# Open Image Skill

当前技能版本：`v1.0.2`。

使用同级 `scripts/open_image.py` 调用用户配置的 OpenAI-compatible Image API。该目录遵循 Agent Skills 开放格式，可由 Codex、Claude Code、Hermes、DeepSeek Harness 或其他支持 `SKILL.md` 的 Agent 加载。客户端只依赖 Python 标准库，不调用旧 MCP 服务，也不使用固定的本机绝对路径。

## When to Use

- 用户明确要求使用 `open-image`。
- 用户明确要求使用可配置的 OpenAI-compatible 生图 API。
- 支持文生图、参考图生图、文字生图和批量生成。
- 普通图片请求、透明背景、抠图或 Alpha 通道验证使用原生 Image-Gen，不强制调用本技能。

## Prerequisites

- Python 3.11 或更高版本；如果宿主 Agent 提供依赖加载工具，可使用该工具获取 Python 运行时。
- `OPEN_IMAGE_API_KEY`：API Bearer 密钥。
- `OPEN_IMAGE_BASE_URL`：API 根地址；必须显式配置，没有默认值。
- API 地址必须是无用户信息、无查询参数和 Fragment 的 HTTPS 443 地址；允许任意 HTTPS 主机，末尾 `/` 会自动去除。
- API 根地址不要求包含 `/v1`；客户端在其后拼接 `/images/generations`、`/images/edits` 和任务路径。

不要在聊天中发送 API 密钥。Windows 可使用 `Read-Host -AsSecureString` 写入用户环境变量；配置后完全退出并重新打开当前 Agent。

PowerShell 配置示例：

```powershell
[Environment]::SetEnvironmentVariable("OPEN_IMAGE_API_KEY", $plainKey, "User")
[Environment]::SetEnvironmentVariable("OPEN_IMAGE_BASE_URL", "https://api.example.com/v1", "User")
```

## Agent and OS Compatibility

- Codex、Claude Code、Hermes、DeepSeek Harness 等宿主只需要加载此目录中的 `SKILL.md`。
- 运行脚本时使用宿主 Agent 对应的 shell/terminal 工具；不要假设 PowerShell、bash 或某个 Agent 专有工具。
- Windows 使用 `python` 或 `py -3`；macOS/Linux 使用 `python3`。路径由 Agent 根据当前系统生成，不要硬编码其他用户的路径。
- 脚本使用 Python 标准库、`pathlib` 和 HTTPS 请求，未使用 POSIX-only 或 Windows-only API。
- 如果宿主 Agent 不支持自动发现 Skill，按 README 的手动安装方式把整个 `open-image` 目录复制到它的 Skill 根目录。

## How to Run

先从当前 `SKILL.md` 的实际位置推导技能目录和同级脚本路径；不要使用固定本机绝对路径。先确认 `python --version` 不低于 3.11，再确定子命令、模型、尺寸、质量、数量、输出目录和唯一绝对回执路径。最终命令中直接执行 `scripts/open_image.py`；不得使用 `python -c`、内联 Python 或动态拼接 Python 源码。

API 地址可以通过 `OPEN_IMAGE_BASE_URL` 或 `--base-url` 提供。`--base-url` 优先，并可放在主命令后或子命令后。密钥只从 `OPEN_IMAGE_API_KEY` 读取。

- 文生图使用 `generate --prompt`；参考图生图使用 `edit --prompt --reference <绝对图片路径>`，可重复传入 `--reference`；指定文字使用 `text --text --description`，并可传 `--language`、`--position`、`--style`。
- 同一提示词可使用 `--count 1` 至 `--count 10`（`--count 1..10`）一次请求生成多个版本，单次最多 10 张。
- 多个不同提示词使用一次 `batch` 命令，构成整批生成授权；每批最多 4 项。脚本按输入顺序返回成功图片，并将失败项作为批次项诊断写入标准错误。
- 普通文生图与参考图编辑原样传递用户提示词；不得进行视觉检查。

PowerShell 中将动态文本参数放在单引号内；参数中的单引号写成两个单引号。`text` 子命令由脚本构造逐字准确约束，不要手动为指定文字添加额外引号。

## Quick Reference

```text
python skills/open-image/scripts/open_image.py --base-url <HTTPS-API根地址> generate --prompt <提示词> --result-file <绝对JSON路径>
python skills/open-image/scripts/open_image.py generate --base-url <HTTPS-API根地址> --prompt <提示词> --count <1-10> --result-file <绝对JSON路径>
python skills/open-image/scripts/open_image.py edit --prompt <提示词> --reference <绝对图片路径> --result-file <绝对JSON路径>
python skills/open-image/scripts/open_image.py text --text <指定文字> --description <画面描述> --result-file <绝对JSON路径>
python skills/open-image/scripts/open_image.py batch --prompt <提示词1> --prompt <提示词2> --result-file <绝对JSON路径>
```

默认模型是 `gpt-image-2`、尺寸是 `auto`、质量是 `medium`。仅支持 `gpt-image-2`；质量可选 `low`、`medium`、`high`、`auto`。尺寸可使用 `auto` 或符合约束的 `WIDTHxHEIGHT`：最长边不超过 `3840px`，两边是 `16px` 的倍数，比例不超过 `3:1`，总像素在 `655,360` 至 `8,294,400` 之间。尺寸与质量约束来源：[OpenAI Image Generation 文档](https://developers.openai.com/api/docs/guides/image-generation#size-and-quality-options)。显式尺寸总像素超过 `3,686,400` 时必须先提示实验分辨率风险，脚本会输出非阻断警告。

常用分辨率档位：`1024x1024`（标准方图）、`1536x1024`（标准横图）、`1024x1536`（标准竖图）、`2048x2048`（2K 方图）、`2048x1152`（2K 横图）、`3840x2160`（4K 横图）、`2160x3840`（4K 竖图）。档位只用于选择，CLI 接收原始 `WIDTHxHEIGHT` 值。

## Procedure

1. 推导脚本路径并确认 Python 版本；完成后不得联网。
2. 解析 API 地址：命令行参数优先于环境变量；地址校验失败或地址、密钥缺失时，在联网前报错。
3. 构造最终命令和唯一的绝对 JSON 回执路径；完成后只执行一次创建命令。
4. 使用 `Authorization: Bearer <OPEN_IMAGE_API_KEY>` 调用兼容接口。创建请求不自动重试。
5. 仅接受服务返回的相对任务地址；基于当前 API 根地址拼接，拒绝绝对 URL、跨主机地址、查询参数、Fragment、非 HTTPS 和非 443 地址。携带 Bearer 的请求拒绝自动重定向。
6. 等待命令完成并取得完整 stdout、stderr 和退出码；不得扫描输出目录或启动第二次生成。
7. 读取并校验回执：必须是版本 `1` 的 JSON；`status` 只能是 `success`、`partial` 或 `error`，`exit_code` 必须是整数，`paths` 必须是 PNG 绝对路径列表，`errors` 必须是字符串列表。逐一验证回执中的每个路径存在且为 PNG。
8. 将所有成功 PNG 逐张交付。stdout 中的每一行都是成功图片的绝对路径；数量不符时，无论多于还是少于预期，都不得丢弃已返回的图片，数量异常只影响状态和诊断，不得造成路径截断。

## Pitfalls

- 未设置 `OPEN_IMAGE_BASE_URL` 或 `OPEN_IMAGE_API_KEY` 时不要猜测默认值，也不要联网；一次性列出所有缺失项。
- 未列入白名单的模型或非官方质量值会在联网前拒绝；不要为此发起 API 请求。
- 创建请求不会自动重试；请求进入网络调用后生成状态未知，不得切换生成方式或把单请求多图改为并发单图。
- 读取请求仅在首次出现 DNS 解析失败、TLS 连接失败、连接被拒绝或代理连接失败时最多自动重试 1 次；超时、连接中途关闭和其他网络错误不重试。成功重试时 stderr 和回执包含 `RETRY_NOTICE:`。
- 创建请求失败后生成状态可能未知；不得把失败创建请求自动重试。
- 不得把密钥写入仓库、回执、日志、URL 或聊天内容。成功图片会逐张交付；不进行视觉检查。

## Verification

离线验证使用 `terminal` 运行：

```text
python -m unittest discover -s tests -v
python -m unittest discover -v
python -m compileall -q skills tests
python skills/open-image/scripts/open_image.py --help
python skills/open-image/scripts/open_image.py generate --help
python skills/open-image/scripts/open_image.py edit --help
python skills/open-image/scripts/open_image.py text --help
python skills/open-image/scripts/open_image.py batch --help
git diff-tree --check --root --no-commit-id -r HEAD
```

真实 API 测试属于发布前人工门禁，不属于 CI。只有用户提供临时低额度地址和密钥后，才生成一张低质量测试 PNG；测试凭据不得输出或保存。
