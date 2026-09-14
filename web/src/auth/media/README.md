# 夜半卷宗 · 旧证据纸与咖啡桌面图

最新场景：深色木桌上一张略微破旧的纸质证据，纸上醒目、清晰地印着「夜半卷宗」四个大字，旁边是一杯咖啡。暖台灯、墨绿暗部、真实材质与克制的悬疑气氛。

素材现已通过本地 Blender/Cycles 三维渲染生成，完全不需要 API Key 或图像 API。文件为本目录 casebook-desk.webp，1600×1408，约 170 KB。这是原创三维渲染图，不是实拍或扩散模型生成。

场景与纹理生成源在 tools/render_casebook.py。使用 bpy 5.2、Pillow 与 NumPy，中文标题从本机 SimSun 字体栅格化，不分发字体文件。最终 PNG 保留完整画面，WebP 为融入界面暗部而加入少量边缘透明羽化；动画和图片使用相同 alpha。

## 单图接入

- 文件名：casebook-desk.webp 或 casebook-desk.png，放在本目录。
- 推荐 1600×1408，约 8:7 构图；WebP 高质量导出，目标不超过 1 MB。
- 大标题必须准确为「夜半卷宗」，不需要额外副标题。文字随图片一起粒子化。
- 正常不透明图片即可，无需抠图或干净背景。
- 证据纸和咖啡杯居中，边缘自然进入暗部；手机完整显示图片。
- 不出现凶手、毒物、人物、答案、品牌、水印和其他剧透。
- 放入素材后执行 npm run build，Vite 自动打包本地文件，不使用外链。

认证成功后整张画面从边缘与亮部向内部侵蚀，原图像素形成缓慢向右上漂移的粉尘。3.2 秒消散完成后调查总览才可操作。跳过、低动态偏好及故障安全淡出继续保留。

## 兼容旧素材

旧 scene.webp 也作为整张图片消散。不存在完整图片时，仍兼容同构图的 room.webp 干净背景与 evidence.png RGBA 主体方案；仅旧模式保留照片背景、只消散主体。

开发测试页的几何图片只验证不透明整图及透明主体两种引擎路径，不能作为正式主视觉交付。

## 视觉构思参考（实际使用本地建模与光线追踪）
Use case: photorealistic-natural.
Asset type: cinematic opening image for the single-player mystery game 夜半卷宗.
Primary request: a dark wooden investigation desk holding one worn paper evidence document and a cup of coffee beside it.
Scene/backdrop: quiet late-night investigation room; softly blurred rain-streaked window in deep shadow.
Subject: the aged cream document is the main focal point, with slightly frayed edges, small folds, subtle stains and realistic paper fibres. A ceramic coffee cup sits beside the document, holding dark coffee, with natural reflections and realistic contact shadows.
Text (verbatim): "夜半卷宗". Exactly these four Chinese characters, large, legible, dark ink in a vintage Song/Ming serif typeface, prominently across the evidence paper. The characters are 夜 / 半 / 卷 / 宗 in this order. No other readable text.
Composition/framing: 1600x1408 landscape, near 8:7; oblique overhead cinematic close-up. Both the whole paper and cup fit comfortably in frame, with dark negative space around them. The title is easy to read with a shallow perspective, not distorted.
Lighting/mood: narrow warm tungsten lamp light from upper left, restrained low-key suspense, realistic analogue-film atmosphere, shallow depth of field without blurring the title.
Color palette: near-black, desaturated forest-green shadows, dark brown wood, aged paper cream, muted warm copper highlights.
Materials/textures: real wood grain, paper wrinkles, subtle aged ink, ceramic glaze, dark coffee surface; believable proportions and lighting.
Avoid: neon, cyberpunk, purple gradients, illustration, cartoon styling, extra objects, people, weapons, blood, spoilers, gibberish Chinese, watermarks, logos and UI elements.
