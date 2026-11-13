# 华为 P9 徕卡水印 · 本地离线复刻版

为华为 P9 而起的水印工具：**任意品牌机型都能用**，填自己的品牌和设备名即可。
单文件网页，双击 `index.html` 就能跑——不上传、不联网、不装任何东西，照片和预设全部留在本机。

> **在线试用**：<https://ellardomme.github.io/HUAWEI_P9_Leica_Watermark_Tool/>
> **下载 APK**：[v1.0.66](https://github.com/EllarDomme/HUAWEI_P9_Leica_Watermark_Tool/releases/latest)（Android 5.0+，548KB）

![华为 P9 原图](docs/images/sample-before.jpg)
![加完水印](docs/images/sample-after.jpg)

*左：华为 P9 原片 ｜ 右：同一张加完水印（白条模板）*

---

## 快速开始

- **直接打开**：双击 `index.html`（Edge / Chrome 均可，`file://` 下就能跑）
- **手机用**：双击 `开发文件/serve.cmd`，同一 Wi-Fi 下用手机访问 `http://电脑IP:8765`
- 把照片拖进左侧，或 `Ctrl+V` 粘贴截图；`Ctrl+O` 打开，`Ctrl+S` 导出

---

## 六套模板

| 模板 | 参照的版式 | 适合 |
|---|---|---|
| **白条** | 华为 P9 + 徕卡红标，白底参数条 | 最通用，像官方样张 |
| **黑条** | 华为 P9 Plus，暗底参数条 + 两行 | 夜景、暗调照片 |
| **居中** | 小米 17 Ultra，红标在上、参数在下 | 竖构图、发小红书 |
| **左下** | SHOT ON XIAOMI 角标 | 不挡画面，街拍纪实 |
| **大字** | LUMO / OPPO 品牌大字 | 作品封面、品牌感 |
| **胶片** | 画框留边，底部排字 | 日系、胶片模拟 |

![白条](docs/images/tpl-bar.jpg)
![黑条](docs/images/tpl-dark.jpg)
![居中](docs/images/tpl-center.jpg)
![左下](docs/images/tpl-corner.jpg)
![大字](docs/images/tpl-wordmark.jpg)
![胶片](docs/images/tpl-film.jpg)

---

## 功能一览

- **署名 / 文案**：支持中文署名、副标题这类文字，位置和字号自动排
- **文字颜色自动判定**：采样照片底部亮度，深色照片自动白字、浅色自动黑字，也能强制白/黑
- **文字黑度**：墨黑 / 深灰两档；白字时自动隐藏
- **三档深浅**：设备名、日期、参数各有独立滑杆；白 / 墨黑 / 深灰三套参数**互相独立保存**，
  切换颜色不会冲掉之前调好的数值
- **外边框**：照片外圈加一道白边，0–2.5% 可调
- **字体**：默认（系统）/ DIN 工业 / 等宽 / 衬线 / 人文 / HarmonyOS / **徕卡复刻 / 徕卡复刻·细体 / 徕卡复刻·糙体**
  除「默认」外全部内嵌，手机与电脑渲染一致；中文仍走系统字体。内嵌后 `index.html` 约 1MB（六套徕卡字重）
- **徕卡复刻字体**：按刻字样张逐字重绘，73 个字形，大写统一 700 高、基线归零；
  细体为常规内缩，糙体带逐字倾斜与笔画收放；三套均含 400/700 两档，含 265 组字偶距
- **条高 / 字号 / 图标大小 / 垂直位置 / 图标间距**：全部按图宽百分比缩放，4K 导出和预览比例一致
- **预览可缩放**：点预览图进入全屏，双指缩放、拖动、双击切换；工具栏有 − / 百分比 / +
- **原图尺寸导出**：JPEG（质量可调）或 PNG，文件名加 `-wm`

---

## 导出到哪里

点「导出」会先弹出系统的**另存为**对话框：

- 自己选目录、改文件名，确认后写入；默认文件名是 `原文件名-wm.jpg`（PNG 格式则 `.png`）
- 浏览器会记住上次保存的目录，下次默认停在那里
- 点「取消」= 不导出，什么都不会写
- 老浏览器不支持这个对话框时，会自动退回普通下载，文件进系统「下载」文件夹
- **尺寸**可选：原图 / 长边 3000 / 长边 2048（越小越省空间，老手机也更快）

---

## 支持与限制

- 支持 **JPG / PNG / WebP**
- **HEIC 不支持**（浏览器原生解不了），iPhone 照片建议先在相册导出为 JPG
- **微信传图会抹掉 EXIF**——所以参数必须能手改，这也是为什么做成了输入框
- 加水印只改像素，**不会写回文件 EXIF**；显示的时间/地点和水印是两回事
- 导出上限 8000px 宽，正常照片不会碰到

---

## 安卓老机型

- 需要 **Chromium 55+** 的浏览器；系统自带「HTML 查看器」通常禁用 JS，点了没反应
- 实测可用：**X浏览器**（包名 `com.mmbox.xbrowser.pro`）
- 用 `file://` 打开时：导出会进 `Download` 文件夹；**预设可能存不住**（安卓浏览器对本地存储的限制）
- 1200 万像素导出比较吃内存，建议把「尺寸」设为**长边 2048**

---

## 隐私

- 无任何网络请求，断网也能用
- 照片只在浏览器内存里解码、绘制，关掉页面即释放
- 预设和图标存在本机 `localStorage`，不上传

---

## 关于品牌标识与免责声明

本项目内嵌了 Leica 红点标识，**仅用于个人学习与本地水印排版演示**。

- “Leica” 及相关标识是 **Leica Camera AG** 的注册商标，本项目与该公司**无任何关联**，也未获其授权
- 请勿将本工具用于商业用途、批量生成冒充官方样张的图片，或任何可能误导他人的场景
- 如需公开分发修改版，请自行评估商标使用风险，或把图标替换为自己的素材（「上传」按钮支持 PNG / SVG）
- 仓库内不含任何第三方摄影作品；`开发文件/reference/` 中的参考图仅用于本地对照，未上传

---

## 文件结构

```
P9徕卡水印工具/
├─ index.html          # 双击这个就能用：EXIF 解析 + 6 套模板 + 预设
├─ LICENSE             # MIT
├─ README.md           # 本说明
└─ 开发文件/            # 用户不需要碰的部分
   ├─ serve.cmd        # 可选：起本地服务，方便手机访问
   ├─ demo.jpg         # 带 EXIF 的示例照片
   ├─ preview/         # 过程截图
   └─ reference/       # 参考素材（不发布）
```

> `开发文件/reference/`（参考网图与徕卡标原图）**不随仓库发布**，已在 `.gitignore` 中排除。

## 想改版式

`index.html` 里搜 `function drawBar` / `drawCenter` / `drawCorner` / `drawWordmark` / `drawFilm`，
每个模板的尺寸都是 `图宽 × 系数`，改一个数字就能调整比例。
配色、字号、间距都在对应函数顶部几行。

## 自测脚本

`开发文件/tests/` 里有一套基于 CDP 的自动化测试（Node 22+，用本机 Edge 无头模式）：

```powershell
# 先起一个带调试端口的无头 Edge，然后
node 开发文件/tests/cdp_test.mjs
```

覆盖：画布渲染、EXIF 解析、六套模板、八种字体、时间精度、PNG/JPEG 状态、
滑杆与开关、图标切换、文字颜色、预设保存与重载恢复、导出尺寸与编码。

> 这是桌面 Chromium 环境的测试；真机（P9 / 安卓 WebView）仍需人工验收。

## 常见问题：推送失败

如果 `git push` 报 `Connection was reset` / `Proxy CONNECT aborted`，多半是网络到 `github.com:443` 不稳定，可以：

```powershell
# 走系统代理或换一个网络重试
git -c http.proxy=http://127.0.0.1:端口 push origin main
```

仓库本身不依赖任何代理配置，正常网络下直接 `git push` 即可。

## Android APK

`android/` 是一个极简 WebView 壳，把 `index.html` 打进 APK，导出的图由原生代码直接写入相册
（`Pictures/P9Watermark`），完全绕开浏览器对 `file://` 页面的保存限制。

- 包名 `com.ellardomme.p9watermark`，最低 Android 5.0
- 返回键：先关浮层，主界面双击退出
- 体积约 548KB（6 套模板 + 六套内嵌徕卡字重 + 全套离线依赖）

重新打包（需要 JDK 与 Android SDK，脚本里写死了本机路径，换机器改 `build.ps1` 顶部的 `$sdk`）：

```powershell
powershell -ExecutionPolicy Bypass -File android\build.ps1
```

脚本会自动把根目录的 `index.html` 复制进 `assets/`，然后依次执行
aapt2 → javac → d8 → 加 dex → zipalign → apksigner。
