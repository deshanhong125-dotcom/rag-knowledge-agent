# 贡献指南

感谢参与改进本项目。

## 开发流程

1. Fork 仓库并从默认分支创建功能分支。
2. 创建 Python 3.11 虚拟环境。
3. 安装 `requirements-dev.txt`。
4. 修改代码并补充对应测试。
5. 本地运行编译检查和测试。
6. 提交说明清晰、范围单一的 Pull Request。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m compileall -q app.py config.py agent api client rag service
.\.venv\Scripts\python.exe -m pytest
```

## 提交前检查

- 不包含 `.env`、API Key、聊天记录、上传文档或 FAISS 索引。
- 新功能有测试或明确说明了手动验证方式。
- API 数据结构变化已同步更新 Schema 和 README。
- 不在自动测试中调用收费的远程模型。

## Commit 建议

建议使用清晰的前缀：

- `feat:` 新功能
- `fix:` 修复问题
- `docs:` 文档修改
- `test:` 测试修改
- `refactor:` 不改变功能的重构
