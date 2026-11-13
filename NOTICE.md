# NOTICE · 权利说明与来源

本项目是一个**个人学习性质**的离线水印排版工具，与华为了解技术有限公司、Leica Camera AG
及其关联公司**没有任何关系**，也未获得任何一方的授权、认可或赞助。

仓库内所有素材的来源与权利状态如下，逐条列明，便于权利人与使用者核查。

---

## 1. 代码

| 项目 | 状态 |
|---|---|
| `index.html`（网页版） | 作者原创，MIT 许可 |
| `android/`（WebView 壳） | 作者原创，MIT 许可 |
| `开发文件/tools/`（字体构建脚本） | 作者原创，MIT 许可 |

MIT 许可全文见 [LICENSE](LICENSE)。

---

## 2. 图标与商标

| 素材 | 权利归属 | 本项目的使用方式 |
|---|---|---|
| Leica 红点标（内嵌 PNG） | **Leica Camera AG 的注册商标** | 仅作为水印排版中的示意性符号内嵌，供个人本地使用 |
| “Leica”“徕卡”字样 | **Leica Camera AG 的注册商标** | 仅在说明文字中指示性地提及，用于描述功能 |
| “HUAWEI”“P9”字样 | **华为技术有限公司的商标** | 同上，仅作描述性使用 |

**这不是授权使用，也不构成任何形式的品牌关联。**

如果你要二次分发、商业使用，或用于任何可能被理解为“官方出品”的场景，
请自行把图标替换为自己的素材——软件内「上传」按钮支持 PNG / SVG / JPG / WebP，
内置图标不是必须的。

---

## 3. 字体

`开发文件/fonts/` 下的 `HWLeica*.ttf` / `HWLeicaLight*` / `HWLeicaHand*` 是作者**自行构建**的字体文件：

- 通过轮廓整理、几何构造、字重外扩等方式生成，**没有使用任何字体厂商的字体文件**
- 不含 Leica Camera AG 或任何字体公司的原始字体数据（`name` 表、`OS/2` 表均为本项目自行生成）
- 字形参考自公开可见的印刷样张，属于对可见字形的重新绘制

需要说明的是：**字形设计本身在不同法域的保护程度不同**，若权利人认为存在异议，
请通过文末方式联系，本项目会配合处理。

字体文件随项目以 MIT 许可发布，可自由使用、修改、再分发。

---

## 4. 水印模板与版式

六套模板（白条 / 黑条 / 居中 / 左下 / 大字 / 胶片）是作者按公开可见的水印版式**重新实现**的排版方案：

- 版式属于功能性设计（字号、间距、对齐、留白），未复制任何官方发布的图片文件
- README 中的效果图均由**作者自己拍摄的照片**加本工具导出，非官方样张
- 未使用任何第三方摄影作品

---

## 5. 未分发的素材

`开发文件/reference/` 内的参考图与原始图标素材**不随仓库发布**，已在 `.gitignore` 中排除，
仅存在于作者本机，用于比对外观。

---

## 6. 权利主张与下架流程

如果你认为本仓库的某个文件侵犯了你的权利，请通过 GitHub Issues 联系：

<https://github.com/EllarDomme/HUAWEI_P9_Leica_Watermark_Tool/issues>

请说明：涉及的文件、你的权利依据、期望的处理方式（替换 / 删除 / 标注来源）。

本项目承诺：**收到合理通知后 7 日内处理**，无需走法律程序。

---

## English Summary

This is a personal, non-commercial, offline watermark layout tool. It is **not affiliated with
Huawei Technologies Co., Ltd. or Leica Camera AG**, and is not endorsed or licensed by either.

- **Code**: original work, MIT licensed.
- **Leica red dot mark**: a registered trademark of Leica Camera AG, embedded only as a
  decorative symbol for personal local use. Replace it via the built-in "Upload" button if you
  redistribute.
- **Fonts** (`HWLeica*`): built from scratch by the author; no third-party font files or data
  are included.
- **Templates**: functional layouts re-implemented from publicly visible watermark designs; no
  official image assets are copied.
- **Sample photos**: all shot by the author and processed with this tool.

Rights holders may contact us via GitHub Issues; we will act within 7 days of a reasonable notice.
