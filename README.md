# 夜半卷宗 · 单人 AI 互动推理 MVP

这是根据产品需求文档、技术与实施方案、实施计划实现的首个可运行版本。产品边界保持单人调查：没有联机、好友、私聊、社区、排行榜或多人房间。

## 已实现

- 三本冻结预设剧本：雨夜山庄、末班列车、无声回响。
- 游客会话、账号注册/登录、游客升级迁移、自动存档、历史记录、导出与删除。
- 场景搜索、证物分析/出示/组合、角色信任/警觉、追问建议、对话搜索和调查行动日志。
- 三本案件及教学案件共 27 张独立电影风格证物影像；点击现场或证物自动展开，关闭时图像逐渐粒子消散，详见 [证据影像](docs/evidence-images.md)。
- 11 个 NPC 独立职业头像框与一对一聊天室；切换角色时保留各自输入草稿和对话历史，详见 [NPC 头像与聊天室](docs/npc-avatars.md)。
- 角色回应的生成 → 批评 → 修订 → 审核后语义块交付；SSE 游标恢复、取消、失败重试。
- 授权投影与信息隔离：搭档只读已发现证物、已授权笔记和已交付证词。
- 事实/陈述/推断/假设笔记、IndexedDB 离线草稿、调查意图联网后重新核验、版本冲突副本。
- 固定答案、关键证据覆盖、隐藏线索、多结局和分章真相揭示。
- 私人剧本工作台：结构化信息、JSON 导入/导出、作者草稿、规则质检、冻结版本、教学案件试玩。
- 本地演示 Provider；可通过后端环境变量切换 DeepSeek/OpenAI，密钥不进入前端。
- FastAPI + SQLAlchemy + SQLite 本地 / PostgreSQL Docker + React/Vite PWA 壳。
- 深夜调查室登录/注册入口，使用本地 Blender 制作的旧证据纸与咖啡桌面图，无需图像 API。真实认证成功后整张图片粒子消散；支持游客、跳过、低动态偏好和故障降级，详情见 [电影开场认证界面](docs/cinematic-auth.md)。

## 本地启动（Windows PowerShell）

```powershell
cd C:\Users\33864\Desktop\aijuben
.venv\Scripts\Activate.ps1
$env:PYTHONPATH='.'
.venv\Scripts\python -m api.migrate
Start-Process .venv\Scripts\python.exe -ArgumentList '-m','uvicorn','api.main:app','--host','127.0.0.1','--port','8000'
cd web
npm run dev
```

打开 `http://127.0.0.1:5173`。默认 SQLite 文件为 `runtime/game.db`，复制 `.env.example` 为 `.env` 可设置 Provider。没有密钥时保持 `PROVIDER=mock` 即可完整通关。

## Docker

```powershell
copy .env.example .env
$env:POSTGRES_PASSWORD='change-this-in-a-secret-store'
docker compose up --build
```

生产模式要求 PostgreSQL、HTTPS 与 `COOKIE_SECURE=true`。应用启动不隐式迁移数据库；容器命令显式执行 `api.migrate`。正式部署前请替换示例密码和允许来源。

## 验证

```powershell
$env:PYTHONPATH='.'
.venv\Scripts\python -m pytest tests/test_game.py -q
cd web; npm run build
```

测试覆盖三本剧本成功和错误结局、替代调查路径、幂等与并发、权限/IDOR/CSRF、SSE 恢复与取消、笔记冲突、游客升级、作者冻结、删除、断网意图和 500 条防泄露回归样本。

文档中“首 token ≤ 2 秒”和“审核后正文 ≤ 12 秒”是需要在真实 Provider、目标地区和部署规格上基准测试的产品目标；本地演示模式仅用于功能验证，不声称已达到远程模型延迟指标。
