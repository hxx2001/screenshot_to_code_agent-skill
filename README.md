# 截图与视频复刻 H5

使用当前 Agent，将网页或移动端 H5 的截图、录屏复刻为可编辑、可本地运行的前端代码。截图提供布局细节，录屏提供已演示的状态变化和动画过程。

支持截图、视频、截图加视频三种输入。新页面默认 HTML/CSS/JavaScript 与本地资源；已有项目沿用原框架。辅助脚本不负责识图或生成代码。

## 安装

视频扩展目前位于 `codex/video-interaction-recreation` 分支；`main` 仍是纯截图版。安装本文介绍的视频扩展版，请指定分支：

```bash
git clone --branch codex/video-interaction-recreation https://github.com/hxx2001/screenshot_to_code_agent-skill.git \
  ~/.codex/skills/screenshot-to-code-agent
```

自定义了 CODEX_HOME 时，使用其 skills 目录。目标已存在时先检查内容，不覆盖已有修改。通过 Git 克隆会保留历史；通过下载式安装器安装的文件目录可能没有 .git。

需要 Python 3.10+；裁图与图像比较需要 Pillow。视频抽帧还需要 FFmpeg 和 FFprobe。运行 `python3 scripts/video_frames.py doctor` 检查；可用 `SCREENSHOT_TO_CODE_FFMPEG` 和 `SCREENSHOT_TO_CODE_FFPROBE` 指定已有可执行文件。浏览器操作、录制和截图使用当前 Agent 环境提供的能力，本仓库不自带浏览器驱动。

## 更新与同步

已通过 Git 安装的用户，先确认工作区没有需要保留的修改，再更新视频扩展分支：

```bash
cd ~/.codex/skills/screenshot-to-code-agent
git fetch origin
git switch codex/video-interaction-recreation
git pull --ff-only
```

若安装目录没有 `.git`，应先在独立仓库副本中拉取该分支，再同步技能文件；不要在旧版目录直接运行 `git pull`。同步时包含新增的 `references/` 与 `scripts/` 文件，不要只替换 `SKILL.md`，并先备份自己的修改。

## 本次扩展

功能提交 `d97ed5c` 保留原截图流程，并新增：

- 录屏抽帧与真实时间索引，包括分段采样和动画窗口逐帧导出。
- `interaction-spec.json`：记录状态、转换、触发依据，以及观察、推断和未知项。
- 按真实经过时间配对参考录屏与复刻录屏，输出动态对比图与时间误差。
- 页面视觉、交互行为、动态还原分别验证，避免用点击成功代替视觉检查。
- 截图兼容性与视频辅助工具的回归测试。

纯截图任务继续支持原有四个辅助命令，不要求 FFmpeg 或交互说明文件。新增依赖只用于相应的视频、裁图和比较操作。

## 使用

```text
使用 $screenshot-to-code-agent 将这些截图复刻为本地可运行 H5，
保留文字和布局，实现可见交互，并截图对比。
```

```text
使用 $screenshot-to-code-agent 根据这段录屏复刻页面，
还原演示过的弹层、切换和动画，标出推断的交互，并回放对比过程。
```

```text
使用 $screenshot-to-code-agent 在当前 React 项目里复刻：
截图用于视觉细节，视频用于交互和动画。
```

录屏尽量完整演示需要还原的流程：进入、操作、退出；操作前后稍停，有触点显示更容易判断。不必点击所有按钮。未演示的行为按用户补充实现，或明确标成推断；关键行为缺失时需要补充说明。声音不默认分析。

## 工作流程

原有截图流程是所有输入的基础，视频能力在此基础上增加：

1. **分析截图**：确认内容区域、尺寸、文字、多图关系和状态差异；沿用现有项目的框架、目录和样式方案。
2. **整理素材**：优先复用原素材，裁切图片并检查清晰度、比例和来源；文案、数字、按钮保持可编辑。
3. **实现页面**：还原布局、字体、间距、颜色、图标、内容密度和固定/滚动区域，连接核心交互；局部修改保持原范围。
4. **预览校准**：实际浏览器同尺寸截图，逐项修正明显差异并重新截图；同时检查用户实际打开的预览尺寸。
5. **交付结果**：提供源码、预览入口和 design-qa.md。视觉和功能分别记录，生成对比图或点击成功不等于还原通过。

仅当提供视频时，额外检查完整操作过程、关键动画逐帧图和真实时间，用 interaction-spec.json 记录观察/推断，再在上述页面标准上实现交互与动画并回放验证。纯截图仍支持单图、多图、多页面与多状态，无需 FFmpeg、帧索引或 interaction-spec.json。

页面标准见 [page-fidelity.md](references/page-fidelity.md)。素材、字体或证据不足时具体说明缺口；可以修复的明显视觉差异不能只标注“近似”后结束。

计时动画、跟手拖拽、滚动联动和加载完成触发的变化分别处理。视频不能唯一确定原始缓动曲线、弹簧参数或实现库；这些可以近似，但不能宣称精确还原。静态视觉、交互行为和动态还原分别验收，任何一项通过都不能代替另外两项。

## 辅助脚本

| 脚本 | 用途 |
| --- | --- |
| agent_adapter.py prepare | 读取截图；可追加 --interaction-spec 生成包含交互证据的构建说明 |
| agent_adapter.py crop / finalize / compare | 素材裁切、HTML 提取、等尺寸截图对比 |
| video_frames.py doctor / extract | 依赖检查、分段或逐帧导出原尺寸 PNG 与真实时间索引 |
| interaction_spec.py | 检查状态、触发依据、帧引用、审阅范围与验证记录 |
| motion_compare.py | 按动画起点及真实经过时间配对两段录屏，生成并排图、叠加图及时间误差记录 |

详细示例见 [技能入口](SKILL.md)、[视频流程](references/video-workflow.md)、[交互格式](references/interaction-spec.md)和[动态验证](references/motion-verification.md)。对比不会偷偷缩放图片或拉伸时间轴，不输出未经验证的还原度评分。检查器能校验结构，不能代替 Agent 看画面和判断。

## 验证

```bash
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

测试使用临时生成的画面和视频，不需要用户录屏。FFmpeg/FFprobe 缺失时实际视频测试会跳过，其他测试继续；报告结果时应说明跳过项。浏览器真实录制与复刻质量需要另外实际验证，不能用单元测试代替。

## 版本与回退

初始纯截图版的 Git 提交是 `ffd43c5ba4273dcde264586ee0c391d6d0c3d598`。保留历史后，每次本地提交都是一个可定位的版本；只有 push 才会更新 GitHub。标签也需要单独推送或显式包含在推送里。

可以用独立 worktree 查看旧版，保留当前工作：

```bash
git worktree add --detach /absolute/screenshot-only-preview ffd43c5ba4273dcde264586ee0c391d6d0c3d598
```

该命令只打开旧版副本，不切换全局已安装技能。需要实际恢复安装版时，先保留未提交和未跟踪文件，再切换或创建恢复提交。远端恢复通常使用新提交保留历史，不依赖强制推送。

## 来源与边界

提示词和 HTML 提取代码部分来自 [abi/screenshot-to-code](https://github.com/abi/screenshot-to-code)，固定版本及复用范围见 [来源说明](references/upstream.md)，MIT 许可保留在 [vendor/LICENSE](vendor/LICENSE)。

视频证据流程参考项目内的视频问题分析技能的时间戳与关键帧方法，新增工具只处理本地媒体，不包含业务接口或项目专用诊断流程。用户媒体和生成页面放在任务输出目录，不进入技能仓库。

本地页面中的关注、发布、购买等交互是演示，不代表接入业务服务。低分辨率、缺帧、隐藏触点和未演示路径会限制复刻；结果应保留这些证据边界。
