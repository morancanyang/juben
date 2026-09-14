# 三起案件封面更新

已使用本地 Pillow 绘图与分层合成生成三张原创电影化封面，无 API Key、无外链、无素材下载：

- train.webp：末班列车驶入漆黑隧道，月光、隧道拱架、车窗灯光与湿润铁轨。
- manor.webp：暴雨中的山庄，雷光、山体轮廓、亮起的窗户与雨幕。
- station.webp：极地观测站，极夜、极光、雪原、天线和观测舱。

文件位于 `web/src/media/covers/`，尺寸均为 1600×900 WebP。`web/src/media/covers.ts` 通过 Vite 本地打包，`Layout.tsx` 将图片绑定到 train/manor/station 三个 cover 值；旧 CSS 几何剪影只在图片缺失时作为后备。

生成源：`tools/render_case_covers.py`。运行：

```powershell
cd C:\Users\33864\Desktop\aijuben
C:\Users\33864\Documents\Codex\2026-09-12\xi-s\work\render-env\Scripts\python.exe tools\render_case_covers.py
```

这套绘图使用渐变、透视结构、雨线/星点、光晕、颗粒、暗角和电影色彩分级实现；图片中的剧本标题仍由 HTML 排版，保证可读性和无障碍。
