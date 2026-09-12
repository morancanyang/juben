# 内容包 v1.0

官方剧本由 `api/seed_content.py` 以冻结版本发布；作者草稿通过 `/api/v1/author/drafts` 保存，质检通过后才允许冻结。玩家浏览器只收到 `public_script()` 投影和本局已发现的证物。

## 规则边界

- `CasePackage`、`Condition` 和效果使用严格 Pydantic Schema；未知字段、无效 ID 和超长文本会被拒绝。
- 条件只允许 `always`、`all`、`any`、`not`、`hasEvidence`、`analyzed`、`presented`、`trust`、`phase`、`time`；不执行 `eval`、JavaScript、SQL 或网络地址。
- 冻结版本不可原地修改；进行中的会话固定 `script_version_id`。
- 事实、证词、玩家笔记和系统答案分层保存，角色回答不返回 `answer`、隐藏证物或其他角色私密资料。
- 质检报告的 `blocker` 会阻止冻结；建议级问题要求作者人工试玩成功、误判和替代路径。

## 验证

```powershell
$env:PYTHONPATH='.'
.venv/Scripts/python -m api.migrate
.venv/Scripts/python -m pytest tests/test_game.py -q
```
