# g6-spike —— AntV G6 验证目录

> 独立验证目录，**不参与阶段一原型交付**。用途见 `../G6-A与B对比-20261012.md`。
> **决议（2026-10-12）**：G6 定为**阶段二图谱底座**；是否走「混合路线」届时再定。

## ⚠ 首次使用需先补回库文件

`g6.min.js`（1.38 MB，第三方，MIT）**不入公开仓库**，已被 `.gitignore` 排除。克隆后请先补回，否则页面白屏：

```
curl -sL -o g6.min.js https://unpkg.com/@antv/g6@5.1.1/dist/g6.min.js
```

或 `npm i @antv/g6@5.1.1`，取 `node_modules/@antv/g6/dist/g6.min.js`。

## 怎么打开

双击 `index.html`（`file://` 即可，**无需服务器、无需联网**）。

## 文件

| 文件 | 入库 | 说明 |
|---|---|---|
| `index.html` | ✓ | 验证页（G6 v5 图谱，含 combo 分组框 / 标签分级 / 自写避让 / 屏幕恒定字号） |
| `data.js` | ✓ | 由 `原型/data/ontology.json` 导出：107 类 + 83 条 `subClassOf` + 7 个语义域 |
| `_gen_data.py` | ✓ | `data.js` 生成器（含 8 条防漂移断言，可重跑） |
| `g6.min.js` | ✗ | `@antv/g6@5.1.1` UMD，**1.38 MB**，本地内联（MIT），`.gitignore` 排除 |

## URL 参数

| 参数 | 取值 | 说明 |
|---|---|---|
| `cfg` | `A`（默认）／`B`／`C` | 布局配置，见下表 |
| `all` | `1` | 打开即显示全部标签 |

## 三个布局配置

| cfg | 做法 | 结果 |
|---|---|---|
| **A** | `combo-combined` + 调参（`preventOverlap:true`、`nodeSize`、`combo.nodeSize 340`） | 最接近参考图；**非确定性**，同数据两次运行结果不同 |
| **B** | `combo-combined` 默认参数 | 较差，节点与标签均重叠 |
| **C** | `preset` —— 用我方确定性撒点（黄金角 + 域锚点），G6 只渲染 | **结果稳定**；combo 框尺寸偏小、需再调 `padding` |

## 已验证的能力

- **离线**：`file://` 直开跑通，无 CDN 依赖
- **combo 分组框**：7 个语义域 ✓
- **节点光晕环** `halo` ✓
- **边标签底衬** `labelBackground` ✓
- **节点防重叠**：`preventOverlap + nodeSize` 生效（**默认参数会糊成一团**）
- **标签分级**：总览只标 25 个（16 顶层 + 16 有子类，去重 25），避让后显示 18 个
- **屏幕恒定字号**：配置函数读全局 `ZK`，`labelFontSize = NF / ZK`

## 已知限制

1. **布局非确定性**：cfg A/B 的力导向同数据两次运行结果不同（三次截图 md5 全不同）。cfg C 无此问题。
2. **无内置标签避让**：须自写（本页移植了我方算法）。
3. **Canvas 渲染**：`视觉规范-现代中性-语义域配色` 的 CSS 变量块**不可复用**，须转写 JS 样式对象。
4. **配置样式函数会覆盖数据更新**：`labelText` 必须用静态值 + `updateNodeData` 来控制；函数形式的样式每次绘制重新求值，改不动。
5. **视口 API 名**：`getTransforms()` / `getViewportByCanvas()` / `getZoom()`（**无 `getTranslate()`**）。

## 重新生成数据

改完本体后跑三步（项目根目录下）：

```
python 03-本体模型/_gen_ttl.py
python 03-本体模型/_to_graph_json.py
python 05-产出/原型方案/g6-spike/_gen_data.py
```

`_gen_data.py` 会读 `原型/data/ontology.json` 并覆写本目录的 `data.js`，同时跑 8 条防漂移断言（类数 / 边数 / 域归属 / 16 个顶层类）。
