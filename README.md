# Open Image

可安装的 Codex Skill，用于调用任意兼容 OpenAI Images API 的 HTTPS 服务生成图片。技能内置仅依赖 Python 标准库的客户端，不依赖 MCP 常驻服务、本机固定路径或额外 Python 包。

## 安装

需要 Codex 和 Python 3.11 或更高版本。首个稳定版安装命令固定到 `v1.0.0`：

```powershell
npx.cmd skills add "https://github.com/yixixi-yahaha/open-image/tree/v1.0.0/skills/open-image" -g -y
```

安装完成后，重新打开 Codex。技能会在用户明确要求使用 `open-image`，或明确要求使用可配置的 OpenAI-compatible 生图 API 时启用；普通图片请求不强制使用本技能。

## 配置

技能没有默认 API 地址，必须显式设置 API 根地址。地址必须是无用户信息、无查询参数和 Fragment 的 HTTPS 443 地址；允许任意 HTTPS 主机。末尾 `/` 会自动去除，路径不要求必须包含 `/v1`。

使用 PowerShell 安全设置 API 密钥，不要在聊天中发送密钥：

```powershell
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$secureKey = Read-Host "请输入 Open Image API 密钥" -AsSecureString
$plainKey = [System.Net.NetworkCredential]::new("", $secureKey).Password
[Environment]::SetEnvironmentVariable("OPEN_IMAGE_API_KEY", $plainKey, "User")
Remove-Variable plainKey
```

设置 API 地址：

```powershell
[Environment]::SetEnvironmentVariable("OPEN_IMAGE_BASE_URL", "https://api.example.com/v1", "User")
```

也可以在每次调用时传入 `--base-url`。命令行参数优先于 `OPEN_IMAGE_BASE_URL`；它既可以放在主命令后，也可以放在子命令后。两项配置都缺失时，客户端会一次性列出缺失的配置项并在联网前退出。客户端只读取 `OPEN_IMAGE_API_KEY`，不兼容旧的 `LUMENVERBA_API_KEY`。

API 使用以下接口结构和 Bearer 认证：

```text
POST /images/generations
POST /images/edits
GET  /tasks/{task_id}
Authorization: Bearer <OPEN_IMAGE_API_KEY>
```

异步任务地址必须是服务返回的相对地址；客户端会基于当前 API 根地址拼接，并拒绝绝对地址、跨主机地址、查询参数、Fragment、非 HTTPS 或非 443 地址。携带认证的请求拒绝自动重定向。

完全退出并重新打开 Codex 后，环境变量配置才会对新进程生效。

## 功能

- 文生图：根据提示词创建图片。
- 参考图生图：使用一张或多张本地参考图片生成新图。
- 文字生图：要求图片完整呈现指定、清晰可读的文字。
- 批量生成：同一提示词使用 `--count 2` 至 `--count 10`（单次最多 10 张）；不同提示词使用 `batch --prompt`，每批 2 至 4 个 `--prompt`，并发生成上限为 4 张。

默认模型为 `gpt-image-2`、尺寸为 `auto`、质量为 `medium`。仅支持 `gpt-image-2`；质量可选 `low`、`medium`、`high`、`auto`。

尺寸可使用 `auto` 或自定义 `WIDTHxHEIGHT`。自定义尺寸最长边不得超过 `3840px`，两边必须是 `16px` 的倍数，长短边之比不得超过 `3:1`，总像素必须在 `655,360` 到 `8,294,400` 之间。显式尺寸总像素超过 `3,686,400` 时属于官方标记的实验范围。约束来源见 [OpenAI Image Generation 文档](https://developers.openai.com/api/docs/guides/image-generation#size-and-quality-options)。

## 使用示例

```powershell
python "skills/open-image/scripts/open_image.py" --base-url "https://api.example.com/v1" generate --prompt '雨夜中的上海街头，电影感摄影，霓虹灯倒映在路面上。'
python "skills/open-image/scripts/open_image.py" generate --base-url "https://api.example.com/v1" --prompt '同一提示词' --count 2
python "skills/open-image/scripts/open_image.py" edit --prompt '保留主体姿态并更换背景' --reference 'C:\images\reference.png'
python "skills/open-image/scripts/open_image.py" text --text '夏日特惠' --description '柠檬汽水海报' --language 'zh-CN' --position 'center' --style '粗体无衬线'
python "skills/open-image/scripts/open_image.py" batch --prompt '清晨薄雾中的江南水乡' --prompt '火星基地内的植物温室'
```

动态提示词、指定文字和描述在 PowerShell 中放在单引号内；参数中的单引号写成两个单引号。普通文生图和参考图编辑原样传递提示词，文字模式只由脚本追加逐字准确约束。

- `--output-dir`：生成 PNG 的输出目录；默认使用当前目录下的 `output`。
- `--result-file`：写入结果回执的绝对 JSON 路径。

## 结果与重试

脚本成功时标准输出只返回生成 PNG 的绝对路径，每行一张；失败诊断写入标准错误。使用 `--result-file` 可写入版本为 `1` 的 JSON 回执，包含 `status`、`exit_code`、`paths` 和 `errors`。`status` 为 `success`、`partial` 或 `error`。

创建请求不会自动重试，因为网络失败时生成状态可能未知，重试可能造成重复生成或重复计费。读取请求仅在首次出现 DNS 解析失败、TLS 连接失败、连接被拒绝或代理连接失败时最多自动重试 1 次；超时和其他网络错误不重试。成功读取会在标准错误和回执中记录 `RETRY_NOTICE:`。批次部分失败时保留并输出全部成功图片。

## 干净卸载

如需通过 Codex 请求清理，请发送：`请卸载 open-image 技能，并删除 OPEN_IMAGE_API_KEY 和 OPEN_IMAGE_BASE_URL。不要显示密钥，不要删除生成的图片或修改其他环境变量。`

删除技能目录不会清除环境变量。如需清理配置，请在 PowerShell 中运行：

```powershell
[Environment]::SetEnvironmentVariable("OPEN_IMAGE_API_KEY", $null, "User")
[Environment]::SetEnvironmentVariable("OPEN_IMAGE_BASE_URL", $null, "User")
Remove-Item Env:OPEN_IMAGE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:OPEN_IMAGE_BASE_URL -ErrorAction SilentlyContinue
```

不要显示密钥，不要删除生成的图片或修改其他环境变量。清理后完全退出并重新打开 Codex。

## 维护者验证

每个发布标签前从 `main` 分支运行离线发布门禁：

```powershell
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

真实 API 冒烟测试不是 CI 的一部分。发布前使用临时、低额度的 API 地址和密钥生成一张低质量 PNG，并验证返回文件；测试凭据不得写入仓库、日志或回执。
