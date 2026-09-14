# 证据影像与消散

为三个预设案件的 24 件证物，以及教学案件的 3 件证物分别制作了 1600×1000 WebP。素材来自本地 Blender/Cycles 三维渲染，使用暖色现场光、冷色环境光、实物材质与轻微胶片颗粒，不调用图像 API。不是实拍照片。

每件画面以 `evidence-art-specs.json` 中的公开描述为依据；时间、编号和文书文字保持与证物一致，不采用尚未授权的分析结论或系统答案。图像为调查氛围与物件展示服务，准确的证据描述仍显示在图像下方。

## 交互

- 首次点击可调查对象：服务端确认发现后自动打开新证物影像。
- 点击已收录的现场对象或证物栏：直接查看，不产生调查行动，不扣调查点。
- 点击收起、背景或按 Escape：图像像素逐步侵蚀，同时生成同色粉尘与碎片，3.2 秒后回到调查。图片本体和粒子共用视口坐标，粉尘不会被图片容器裁切。
- 原生模态对话框限制背景操作，关闭后恢复焦点；隐藏页面暂停时钟。手机限制粒子数量和像素倍率。
- 低动态偏好、缺图或 Canvas 故障时淡出；证据文字仍然可读，关闭始终可用。
- 素材通过 Vite 静态导入生成哈希路径，开发服务与构建版均可访问。私人教学草稿只有证物标题与描述未改变时才复用教学图片；其他自定义证物明确显示尚无影像。

## 再生成

在具有 `bpy`、Pillow、NumPy 的 Python 环境中，从项目根目录运行：

```powershell
python tools/render_evidence.py --manifest docs/evidence-art-specs.json --work-dir runtime/evidence-render --out-dir web/src/media/evidence --samples 64
```

支持 `--only last-train-e1,rain-manor-e1` 仅重新制作指定证物。中文文字使用本机 Windows 字体栅格化到纹理，不分发字体文件。

## 验证

`tests/evidence_browser.py` 必须指向独立测试数据库，覆盖所有 27 张图、首次发现、已收录重开不扣点、粒子像素递减、坐标对齐、关闭按钮/Escape/背景、重复关闭、移动端、运行中切换低动态和缺图降级。

```powershell
$env:PYTHONPATH='.'
$env:E2E_BASE_URL='http://127.0.0.1:8768'
.venv/Scripts/python tests/evidence_browser.py
.venv/Scripts/python tests/browser_smoke.py
.venv/Scripts/python -m pytest -q
```
