# 截图复刻 H5

使用当前 Agent，将网页或移动端 H5 截图复刻为可编辑、可本地运行的前端代码。

适合复刻已有页面、根据多张截图还原交互状态，以及对照截图逐步调整布局与视觉细节。

## 能做什么

- 还原截图中的文字、布局、间距、颜色、图片和固定区域。
- 将同一页面的多张截图连接成可操作的状态，例如展开评论、切换标签或打开弹层。
- 优先复用提供的图片素材，必要时从截图中裁切头像、照片和插画。
- 生成真实的 HTML、CSS 和交互逻辑，页面文字与控件保持可编辑。
- 在浏览器中预览，并通过同尺寸截图对比检查差异。

新建 H5 默认使用 HTML / CSS / JavaScript 和本地资源；已有项目则优先沿用原框架与目录结构。

## 安装

将仓库内容放入 Codex 的技能目录，文件夹命名为 `screenshot-to-code-agent`。

macOS / Linux 默认路径示例：

```bash
git clone https://github.com/hxx2001/screenshot_to_code_agent-skill.git \
  ~/.codex/skills/screenshot-to-code-agent
```

如果配置了自定义 `CODEX_HOME`，请将技能放到对应的 `skills/screenshot-to-code-agent` 目录。目标目录已有同名技能时，请先检查内容，避免覆盖自己的修改。

## 使用

在支持本地技能的 Agent 环境中，上传截图并调用：

```text
使用 $screenshot-to-code-agent 将这些截图复刻成本地可运行的 H5，
保留原图文字和布局，实现可见交互，并截图对比校准。
```

已有项目可以补充具体要求：

```text
使用 $screenshot-to-code-agent 在当前 React 项目里复刻这两张截图。
第一张是默认状态，第二张是展开评论后的状态。
沿用现有组件和样式方案，实现两个状态之间的切换。
```

尽量提供清晰的原始截图、目标页面尺寸，以及可复用的图片或字体。多张截图请说明它们是独立页面，还是同一页面的不同状态。

## 工作流程

1. **分析截图**：确认内容区域、尺寸、文字和状态差异。
2. **整理素材**：复用提供的资源，裁切必要的图片素材并记录来源。
3. **实现页面**：编写可编辑的前端代码，连接核心交互。
4. **预览校准**：在浏览器中运行，以相同尺寸截图对比并修正差异。
5. **交付结果**：提供源码、本地预览入口和 `design-qa.md` 检查记录。

检查记录应注明实际验证的状态与交互，以及仍存在的视觉差异。环境无法截图时，应明确标注尚未完成视觉验证。

## 目录结构

```text
screenshot-to-code-agent/
├── README.md
├── SKILL.md                         # 技能入口与工作流程
├── agents/
│   └── openai.yaml                  # 显示名称与默认调用提示
├── scripts/
│   └── agent_adapter.py             # 本地辅助脚本
├── references/
│   ├── upstream.md                  # 来源与适配说明
│   └── upstream-manifest.json       # 上游版本与文件校验值
└── vendor/
    ├── LICENSE                      # 上游许可证
    ├── codegen/utils.py             # HTML 提取工具
    └── prompts/
        ├── system_prompt.py
        └── create/image.py
```

## 辅助脚本

需要 Python 3.10 或更新版本；`crop` 和 `compare` 额外依赖 Pillow。脚本辅助 Agent 完成文件处理，本身不负责识图或生成网页。

| 命令 | 用途 |
| --- | --- |
| `prepare` | 根据截图路径和所选技术栈生成任务说明 |
| `crop` | 按像素坐标裁切素材，输出来源清单 |
| `finalize` | 从生成文本中提取完整 HTML |
| `compare` | 生成原图与渲染截图的并排图和叠加图 |

`compare` 要求两张图片像素尺寸一致，不会自动缩放，也不会给出未经验证的还原度评分。具体参数与示例见 [SKILL.md](SKILL.md)。

## 使用边界

- 需要具备看图、文件操作能力的 Agent；浏览器预览与截图验证还需要相应工具。
- 复刻质量取决于截图清晰度、素材完整性、字体和运行环境，不保证像素级一致。
- 页面中的关注、发布、分享等交互默认在本地演示，不代表接入真实业务服务。
- 页面以可编辑代码实现，不将整张截图作为页面背景来代替界面。

## 来源与许可

部分提示词与 HTML 提取代码来自 [abi/screenshot-to-code](https://github.com/abi/screenshot-to-code)。复用范围及固定版本见 [来源说明](references/upstream.md)，对应的 MIT 许可证保留在 [vendor/LICENSE](vendor/LICENSE)。
