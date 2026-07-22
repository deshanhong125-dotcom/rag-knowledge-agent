# 安全策略

## 敏感信息

不要提交以下内容：

- `.env`、`.evn` 或任何真实 API Key
- `data/chat_history.json`
- `data/file_registry.json`
- `data/uploads/` 中的用户文档
- `data/faiss_db/` 中的索引文件
- `data/backups/` 和 `data/trash/`

如果密钥曾出现在提交、日志或截图中，请先在服务提供商处撤销并重新生成；从最新提交删除密钥并不能将它从 Git 历史移除。

## FAISS 索引

本项目使用 LangChain FAISS 的本地持久化功能，其中 `index.pkl` 使用 Python pickle。只加载本项目在可信环境中生成的索引，不要下载并加载来源不明的索引文件。

## 部署范围

当前版本没有用户认证、租户隔离、上传配额和速率限制，默认面向本机学习和受信任网络。面向互联网部署前至少应增加：

- 身份认证和权限控制
- HTTPS
- 文件大小、数量和类型限制
- 请求速率限制
- 日志脱敏和数据保留策略

## 报告漏洞

请不要在公开 Issue 中附带 API Key、私人文档或完整聊天记录。仓库启用 GitHub Private Vulnerability Reporting 后，优先通过该渠道报告安全问题。
