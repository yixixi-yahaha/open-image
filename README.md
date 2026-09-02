<div align="center">

<h1>Open Image</h1>

<p>遵循 Agent Skills 开放格式 · 跨 Agent、跨平台的 OpenAI-compatible 图像生成 Skill</p>

<p>
  <a href="https://github.com/yixixi-yahaha/open-image/actions/workflows/ci.yml"><img src="https://github.com/yixixi-yahaha/open-image/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI Status"></a>
  <a href="https://github.com/yixixi-yahaha/open-image/releases"><img src="https://img.shields.io/github/v/release/yixixi-yahaha/open-image?label=release" alt="Latest Release"></a>
  <a href="https://github.com/yixixi-yahaha/open-image/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-3776AB.svg" alt="Python 3.11+"></a>
  <a href="https://agentskills.io/"><img src="https://img.shields.io/badge/Agent%20Skills-compatible-7C3AED.svg" alt="Agent Skills compatible"></a>
</p>

</div>

> [!IMPORTANT]
> `open-image` 不内置 API 地址或 API 密钥。首次使用前只需配置 `OPEN_IMAGE_API_KEY` 和 `OPEN_IMAGE_BASE_URL`；密钥不要粘贴到聊天或命令行中。

## 快速开始

| 步骤 | 做什么 | 入口 |
| --- | --- | --- |
| **1** | 安装 Skill | [对话安装](#方式一通过对话安装) 或 [命令安装](#方式二使用命令安装) |
| **2** | 配置 API | [Windows 向导](#windowspowershell-交互式配置) 或 [macOS/Linux 向导](#macosterminal-交互式配置) |
| **3** | 开始生图 | [Agent 对话](#在-agent-对话中使用) 或 [CLI](#使用-cli) |

<details>
<summary><strong>最快的命令安装方式</strong></summary>

```bash
npx skills add "https://github.com/yixixi-yahaha/open-image/tree/v1.0.2/skills/open-image" --global --yes
```

</details>

## 目录

- [你将配置什么](#你将配置什么)
- [安装](#安装)
  - [通过对话安装](#方式一通过对话安装)
  - [使用命令安装](#方式二使用命令安装)
- [最直观的首次配置](#最直观的首次配置)
  - [Windows PowerShell](#windowspowershell-交互式配置)
  - [macOS/Linux](#macosterminal-交互式配置)
- [使用方式](#使用方式)
- [功能和参数](#功能和参数)
- [结果、回执和重试](#结果回执和重试)
- [干净卸载](#干净卸载彻底清理)
- [发布与维护者验证](#发布与维护者验证)

---

## 你将配置什么

只需要两项配置：

| 配置 | 用途 | 是否必需 |
| --- | --- | --- |
| `OPEN_IMAGE_API_KEY` | `Authorization: Bearer` API 密钥 | 是 |
| `OPEN_IMAGE_BASE_URL` | API 根地址 | 是 |

API 根地址可以是任意 OpenAI-compatible HTTPS 服务，例如：

```text
https://api.example.com/v1
https://your-provider.example.com/openai
```

客户端会在根地址后追加：

```text
POST /images/generations
POST /images/edits
GET  /tasks/{task_id}
```

地址规则：

- 必须使用 `https://`。
- 只能使用默认 HTTPS 端口 `443`。
- 不允许用户名、密码、查询参数或 Fragment。
- 允许任意 HTTPS 主机。
- 末尾 `/` 会自动去除。
- 不强制要求地址包含 `/v1`。
- 没有默认地址；没有配置时客户端会在联网前报错。

## 安装

安装前准备：

- 安装 Python 3.11 或更高版本。
- 安装 Node.js 和 npm，以便使用 `npx skills`；如果目标 Agent 没有该安装器，也可以手动复制目录。
- 不要把 API 密钥粘贴到聊天、README、命令历史或 Git 仓库中。

### 方式一：通过对话安装

这种方式适用于支持从 GitHub 读取 Agent Skill 的 Codex、Claude Code、Hermes、DeepSeek Harness 等 Agent。新建一个对话，发送下面这段话：

```text
请从 https://github.com/yixixi-yahaha/open-image/tree/v1.0.2/skills/open-image 安装 open-image Skill。
它是一个跨平台、兼容 OpenAI Images API 的生图 Skill，请保留整个 skills/open-image 目录及其 scripts/open_image.py 文件。
安装完成后请告诉我 Skill 文件的位置，不要要求我在聊天中发送 API 密钥。
```

如果 Agent 支持直接使用本地仓库，也可以发送：

```text
请加载当前项目 skills/open-image/SKILL.md，并把它作为 open-image Skill 使用。不要修改 Skill 文件，也不要要求我在聊天中发送 API 密钥。
```

安装后重新启动 Agent 或新建会话，再进行配置和测试。

### 方式二：使用命令安装

#### 使用 `npx skills` 安装到自动识别的 Agent

```bash
npx skills add "https://github.com/yixixi-yahaha/open-image/tree/v1.0.2/skills/open-image" --global --yes
```

只安装到指定 Agent 时，可以使用 `--agent`。具体 Agent 名称取决于当前版本的安装器：

```bash
npx skills add "https://github.com/yixixi-yahaha/open-image/tree/v1.0.2/skills/open-image" --global --agent claude-code --yes
npx skills add "https://github.com/yixixi-yahaha/open-image/tree/v1.0.2/skills/open-image" --global --agent codex --yes
```

先查看当前安装器支持的 Agent：

```bash
npx skills add --help
```

`npx skills` 支持从固定版本标签安装；使用 `v1.0.2` 可以避免安装命令随着 `main` 分支变化。

#### 手动安装：适用于任何支持 `SKILL.md` 的 Agent

先克隆仓库：

```bash
git clone --branch v1.0.2 --depth 1 https://github.com/yixixi-yahaha/open-image.git
```

需要复制的完整目录是：

```text
open-image/skills/open-image
```

不要只复制 `SKILL.md`，因为脚本位于同级的 `scripts/open_image.py`。

常见的用户级目录：

| Agent | 用户级 Skill 目录 | 项目级 Skill 目录 |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/open-image/` | `.claude/skills/open-image/` |
| Hermes | `$HERMES_HOME/skills/open-image/`；未设置时通常为 `~/.hermes/skills/open-image/` | 按 Hermes 当前项目配置的 Skill 根目录 |
| Codex | 推荐使用 `npx skills add` | 推荐使用 `npx skills add` 或 Agent 配置的 skills 根目录 |
| DeepSeek Harness | 使用 Harness 设置中的 Skill 根目录 | 使用 Harness 设置中的项目 Skill 根目录 |

macOS/Linux 手动复制示例：

```bash
mkdir -p "$HOME/.claude/skills"
cp -R open-image/skills/open-image "$HOME/.claude/skills/open-image"
```

Hermes 用户级复制示例：

```bash
mkdir -p "${HERMES_HOME:-$HOME/.hermes}/skills"
cp -R open-image/skills/open-image "${HERMES_HOME:-$HOME/.hermes}/skills/open-image"
```

Windows PowerShell 手动复制示例：

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force ".\open-image\skills\open-image" "$HOME\.claude\skills\open-image"
```

如果 DeepSeek Harness 或其他 Agent 使用不同的 Skill 根目录，请把完整的 `open-image` 文件夹复制到它的用户级或项目级 Skill 目录，并确保最终结构类似：

```text
<agent-skills-root>/open-image/SKILL.md
<agent-skills-root>/open-image/scripts/open_image.py
```

## 最直观的首次配置

配置的目标是让 Agent 调用脚本时能同时读取：

```text
OPEN_IMAGE_API_KEY
OPEN_IMAGE_BASE_URL
```

推荐先使用下面对应系统的交互式配置。API 密钥会在输入时隐藏，不需要把密钥写在命令行中。

### Windows：PowerShell 交互式配置

打开 PowerShell，完整粘贴并执行：

```powershell
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$baseUrl = Read-Host "请输入 API 根地址（例如 https://api.example.com/v1）"
$secureKey = Read-Host "请输入 API 密钥（输入内容不会显示）" -AsSecureString
$plainKey = [System.Net.NetworkCredential]::new("", $secureKey).Password

[Environment]::SetEnvironmentVariable("OPEN_IMAGE_BASE_URL", $baseUrl.TrimEnd('/'), "User")
[Environment]::SetEnvironmentVariable("OPEN_IMAGE_API_KEY", $plainKey, "User")
$env:OPEN_IMAGE_BASE_URL = $baseUrl.TrimEnd('/')
$env:OPEN_IMAGE_API_KEY = $plainKey

Remove-Variable baseUrl, secureKey, plainKey
Write-Host "配置完成。请完全退出并重新打开 Agent。"
```

这个向导会同时完成：

1. 交互输入 API 地址。
2. 隐藏输入 API 密钥。
3. 保存为当前 Windows 用户环境变量。
4. 让当前 PowerShell 进程也可以立即使用。

如果你的 Agent 已经在运行，必须完全退出并重新打开它，才能读取新的用户环境变量。

验证配置是否存在时只检查变量名，不要输出密钥值：

```powershell
[Environment]::GetEnvironmentVariable("OPEN_IMAGE_BASE_URL", "User")
$keyExists = -not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("OPEN_IMAGE_API_KEY", "User"))
Write-Host "API 密钥已配置: $keyExists"
Remove-Variable keyExists
```

### macOS：Terminal 交互式配置

打开 Terminal，完整粘贴并执行：

```bash
read -r -p "请输入 API 根地址（例如 https://api.example.com/v1）: " OPEN_IMAGE_BASE_URL
OPEN_IMAGE_BASE_URL="${OPEN_IMAGE_BASE_URL%/}"
read -r -s -p "请输入 API 密钥（输入内容不会显示）: " OPEN_IMAGE_API_KEY
printf '\n'
export OPEN_IMAGE_BASE_URL OPEN_IMAGE_API_KEY
printf '当前 Terminal 已完成配置。请从这个 Terminal 启动 Agent，或按下方方式保存到 shell 配置后重启 Agent。\n'
```

如果希望以后打开 Terminal 自动拥有这两项环境变量，建议让 Agent 或系统密码管理工具负责注入密钥；不要把明文密钥直接写进 README 或普通脚本。只保存 API 地址时可以执行：

```bash
printf '\nexport OPEN_IMAGE_BASE_URL=%q\n' 'https://api.example.com/v1' >> "$HOME/.zshrc"
```

API 密钥建议通过 macOS Keychain、企业密钥管理器或 Agent 的安全环境变量机制注入。配置完成后，重新打开 Terminal 和 Agent。

### macOS/Linux：通用 shell 配置

如果当前 shell 不是 zsh，把上面的 `export` 语句放到对应 shell 的启动配置中。一次性会话配置可以使用：

```bash
read -r -p "API 根地址: " OPEN_IMAGE_BASE_URL
OPEN_IMAGE_BASE_URL="${OPEN_IMAGE_BASE_URL%/}"
read -r -s -p "API 密钥: " OPEN_IMAGE_API_KEY
printf '\n'
export OPEN_IMAGE_BASE_URL OPEN_IMAGE_API_KEY
```

### 不想保存配置时：单次调用

也可以只在一次调用中设置地址，并让密钥由当前环境提供：

```bash
OPEN_IMAGE_BASE_URL='https://api.example.com/v1' \
python3 skills/open-image/scripts/open_image.py generate \
  --prompt '生成一张清晨薄雾中的江南水乡' \
  --quality low
```

Windows PowerShell：

```powershell
$env:OPEN_IMAGE_BASE_URL = "https://api.example.com/v1"
python "skills/open-image/scripts/open_image.py" generate --prompt '生成一张清晨薄雾中的江南水乡' --quality low
```

如果地址同时通过环境变量和命令行参数提供，命令行参数优先：

```text
--base-url > OPEN_IMAGE_BASE_URL
```

`--base-url` 可以放在主命令后，也可以放在子命令后。

## 使用方式

### 在 Agent 对话中使用

安装并配置后，可以直接对 Agent 说：

```text
请使用 open-image 生成一张雨夜中的上海街头，电影感摄影，霓虹灯倒映在路面上。
```

参考图生图：

```text
请使用 open-image，以 C:\images\product.png 作为参考图，生成一张白色背景的电商产品主图，保留产品外形和颜色。
```

macOS/Linux 示例：

```text
请使用 open-image，以 $HOME/images/character.png 作为参考图，生成一张同一角色在雪山木屋前的插画。
```

文字生图：

```text
请使用 open-image 生成一张中文饮料海报，图片中必须清晰完整地显示“夏日特惠”，文字位于画面中央，使用醒目的粗体字。
```

批量生成：

```text
请使用 open-image 生成 4 张不同版本的图片：雨夜中的上海街头，电影感摄影，霓虹灯倒映在路面上。
```

多个不同提示词：

```text
请使用 open-image 同时生成两张图片：
1. 清晨薄雾中的江南水乡，写实摄影风格。
2. 火星基地内的植物温室，科幻概念艺术风格。
```

### 使用 CLI

文生图：

```bash
python3 skills/open-image/scripts/open_image.py \
  --base-url 'https://api.example.com/v1' \
  generate \
  --prompt '清晨薄雾中的江南水乡，写实摄影风格' \
  --quality medium \
  --size 1536x1024 \
  --output-dir "$HOME/open-image-output" \
  --result-file "$HOME/open-image-result.json"
```

Windows PowerShell：

```powershell
python "skills/open-image/scripts/open_image.py" `
  --base-url "https://api.example.com/v1" `
  generate `
  --prompt '清晨薄雾中的江南水乡，写实摄影风格' `
  --quality medium `
  --size 1536x1024 `
  --output-dir "$HOME\open-image-output" `
  --result-file "$HOME\open-image-result.json"
```

参考图编辑：

```bash
python3 skills/open-image/scripts/open_image.py \
  edit \
  --prompt '保留主体姿态并更换为极简工作室背景' \
  --reference '$HOME/images/reference.png' \
  --result-file "$HOME/open-image-edit-result.json"
```

指定文字：

```bash
python3 skills/open-image/scripts/open_image.py \
  text \
  --text '夏日特惠' \
  --description '柠檬汽水促销海报，明亮清爽的夏日配色' \
  --language 'zh-CN' \
  --position 'center' \
  --style '粗体无衬线' \
  --result-file "$HOME/open-image-text-result.json"
```

同一提示词生成多个版本：

```bash
python3 skills/open-image/scripts/open_image.py \
  generate \
  --prompt '雨夜中的上海街头，电影感摄影' \
  --count 4 \
  --result-file "$HOME/open-image-batch-result.json"
```

多个不同提示词批量生成：

```bash
python3 skills/open-image/scripts/open_image.py \
  batch \
  --prompt '清晨薄雾中的江南水乡，写实摄影风格' \
  --prompt '火星基地内的植物温室，科幻概念艺术风格' \
  --result-file "$HOME/open-image-multi-result.json"
```

PowerShell 中，动态文字、提示词和路径建议放在单引号内；如果参数中有单引号，将单引号写成两个单引号。不要把 API 密钥直接作为命令行参数。

## 功能和参数

- 文生图：`generate --prompt`。
- 参考图生图：`edit --prompt --reference`，可重复传入多个参考图。
- 文字生图：`text --text --description`。
- 同一提示词多图：`--count 1` 至 `--count 10`。
- 不同提示词：`batch --prompt`，每批 2 至 4 个 `--prompt`，并发生成上限为 4 张；部分失败时保留并输出全部成功图片。
- 单次最多 10 张：同一提示词使用 `--count 2` 至 `--count 10`。
- 默认模型：`gpt-image-2`。
- 默认尺寸：`auto`。
- 默认质量：`medium`。
- 质量：`low`、`medium`、`high`、`auto`。

自定义尺寸必须满足：

- 最长边不超过 `3840px`。
- 宽和高都是 `16px` 的倍数。
- 长宽比不超过 `3:1`。
- 总像素在 `655,360` 到 `8,294,400` 之间。
- 显式尺寸总像素超过 `3,686,400` 时允许执行，但会输出实验分辨率警告。

尺寸约束参考：[OpenAI Image Generation 文档](https://developers.openai.com/api/docs/guides/image-generation#size-and-quality-options)。

## 结果、回执和重试

脚本成功时标准输出每行返回一张生成 PNG 的绝对路径。`--result-file` 会写入版本为 `1` 的 JSON：

```json
{
  "version": 1,
  "status": "success",
  "exit_code": 0,
  "paths": ["绝对 PNG 路径"],
  "errors": []
}
```

`status` 只能是 `success`、`partial` 或 `error`。返回数量不符时仍保留并交付所有已返回图片，状态标记为 `partial`，不会按请求数量截断路径。

创建请求不会自动重试，因为网络错误后生成状态可能未知，重试可能导致重复生成或重复计费。读取请求仅在首次出现 DNS 解析失败、TLS 连接失败、连接被拒绝或代理连接失败时最多自动重试 1 次；超时和其他网络错误不重试。成功重试会在标准错误和回执中记录 `RETRY_NOTICE:`。

## 干净卸载（彻底清理）

### 对话卸载

在任意支持该 Skill 的 Agent 中发送：

```text
请彻底卸载 open-image Skill（请卸载 open-image 技能）：
1. 删除 open-image Skill 安装目录；
2. 删除用户级 OPEN_IMAGE_API_KEY 和 OPEN_IMAGE_BASE_URL 环境变量；
3. 不要显示或记录 API 密钥；
4. 不要删除生成的图片；
5. 不要修改其他环境变量或其他 Skill；
6. 最后只报告 Skill 目录和这两项变量是否仍存在，并提醒我完全退出并重新打开 Agent。
```

如果 Agent 不具备修改本机环境变量的权限，请让它只报告路径，并使用下面的系统命令清理变量。

### Windows PowerShell 卸载

```powershell
$ErrorActionPreference = "Stop"

Remove-Item -Recurse -Force "$HOME\.claude\skills\open-image" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$HOME\.hermes\skills\open-image" -ErrorAction SilentlyContinue

[Environment]::SetEnvironmentVariable("OPEN_IMAGE_API_KEY", $null, "User")
[Environment]::SetEnvironmentVariable("OPEN_IMAGE_BASE_URL", $null, "User")
Remove-Item Env:OPEN_IMAGE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:OPEN_IMAGE_BASE_URL -ErrorAction SilentlyContinue

$keyStillExists = -not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("OPEN_IMAGE_API_KEY", "User"))
$urlStillExists = -not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable("OPEN_IMAGE_BASE_URL", "User"))
Write-Host "OPEN_IMAGE_API_KEY 仍存在: $keyStillExists"
Write-Host "OPEN_IMAGE_BASE_URL 仍存在: $urlStillExists"
Remove-Variable keyStillExists, urlStillExists
```

如果通过对话卸载，要求 Agent 不要显示密钥；不要删除生成的图片或修改其他环境变量；如果你通过其他 Agent 目录安装，还要删除对应的 `open-image` 文件夹。不要删除 `output` 或其他生成图片目录。

### macOS/Linux 卸载

下面命令删除 Claude Code 和 Hermes 的常见用户级目录，并清理当前 shell：

```bash
rm -rf "$HOME/.claude/skills/open-image"
rm -rf "${HERMES_HOME:-$HOME/.hermes}/skills/open-image"
unset OPEN_IMAGE_API_KEY OPEN_IMAGE_BASE_URL
```

如果你把配置写入了 `~/.zshrc`、`~/.bashrc` 或其他 shell 启动文件，请只删除其中与 `OPEN_IMAGE_API_KEY`、`OPEN_IMAGE_BASE_URL` 对应的行，不要改动其他配置。清理后请完全退出并重新打开 Codex 或其他 Agent。

## 发布与维护者验证

安装命令固定到版本标签。发布新版本时，从已经验证的 `main` 创建不可变标签，并更新 README 和 `SKILL.md` 中的版本号。

离线验证：

```bash
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

真实 API 冒烟测试不是 CI 的一部分。只有使用临时、低额度地址和密钥时才执行；测试凭据不得写入代码、文档、日志、回执或 GitHub Actions。

## 许可证

本项目沿用 MIT License，并保留原版权声明。
