# NPC 头像与一对一聊天室

三个正式案件和教学案件共 11 个 NPC，各自有一张 720×900 的竖版头像卡。头像采用本地 Blender Eevee 渲染，保持案件的电影光影和深色档案框；职业、外貌和道具根据角色公开资料绘制，例如乘务长制服、医生听诊器、系统工程师权限卡、学生耳机与乐谱、修复师画笔等。

素材位于 `web/src/media/avatars/`，规格清单位于 `docs/npc-avatar-specs.json`。生成脚本为 `tools/render_npc_avatars.py`：

```powershell
python tools/render_npc_avatars.py --manifest docs/npc-avatar-specs.json --work-dir runtime/npc-render --out-dir web/src/media/avatars --samples 48
```

游戏页现在显示“**一对一聊天室**”。切换角色会切换独立的聊天标题、头像、输入草稿和消息历史；发送请求时服务端仍按 `actor_id` 隔离角色授权证词。重新进入本局后，历史消息按角色过滤显示，不会混在一起。

自定义剧本没有对应头像时会安全回退到姓名首字；不会错误复用其他角色图片。头像路径通过 Vite 静态导入生成哈希资源。
