# 给 Codex 加载 Unity MCP / Skill 的调研报告

检索时间：2026 年（资料以当时页面为准）
目标：搞清"把 Unity 接进 Codex（Codex CLI / IDE 扩展 / ChatGPT 桌面端）"有哪些可行路线、各自怎么配、有什么坑。

---

## 0. 先分清两件事：MCP 和 Skill 解决的是不同问题

| | MCP（Model Context Protocol） | Skill（Agent Skills） |
|---|---|---|
| 作用 | 给 Codex 装**工具**，能真正操作 Unity Editor | 给 Codex 装**知识/流程**，教它 Unity 的正确用法 |
| 形态 | 本地 stdio 进程或 HTTP/SSE 服务 | `SKILL.md` + 参考资料目录 |
| 效果 | 创建 GameObject、改场景、跑测试、截图、跑 Play Mode | 少写错 API、按 Unity 官方实践走、少来回试错 |
| 局限 | 工具 schema 会占上下文（几十个工具可能上万 token） | 单独用 Skill 无法控制 Editor，也无法隐藏已加载的 MCP 工具 schema |

很多方案是**两者搭配**：MCP 给手，Skill 给脑。

Codex 侧的关键事实（官方文档）：

- **MCP 配置**写在 `~/.codex/config.toml`，也可以项目级 `.codex/config.toml`（**仅受信任项目**才会加载）。
- CLI 方式：`codex mcp add <名字> --env K=V -- <启动命令>`、`codex mcp list`、`codex mcp login <名字>`；TUI 里用 `/mcp` 查看。
- 支持 **stdio**（`command` / `args` / `env` / `env_vars` / `cwd`）和 **Streamable HTTP**（`url` / `bearer_token_env_var` / `http_headers`）。
- 常用可调项：`startup_timeout_sec`（默认 10）、`tool_timeout_sec`（默认 60）、`enabled`、`enabled_tools` / `disabled_tools`、`default_tools_approval_mode`（`auto` / `prompt` / `writes` / `approve`）。
- **Skill 发现路径**：仓库内 `.agents/skills/`（从 cwd 向上找）、用户级 `~/.agents/skills/`、管理员 `/etc/codex/skills`、内置系统技能。`SKILL.md` 的 YAML frontmatter 只需 `name` + `description`，其中 `description` 就是隐式触发条件。
- 显式调用用 `$技能名` 或 `/skills`；可用 `[[skills.config]]`（`path` + `enabled = false`）单独禁用某个技能。
- **Plugin** 是 Skill / MCP 的分发单元：`codex plugin marketplace add <repo>`、`codex plugin add <name>@<marketplace>`、`codex plugin list`。插件自带的 MCP server 由插件清单启动，用户配置只能控制开关和工具策略（`[plugins."x@y".mcp_servers.z]`）。

补充概念：Codex 里还有 **Plugin** 这个第三层概念，它是**分发单元**而不是能力类型——一个插件可以只带 skills、只带 MCP servers，或者两者都带。所以"是插件"不等于"是 MCP"。

参考：
- [Codex MCP 官方文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [openai/codex docs/config.md](https://raw.githubusercontent.com/openai/codex/main/docs/config.md)
- [Codex Skills 系统参考（社区整理）](https://raw.githubusercontent.com/shanraisshan/codex-cli-best-practice/main/docs/SKILLS.md)

### 逐项分类：谁提供 MCP、谁提供 Skill

**怎么自行判断：**MCP 一定有**一个 server**（启动命令 `command`/`args` 或 `url`），配置落在 `[mcp_servers.<名字>]`；Skill 一定有 **`SKILL.md`**，放在 `.agents/skills/` 之类的技能目录，靠 frontmatter 的 `description` 触发。没有 server 进程的东西都不是 MCP。

**纯 MCP（只给工具，不给知识）**

| 项目 | server 形态 |
|---|---|
| [CoderGamester/mcp-unity](https://github.com/CoderGamester/mcp-unity) | Node stdio server + Unity 内 WebSocket(8090) |
| [emeryporter/UnityMCP](https://github.com/emeryporter/UnityMCP) | Unity 内原生 HTTP server `http://localhost:8080/` |
| [Enyer182/codex-unity-mcp](https://github.com/Enyer182/codex-unity-mcp) | Python stdio server → Unity 内 loopback HTTP 桥 |
| **Unity CLI 的 `unity mcp`** | 官方，MCP server 直接编译进 `unity` 二进制（stdio） |

**纯 Skill（只给知识/流程，不直接操作 Editor）**

| 项目 | 说明 |
|---|---|
| [Unity-Technologies/unity-agent-plugin](https://github.com/Unity-Technologies/unity-agent-plugin) | ⚠️ 注意：这是 Unity **官方 Codex 插件**，名字里有 "plugin" 容易误判。其 `.codex-plugin/plugin.json` 只声明了 `"skills": "./skills/"`，**没有 `mcpServers` 字段**（另有 `requires_local_executor: true`）——即它自己**不含 MCP server**，31 个技能是纯知识。Editor 控制要靠它引导你去装/调用 **Unity CLI 的 MCP**，也就是上面那条 `unity mcp`。**官方插件 + 官方 CLI MCP = 脑 + 手，是两件东西拼起来的。** |
| [Unity-Technologies/skills](https://github.com/Unity-Technologies/skills) | 同一批官方技能的独立仓库（`npx skills add Unity-Technologies/skills`），也是纯知识 |
| `unity-cli` skill | 同样由 `unity skill install` 装到 `~/.agents/skills/unity-cli`，纯文档；注意它讲的是 CLI 用法，和 `unity mcp` 那个 server 不是一回事 |
| [AUN-PN/unity-agent-workflows](https://github.com/AUN-PN/unity-agent-workflows) | 第三方 Codex 插件/skill，纯工作流规则，无 MCP；可以配合任意 MCP 使用 |

**MCP + Skill 两件套（一个仓库同时提供两者）**

| 项目 | MCP 部分 | Skill 部分 |
|---|---|---|
| [CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp) | 约 50 工具，Python(FastMCP) stdio 或 HTTP `http://127.0.0.1:8080/mcp` + Unity 包 | `unity-mcp-skill/SKILL.md`（name: `unity-mcp-orchestrator`，约 16KB）+ `references/`（tools-reference 74KB、workflows 75KB、resources-reference、probuilder-guide） |
| [Vangardo/unity-mcp-efficient](https://github.com/Vangardo/unity-mcp-efficient) | facade server（6 工具，代理上游 CoplayDev） | `skills/unity-mcp-efficient/SKILL.md` → `~/.agents/skills/` |

**重要区分：两种 skill 的性质完全不同，不能只按"有/没有"看。**

- CoplayDev 的 skill 是**操作指南（operator guide）**：教 Codex 怎么用好这个 MCP——先读 resource 再动手、用 `batch_execute` 批量、写完脚本轮询编译状态、ProBuilder 怎么调。范围就是**这个 MCP 的工具面**。
- Unity 官方的 31 个 skill 是**引擎领域知识**：比如 `2d-pixel-perfect` 讲的是"PixelPerfectCamera 在 URP 和 Built-in 下是两套不兼容实现，写代码前先探测渲染管线"这种引擎层面的坑。31 个里只有 `unity-cli` 一个是操作指南，其余 30 个都是领域知识。

也就是说：**"怎么操作 MCP"这层 CoplayDev 自给自足；"懂不懂 Unity 引擎"这层它基本没有。**

作者刻意做了两件套（Vangardo）的理由也在这里：**facade 负责把工具面压小，skill 负责教 Codex 怎么搜索/批处理/恢复/验证**——单靠任何一半都不成立。

---

## 1. 路线 A：Unity 官方插件（最省事，也是目前最"正规"的路）

Unity 在 2026-09-16 发布了 **官方 Codex 插件**（配套还有 Claude Code 版），插件仓库是公开的：

- 仓库：[Unity-Technologies/unity-agent-plugin](https://github.com/Unity-Technologies/unity-agent-plugin)
- 介绍文章：[Unity's Official Plugin for Codex: Skills, CLI, Editor Control](https://unity.com/blog/unity-plugin-codex)（[中文版](https://unity.com/cn/blog/unity-plugin-codex)）
- 官方文档：[Unity's plugin for Codex • Unity Docs](https://docs.unity.com/zh-cn/ai/unity-plugin/codex)
- 相关背景报道：[mixed-news 的解读](https://mixed-news.com/en/unity-official-codex-claude-code-plugins-engine-skills/)

**安装（两条命令）：**

```bash
codex plugin marketplace add Unity-Technologies/unity-agent-plugin
codex plugin add unity@unity-agent-plugin
```

验证：`codex plugin list` 应显示 `unity@unity-agent-plugin  installed, enabled`。

**手动安装（不用 marketplace，把技能软链进个人技能目录）：**

```bash
git clone https://github.com/Unity-Technologies/unity-agent-plugin.git
cd unity-agent-plugin
mkdir -p ~/.agents/skills
for d in "$PWD"/skills/*; do ln -sfn "$d" ~/.agents/skills/"$(basename "$d")"; done
```

注意：这种方式装的技能**不带 `unity:` 前缀**（不是以插件形式装的）。

**内容：**约 31 个 Unity 工程师写的引擎技能，覆盖 9 个方向——入门与工具链、UI 与文本、2D 与精灵、图形与渲染、音频、场景与玩法、变现与 LiveOps、多人、平台与本地化。实际技能目录（从仓库 `skills/` 拉到的）包括：

`new-unity-project`、`unity-cli`、`unity-package-management`、`ui` / `ui-ugui` / `ui-uitk` / `ui-imgui`、`localization`、`optimize-text-mesh-pro`、`2d-pixel-perfect`、`sprite-editor`、`sprite-segment-3x3grid`、`create-tile-palette-or-rule-tiles`、`manage-sprite-atlas`、`create-2d-physics`、`physics-3d-collision`、`shader-graph-create-custom-node`、`migrate-birp-to-urp`、`urp-postprocessing`、`validate-urp-render-graph-renderer-feature`、`audio-setup-mixers`、`optimize-audio`、`setup-multiplayer-services`、`setup-vivox-voice-chat`、`initialize-ai-navigation`、`implement-in-app-purchases`、`levelplay-unity-integration`、`build-live-game`、`build-gtk`、`optimize-web`、`asset-transformer-toolkit`、`generate-editor-search-query`。

**Editor 控制怎么来的？** 插件本身主要是技能（知识），真正的 Editor 操作走 **Unity CLI 内置的 MCP server**：

- 技能会引导 Codex 在需要时检查/安装 Unity CLI，以及 CLI 连接 Editor 用的小包（`com.unity.pipeline`，从 UPM 注册表装）。装了 Unity Hub 的话 CLI 通常已经自带。
- `unity mcp` 启动一个内置 stdio MCP server，把连接中 Editor 的命令暴露成 MCP 工具。
- 一条命令写入 Codex 配置：`unity mcp configure codex`（`--local` 可写项目级，Codex 支持项目级）；`unity mcp configure --list` 看支持哪些客户端和配置路径。
- 把 **文档型技能**装进 Codex：`unity skill install codex`（默认 `~/.agents/skills/unity-cli`；`--local` 写 `.agents/skills/unity-cli`）。`unity upgrade` 后要跑 `unity skill refresh`。
- 运行时常用命令：`create_gameobject`、`find_gameobjects`、`get_scene_hierarchy`、`set_transform`、`add_component`、`rename/delete_gameobject`、`save_scene`、`create_script → recompile → attach_script`，以及 `eval` / `eval_file`（在 Editor 里直接跑 C#）。
- 一条重点：这类连接是**热连接**，单次往返大约 200–600ms，无脚本重编译、无 domain reload，适合 agent 反复迭代。

**注意：**Unity 官方插件兼容 Unity 6 及以上；技能是按 Unity 6.0+ 写的。据报道这套技能里**没有 XR/OpenXR 相关技能**（做 Quest / Vision Pro 的话这块仍缺）。

---

## 2. 路线 B：CoplayDev 的 "MCP for Unity"（社区最主流，生态最大）

- 仓库/README：[CoplayDev/unity-mcp](https://raw.githubusercontent.com/CoplayDev/unity-mcp/HEAD/README.md)
- 文档站：<https://coplaydev.github.io/unity-mcp/>

**定位：**MIT、免费，明确支持 Codex / Claude / Cursor / VS Code / Windsurf / Cline / Gemini CLI 等。约 **50 个 MCP 工具入口**，覆盖资产、场景、脚本、测试、Profiling、构建。有 Roslyn 脚本校验、多实例路由、工具分组（vfx/animation/ui/testing…）。

**要求：**Unity 2021.3 LTS → 6.x，Python 3.10+（走 `uv`）。

**安装：**
1. Unity → Package Manager → Add from git URL：
   `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main`
   （或 `openupm add com.coplaydev.unity-mcp`）
2. Unity 菜单 **Window → MCP for Unity → Configure All Detected Clients**
3. 直接下提示词，比如 "Create a cube at the origin and add a Rigidbody."

HTTP 后端默认在 `http://127.0.0.1:8080/mcp`（这一条在下面路线 D 里很关键）。

---

## 3. 路线 C：CoderGamester/mcp-unity（Node 桥 + 明确的 Codex TOML 片段）

- 仓库：[CoderGamester/mcp-unity](https://github.com/CoderGamester/mcp-unity)（[中文 README](https://github.com/codergamester/mcp-unity/blob/main/README_zh-CN.md)）
- 架构：Unity 内跑 WebSocket server（默认端口 **8090**），外部 Node.js server 实现 MCP 协议连过去。
- 要求：Unity 6+、Node.js 18+、npm 9+。

**Codex 全局配置（`~/.codex/config.toml`）：**

```toml
[mcp_servers.mcp-unity]
command = "node"
args = ["ABSOLUTE/PATH/TO/mcp-unity/Server~/build/index.js"]
```

**Codex 项目级（Unity 项目根目录 `.codex/config.toml`，相对路径、可提交 git）：**

```toml
[mcp_servers.mcp-unity]
command = "node"
args = ["Library/PackageCache/com.gamelovers.mcp-unity@<hash>/Server~/build/index.js"]
```

> 项目级要点：Codex 会用项目 `.codex/config.toml` 覆盖全局配置，**但前提是项目被标记为受信任**。第一次在项目根目录跑 `codex` 时必须批准 trust 提示，否则 Codex 直接忽略该文件。

其他细节：
- Unity 菜单 **Tools → MCP Unity → Server Window** 里有 "Configure Codex CLI" / "Configure Codex CLI (Project)" 按钮，也能生成片段，并可切换绝对路径/相对路径（"Use relative path"）。
- 包缓存路径里的 `@<hash>` 在升级 UPM 包后会变，升级后要重新点 Configure 或手改路径。
- 端口通过 `ProjectSettings/McpUnitySettings.json` 持久化，可用 `UNITY_PORT` 环境变量覆盖。
- **安全**：每个项目生成 256-bit token（`Library/McpUnity/bridge-token`），Unity 端要求 HTTP Basic（用户名 `mcp-unity`）并拒绝带 `Origin` 头的握手；`add_package` 工具默认关闭（Unity 包编译时可执行 Editor 代码）。
- 远程连接仍是明文 `ws://`，只在可信网络/VPN/SSH 隧道里用。
- 已知坑：Play Mode 切场景时 domain reload 会断连，导致 `run_tests` 报 "Connection failed: Unknown error"，规避方法是关掉 **Edit > Project Settings > Editor > Enter Play Mode Settings → Reload Domain**。
- `-batchmode` 默认禁用该 MCP，需要显式开 **Allow Batch Mode Server** 或 `MCP_UNITY_ALLOW_BATCH_MODE=true`。
- WSL2 里跑 Node 桥、Unity 在 Windows 上时会 `ECONNREFUSED`，解法是开启 WSL2 mirrored networking，或用 `UNITY_HOST=$(grep -m1 nameserver /etc/resolv.conf | awk '{print $2}')`。

---

## 4. 路线 D：Vangardo/unity-mcp-efficient（专治"工具 schema 撑爆上下文"，含 Codex skill）

- 仓库：[Vangardo/unity-mcp-efficient](https://github.com/Vangardo/unity-mcp-efficient)

**解决的问题很实际：**MCP for Unity 把 48 个工具的 schema 全塞进每次请求，实测约 **23,280 token**；这个 facade 把模型可见的工具降到 **6 个**、约 **915 token**（-96%），背后 377 个 Unity 操作仍可达。响应也做了压缩、分页、结果句柄。

**安装（就是给 Codex 用的命令）：**

```bash
codex mcp add unity-efficient \
  --env UNITY_MCP_BACKEND_URL=http://127.0.0.1:8080/mcp \
  -- uvx --from git+https://github.com/Vangardo/unity-mcp-efficient.git@v0.2.0 unity-mcp-efficient
```

**装 Codex skill：**

```text
$skill-installer Install the skill from https://github.com/Vangardo/unity-mcp-efficient/tree/v0.2.0/skills/unity-mcp-efficient
```

或手动把 `skills/unity-mcp-efficient` 拷到 `$HOME/.agents/skills/unity-mcp-efficient`（Codex 会自动检测技能变更，不出现就重启）。

**关键提醒（作者强调）：**
- 这个 facade **不替代** Unity 包和 Python server，`CoplayDev/unity-mcp` 仍是后端——要用 HTTP 传输模式启动上游。
- **必须在同一个 Codex 客户端里移除/禁用上游的直连条目**，否则两套工具面都暴露，省下的上下文全没了。
- 前端六工具：`search_capabilities`、`call_operation`、`batch_operations`、`inspect_unity`、`get_result`、`get_viewport`。
- 作者还点破了一个概念问题：**光靠 Skill 藏不住 MCP 客户端已经加载的工具 schema**，所以这个项目是 facade + skill 两件套。

---

## 5. 其他可选项（更小众，按需评估）

| 项目 | 特点 | 配置要点 |
|---|---|---|
| [emeryporter/UnityMCP](https://github.com/emeryporter/UnityMCP) | **100% Unity 原生**：纯 C 插件在 Editor 内起 HTTP server，不需要 Node/Python，跨 domain reload 不断连。51 工具、23 资源、Checkpoint、截图给 AI 看、远程访问带 TLS+API key。**GPLv3**。 | Editor 内起 `http://localhost:8080/`；Codex 等只支持 stdio 的客户端要用 `npx -y mcp-remote http://localhost:8080/` 桥接。作者注明除 Claude Code 外的客户端配置"未测试"。 |
| [Enyer182/codex-unity-mcp](https://github.com/Enyer182/codex-unity-mcp) | 专为 Codex 拆的：Unity 包起 loopback HTTP 桥 + Python stdio MCP server。安全模型明确（只监听 127.0.0.1、场景脏时禁止打开、文件读取限制在项目根内）。 | Codex + stdio → `python-server` → `127.0.0.1` HTTP → Unity Editor。仓库较新，成熟度需自行验证。 |
| [AUN-PN/unity-agent-workflows](https://github.com/AUN-PN/unity-agent-workflows) | 纯 Skill/Plugin 路线（无 MCP）：强制"没有证据不许改"的 Unity 2D 工作流，运行时归属链证明、UI/safe-area/TMP、多 agent 范围锁定等。MIT。 | 可作为 Codex plugin 装，或 `npx unity-agent-workflows`（默认写 `~/.codex/skills/unity-agent-workflows`）。 |
| [Unity-Technologies/skills](https://github.com/Unity-Technologies/skills) | Unity 官方技能集合的独立仓库，与插件同源。 | `npx skills add Unity-Technologies/skills`；官方明确建议 **Claude Code / Codex 用户改用 unity-agent-plugin 插件**，这样技能统一更新并出现在 agent 自己的插件菜单里。 |

---

## 6. 怎么选（建议）

1. **只想最省事、且项目是 Unity 6+ → 路线 A**：`codex plugin marketplace add` + `codex plugin add` 两条命令，技能和 Unity 官方知识都拿到；再用 `unity mcp configure codex` 接上 Editor 控制。没有 XR 技能，需要就自己补。
2. **想最大工具面 / 跨客户端统一 → 路线 B + 路线 D 组合**：上游 CoplayDev 跑 HTTP，Codex 里**只**注册 efficient facade，并配上它的 skill，避免上下文爆炸。这是目前"既要有手、又不烧 token"的最优解。
3. **喜欢显式 TOML、要项目级可提交配置 → 路线 C**：注意 trust 提示、`@<hash>` 路径漂移和 Play Mode 断连。
4. **不想装 Node/Python → emeryporter/UnityMCP**，但接受 GPLv3 和 stdio 桥接。

**无论走哪条，都建议：**
- 先 `codex mcp list` / TUI 的 `/mcp` 确认 server 真的连上了，再让它动项目。
- 用 `enabled_tools` / `disabled_tools` / `default_tools_approval_mode = "prompt"` 收紧破坏性工具。
- Codex 会直接改脚本、场景、资产，**动手前先提交或建分支**。
- 多个 Unity 实例同时开会互相抢/连错，优先用 `--project-path` 之类的显式指定。
- 上下文成本是真实成本：工具越多越贵，按需注册，不要把一个客户端里叠三套 Unity MCP。

---

## 7. 官方项目 star 为什么低，以及 CoplayDev 能否平替

### 7.1 实测 star / 活跃度（GitHub API，2026-10 前后）

| 仓库 | stars | forks | created | 许可证 |
|---|---:|---:|---|---|
| [CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp) | **14,801** | 1,540 | 2025-03-18 | MIT |
| [CoderGamester/mcp-unity](https://github.com/CoderGamester/mcp-unity) | 1,924 | 245 | 2025-03-13 | MIT |
| [Unity-Technologies/skills](https://github.com/Unity-Technologies/skills) | **1,060** | 64 | 2026-05-05 | Unity Companion License |
| [Unity-Technologies/unity-agent-plugin](https://github.com/Unity-Technologies/unity-agent-plugin) | **401** | 39 | 2026-08-06 | Unity Companion License |
| [Vangardo/unity-mcp-efficient](https://github.com/Vangardo/unity-mcp-efficient) | 14 | 1 | 2026-08-24 | MIT |
| [emeryporter/UnityMCP](https://github.com/emeryporter/UnityMCP) | 9 | 3 | 2026-01-26 | GPL-3.0 |
| [Enyer182/codex-unity-mcp](https://github.com/Enyer182/codex-unity-mcp) | 3 | 0 | 2026-03-17 | 无 |

先纠正一个前提：官方那两个**并不是"极低"**——401 和 1,060 对一个 2 个月 / 5 个月的新仓库不算差，只是相对 CoplayDev 的 14.8k 差了一个数量级。注意 `skills`（1060）反而**比插件本体**（401）还高，说明大家 star 的是内容，不是那个插件壳。

### 7.2 差距的成因（按影响排序）

1. **时间**：CoplayDev 已积累约 19 个月，官方插件才约 2 个月。star 是累积量，这条就占了大头。
2. **分发渠道不靠 GitHub**：官方走 `codex plugin marketplace add` / Claude 插件市场 / `npx skills add`，装上即用，用户**根本不需要访问仓库页**；插件市场自带发现机制。CoplayDev 恰恰相反，必须靠 README、star 徽章、Discord、star-history 图表来获客——它的 README 里真的挂了 star-history 图，这是典型增长手段。
3. **不是"代码项目"**：官方两个仓库的主体是 markdown 技能 + 清单，真正的 MCP/CLI 能力在 `unity` 二进制里（不在 GitHub）。CoplayDev 是标准 OSS 库（Unity 包 + Python server），有 code、issues、PR 需求，自然更容易被 star / fork。
4. **许可证与协作模式**：官方是 Unity Companion License（非 OSI 开源），`skills` 仓库还明确写着**不接受 PR**（"published here automatically, so this repo doesn't accept pull requests"）。不能 fork、不能提 PR，star 动机就弱很多；CoplayDev 是 MIT + 1,540 forks。
5. **star 不是质量指标**：emeryporter 只有 9 star 但路线独特（Unity 原生、免 Node/Python）；Vangardo 14 star 却解决了真实的上下文爆炸问题；Enyer182 3 star 且建仓当天后再无提交。反过来说 CoplayDev 的 14.8k 主要证明它**早、开放、社区运营好**，不自动证明它对 Codex 场景最优。

**结论：官方 star 低主要是"新 + 非开源 + 内容型 + 走插件市场"四个乘数叠加，不是质量差距。**

### 7.3 CoplayDev 能不能平替？要分层回答

| 层 | 官方方案 | CoplayDev | 能否平替 |
|---|---|---|---|
| **A. Editor 控制（手）** | `unity mcp`（CLI 内置 MCP server） | 约 50 工具 MCP server | ✅ **可以，甚至更强** |
| **B. MCP 操作指南（怎么用这只手）** | `unity-cli` skill + 插件里的操作类技能 | `unity-mcp-orchestrator` skill（tools-reference 74KB / workflows 75KB） | ✅ **可以** |
| **C. Unity 引擎领域知识（懂不懂 Unity）** | 30 个引擎技能（URP 迁移、pixel perfect、TMP、IAP/LevelPlay、UGS 多人、Shader Graph、本地化、safe area…） | **没有对应物** | ❌ **不能平替** |

**A 层对比（同为 MCP，确实互相竞争）：**

- CoplayDev 优势：MIT 可 fork；支持 Unity **2021.3 LTS → 6.x**（官方要求 Unity 6+）；不依赖 Unity CLI；工具面更宽；有 Roslyn 脚本校验、多实例路由、远程 server auth、工具分组。
- 官方 `unity mcp` 优势：无 sidecar 进程；热连接单次往返约 **200–600ms、无重编译无 domain reload**；`eval` / `eval_file` 能在 Editor 里直接跑 C#；与官方技能同源、随 CLI 一起升级。
- ⚠️ **两者只能留一个**：同时注册两个 MCP server 会让工具面翻倍、上下文成本暴涨（这正是 efficient facade 存在的理由）。

**C 层是官方真正的价值所在，也是"平替"的断点。** 官方技能讲的是引擎本身的坑（例：`2d-pixel-perfect` 一上来就说"PixelPerfectCamera 在 URP 和 Built-in 下是两套完全不兼容的实现，动手前必须先探测渲染管线"），这类知识 CoplayDev 完全没有，第三方 `AUN-PN/unity-agent-workflows` 也只覆盖 Unity 2D 的一小块。

### 7.4 因此推荐的组合

**最优解不是二选一，而是"官方技能 + 自选一个 MCP"：**

- 技能是纯 markdown，**不与任何 MCP server 冲突**，可以只装官方技能包而不用 Unity CLI MCP。
- Editor 控制二选一：Unity 6+ 且想省事/要热连接和 `eval` → 官方 `unity mcp`；需要 Unity 2021.3 支持、要 MIT 可 fork、要更宽工具面 → CoplayDev（追求上下文效率再加 efficient facade）。
- ⚠️ 一个需要实测的摩擦点：官方有相当一部分技能是**直接驱动 Editor** 的，它们假设你用的是 Unity CLI 那套工具名（`unity command ...`）。若改用 CoplayDev 当手，这些"驱动类"技能的命令名不会 1:1 对上，Codex 需要自行换算或改用纯知识类技能。**纯知识类技能不受影响。**（此条为基于官方 README 表述的推断，建议实际用一两个任务验证。）

---

## 8. 两个官方仓库装哪个：`unity-agent-plugin` vs `skills`

### 8.1 实测技能集差异

两个仓库都是 Unity 内部源自动发布（提交信息形如 `chore: publish N skills (...)`）：

| | 技能数 | 最后提交 |
|---|---:|---|
| [Unity-Technologies/skills](https://github.com/Unity-Technologies/skills) | **34** | 2026-10-08 |
| [Unity-Technologies/unity-agent-plugin](https://github.com/Unity-Technologies/unity-agent-plugin) | **32** | 2026-10-06 |

**重合度：32 个技能完全一致**，插件仓库是 skills 仓库的**子集**。skills 仓库多出 2 个：

- `project-auditor-fixes` —— 用 Project Auditor 做静态分析扫描，触发/轮询/读取 CSV 问题列表。
- `unity-pipeline` —— 驱动运行中的 Editor 或 dev Player：重编译、跑测试、跑 C# 脚本、运行时方法重载、审计项目。描述明确指向 `com.unity.pipeline` 包。

⚠️ 注意媒体报道的"31 个技能"与实际目录不符，**以仓库目录为准**（插件 32 / skills 34）。另外两者提交时间差 2 天，那 2 个技能**可能只是发布延迟**，装之前建议重新比一次目录。差异是有意裁剪还是滞后，官方未说明。

### 8.2 结论：Codex 用户装 `unity-agent-plugin`

Unity 官方 README 明确建议：

> Using Claude Code or Codex? Install the official Unity plugin instead. It ships these same skills as one package, so they update together and appear in the agent's own plugin and slash-command menus.

```bash
codex plugin marketplace add Unity-Technologies/unity-agent-plugin
codex plugin add unity@unity-agent-plugin
```

理由：
1. **Codex 原生路径**：走插件市场，`codex plugin list` 能看到版本与启停状态，技能更新随插件走。
2. **`npx skills add` 是通用转换器**：面向 Claude Code / Copilot / Cursor / Cline 等 50+ agent 的多格式安装器，对 Codex 属于绕路，多一层格式转换与版本管理。
3. 技能内容基本同一份（32 个重合）。

**只有一种情况选 `skills` 仓库**：明确需要那多出来的 2 个技能（尤其是 `unity-pipeline` 的活 Editor 驱动能力）。

⚠️ **不要两个都装**：Codex 对**同名技能不做合并**，重复安装会让同一批技能的元数据（name + description）进两次 prompt，触发判断也可能互相打架。真要补，只手动 link 那 2 个目录，不要整包重装。

### 8.3 三个配套提醒

- 这两个仓库**都只给技能，不含 MCP**。Editor 控制仍需另配（`unity mcp configure codex`，或改用 CoplayDev）。
- **别用**插件 README 里 symlink 到 `~/.agents/skills` 的"手动安装"：那条路装的技能不带 `unity:` 前缀，也不会随插件更新，得自己 `git pull`。
- 若手选的是 CoplayDev 而非 Unity CLI，注意 `unity-cli` / `unity-pipeline` 这两个技能假设的是 Unity CLI 工具名，会与 CoplayDev 的工具名错位（见 7.4）。
