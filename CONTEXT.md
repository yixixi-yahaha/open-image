# Open Image 项目上下文

本项目是一个可安装的 Codex Skill，名称为 `open-image`，用于调用兼容 OpenAI Images API 的 HTTPS 服务。

## 配置契约

- API 密钥变量：`OPEN_IMAGE_API_KEY`。
- API 根地址：`OPEN_IMAGE_BASE_URL`，也可用 CLI 参数 `--base-url` 覆盖。
- 优先级：CLI 参数 > 环境变量；没有默认地址。
- 地址必须是 HTTPS、默认 443 端口、无用户信息、查询参数或 Fragment；允许任意 HTTPS 主机并自动去除末尾 `/`。
- 异步任务地址只接受服务返回的相对地址，并基于当前 API 根地址拼接。

## 功能边界

保留文生图、参考图编辑、文字生图、批量生成、尺寸/质量校验、PNG 保存、结果回执和原有重试边界。创建请求不自动重试；读取请求只对指定的临时网络错误重试一次。

## 目录

- `skills/open-image/SKILL.md`：安装后由 Codex 读取的技能说明。
- `skills/open-image/scripts/open_image.py`：仅依赖 Python 标准库的客户端。
- `tests/`：不联网的单元和回归测试。
- `docs/adr/`：项目决策记录。
- `docs/glossary/`：项目术语。

## 发布

使用 `main` 作为唯一发布源。首个正式版本为 `v1.0.0`，发布前必须通过完整离线门禁；真实 API 冒烟测试只在维护者提供临时凭据后手动执行。测试凭据不得写入代码、文档、回执或日志。
