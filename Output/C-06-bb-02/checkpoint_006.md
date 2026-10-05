# C-06-bb-02 Checkpoint 006（工具迁移）

任务状态：Completed

任务详细说明：战斗域收口后，按总监指示把缺口表的建库、管理、审阅系统从任务输出目录提取为跨章节常驻工具，落在 `Dsh/Tool/缺口决策系统/`，并补写建库、读库、迭代三份说明文档。本轮不改变任何设计内容，战斗域仍为 Closed。

已完成：

- 工具迁移：建库内核、网页填写器、导入与读出脚本、自测脚本共十一个文件迁入 `Dsh/Tool/缺口决策系统/`，任务目录只保留该任务特有产物；
- 路径解析改为通用：新增 `db_locator.py`，从工具目录向上定位工作区根目录，库发现扫描 `Dsh/Output` 下所有子目录中含「决策库」的 sqlite 文件，另接受 `--db` 显式指定；
- 建库内核更名并增强：`decision_db.py` 取代 `decision_db_template.py`（后者保留为兼容入口），表结构新增 `gaps_archived` 归档表并补 `ensure_archive_table()`，新建库直接具备归档条件；
- 三份说明文档：`建库说明.md`（目录结构、数据模型、JSON 格式、建库与校验、八项自检、补建能力、回溯数据）、`读库说明.md`（两种裁定形态与优先级、四种读取方式、五步判断顺序、冲突识别、常用 SQL）、`迭代使用说明.md`（一轮五步、导入判定规则、归档两步、三种开下一轮方式、四条边界、历史版本取用、填写器接口、九项自检）；
- 全流程自测：`测试/smoke_tool.py` 建库（2 缺口/5 候选/2 自定义行，完整性 ok）、模板校验、导出、导入（2 写入 0 未填无冲突）、读取、导出结论、归档（归档 2，主表 0）、填写器接口、临时目录清理九步全部通过；
- 清理：删除被取代的三支旧测试脚本、模板的更名备份与 `__pycache__`，`.gitignore` 增加 Python 缓存条目；
- 顺带修正：`05-运营与经济索引` 文件名 v2.3 与内部版本 v2.4 不一致，更名为 `05_运营与经济索引_v2.4.md`，同步决策 25 的路径引用，决策记录升至 v1.14。

未完成：无。工具可用性由自测覆盖，填写器由用户自行启动。

当前环境：Windows PowerShell；工作区 `D:\myspace\Git\mygame`；本轮写入限于 `Dsh/Tool`、`Dsh/Design/00-总览`、`Dsh/Design/05-运营与经济`、`Dsh/Report`、`Dsh/Output/C-06-bb-02` 与 `.gitignore`。

工具结构：

| 目录 | 内容 |
| --- | --- |
| `建库工具/` | `decision_db.py`、`decision_db_template.py`、`db_locator.py`、`build_decision_db.py`、`export_catalog.py`、`example_build.py` |
| `填写器/` | `decision_server.py`、`index.html`、`app.css`、`app.js` |
| `审阅工具/` | `dump_decisions.py`、`import_answers.py`、`archive_decided.py` |
| `测试/` | `smoke_tool.py` |
| 根目录 | `建库说明.md`、`读库说明.md`、`迭代使用说明.md` |

已修改文件：

- `Dsh/Tool/缺口决策系统/`：全部十一个脚本与三份说明文档（新建）；
- `Dsh/Output/C-06-bb-01/.artifact_runtime/`：旧工具副本删除，只留 `extract_decisions_data.py`；
- `Dsh/Design/05-运营与经济/05_运营与经济索引_v2.4.md`：由 v2.3 更名；
- `Dsh/Design/00-总览/03_设计决策记录_v1.md`：升至 v1.14，修正决策 25 的路径引用；
- `Dsh/Report/C-06-bb-02_Report.md`：新增第 38 至 42 节记录迁移；
- `.gitignore`：新增 Python 缓存条目。

下一步：后续任一章节执行信息缺口分析时，按 `建库说明.md` 准备数据文件建库，按 `迭代使用说明.md` 提问与归档，按 `读库说明.md` 读出裁定；战斗域设计本身不再需要改动。

更新时间：2026-09-25
