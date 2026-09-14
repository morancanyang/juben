# 电影开场认证界面

入口沿用 Vite 主页面：未认证显示调查室；已有有效 Cookie 会话直接进入游戏。登录、注册和游客均使用现有 FastAPI 接口，不改变身份认证契约。

## 代码职责

- `web/src/auth/AuthForm.tsx`：真实认证请求、用户名/密码/确认密码校验、显示密码、超时、重复提交保护与卸载取消。
- `EvidenceScene.tsx`：摄影底图、透明证物、独立 HTML 证物标签；缺图与图片加载错误处理。
- `particleEngine.ts`：图像颜色采样、距离场与连续噪声侵蚀、计数排序像素更新、不同生命周期的粉尘和碎片。
- `AuthExperience.tsx`：认证成功后的转场控制、镜头推进、跳过、焦点恢复、低动态和运行时降级。
- `motion.ts`：页面可见时间时钟；隐藏标签页暂停、卸载清理。
- `App.tsx`：会话状态、已有会话恢复、调查总览准备；转场结束前主页面 inert，阻止提前操作。

认证成功后，图像解体与粉尘出生共用 0.4–2.35 秒进度；2.4 秒开始场景交叠，3.2 秒完成。对话框或动画异常不会撤销已经成功的认证。缺少可用图片、无法读取 Canvas 或低动态偏好时，使用 0.55 秒淡出。

## 本地生成的主视觉

主视觉已经由本地 Blender/Cycles 生成并接入，是三维渲染图，不是实拍或扩散模型生成。无需 OPENAI_API_KEY 或任何图像 API。纸面准确印有「夜半卷宗」，旁边是咖啡杯，使用暗木桌、暖台灯、折痕、磨损纸边、釉面与真实光照阴影。

产品素材为 `web/src/auth/media/casebook-desk.webp`，1600×1408，约 165 KB。画面内容与图内标题一起粒子消散，不需要透明抠图。生成源为 `tools/render_casebook.py`，依赖 bpy 5.2、Pillow、NumPy；参数 `--work-dir` 和 `--out` 指定中间目录与 PNG 输出，自动导出 WebP。中文字体从本机 SimSun 栅格化，不分发字体文件。测试场景仍使用独立几何夹具，生产构建不包含夹具。

## 正式运行

```powershell
cd C:\Users\33864\Desktop\aijuben\web
npm run build
```

正在运行的 FastAPI 静态服务读取 `web/dist`。当前本机游戏地址为 `http://127.0.0.1:8765`。

## 可重复浏览器验证

使用独立测试数据库，避免创建测试档案影响个人进度。以下各服务在独立终端启动。

终端 A（首次运行先迁移）：

```powershell
cd C:\Users\33864\Desktop\aijuben
$env:DATABASE_URL='sqlite:///C:/Users/33864/Desktop/aijuben/runtime/auth-e2e-20260912.db'
$env:APP_ENV='test'
$env:PROVIDER='mock'
$env:ALLOWED_ORIGINS='http://127.0.0.1:8766,http://127.0.0.1:5175'
.venv\Scripts\python -m api.migrate
.venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port 8766
```

终端 B：

```powershell
cd C:\Users\33864\Desktop\aijuben\web
$env:VITE_API_TARGET='http://127.0.0.1:8766'
npm run dev -- --port 5175 --strictPort
```

终端 C：

```powershell
cd C:\Users\33864\Desktop\aijuben
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python tests/auth_browser.py
$env:E2E_BASE_URL='http://127.0.0.1:8766'
.venv\Scripts\python tests/browser_smoke.py
.venv\Scripts\python -m pytest -q
```

测试使用系统 Chrome 与 Python Playwright。认证测试报告默认写入 `test-results/auth/`；设置 `E2E_OUTPUT_DIR` 可更改输出目录。

手动重复粒子：打开 `http://127.0.0.1:5175/tests/auth-lab.html?scene` 测试整图消散；移除 `?scene` 测试旧透明主体模式。点击游客入口或登录；退出后可再次触发。页面顶部明确标注几何测试夹具。支持 `?broken-image` 与 `?opaque-image` 测试旧模式降级；模拟系统低动态偏好检查淡出。此入口只由 Vite 开发服务提供，生产构建不包含测试入口。

桌面测试 1440×1000，手机测试 390×844 和软键盘模拟 390×470。手机性能指标来自桌面 Chrome 仿真，不代表真实低端手机的帧率；正式摄影到位后仍需验收素材衔接与真机表现。
