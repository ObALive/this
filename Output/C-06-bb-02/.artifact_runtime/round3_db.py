# -*- coding: utf-8 -*-
"""第三轮：更新决策库（归档 CBT3 六项，另立新问题）与补齐变更记录。"""
import io
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(OUTPUT_DIR, "C-06-bb-01", "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")
DUMP = os.path.join(HERE, "decisions_dump.json")
ARCHIVE_DOC = os.path.join(OUTPUT_DIR, "C-06-bb-01", "C-06-bb-02_回答归档_v3.md")
NEW_DOC = os.path.join(OUTPUT_DIR, "C-06-bb-01", "C-06-bb-02_新问题清单_v3.md")
DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"

ARCHIVE_INFO = {
    "CBT3-GAP-001": ("法术书用容器组件的允许内容约束表达为只接受符文书页类型；书页装入与取出使用容器界面常规操作并新增两条操作记录",
                     "05-05 §2.3 与 §4；物品操作总表 ITEM-CTN-001、002；06-60 §6；决策 32；交互逻辑 54"),
    "CBT3-GAP-002": ("符文书页主要由战斗后的容器搜刮、敌方遗体与事件掉落产出，少数商人出售；法术获取与战斗探索绑定更强",
                     "06-40 §3.3；06-80 §6；系统全景图跨域关注点"),
    "CBT3-GAP-003": ("物品投掷由专用组件管理：新增投掷组件表登记伤害投掷、效果投掷、重物投掷与禁止投掷四类；贵重装备通过禁止投掷组件排除",
                     "05-05 §4；06-80 §5；新建 80_投掷组件表_v1.csv；决策 33；交互逻辑 55"),
    "CBT3-GAP-004": ("技能系统只定义四类动作的作用与配置约束，基础技能、连携技能与符文书页清单由内容设计按大关分层填充",
                     "06-40 §5；决策 34"),
    "CBT3-GAP-005": ("敌人系统定义行为模板的八个契约字段，敌人类型、强度分层与模板取值由内容设计填充，难度体系通过调制敌人配置起作用",
                     "06-90 §4；决策 34"),
    "CBT3-GAP-006": ("战斗总览只规定四区块职责与选中单位呈现规则，布局、信息优先级、键位与操作方式留到界面设计阶段产出",
                     "06-10 §3.6；决策 34"),
}

NEW_GAPS = [
    ("CBT4-GAP-001", "允许内容约束的类型划分口径未定义：约束按物品类型匹配，但物品类型体系本身还没有清单", "B0",
     "C-06-bb-02 第三轮回答 CBT3-GAP-001；05-05 §2.3",
     "05-05 物品系统、05-30 背包系统、06-60 装备系统、06-80 技能与库存联动、全部配置表",
     "定义物品类型体系与允许内容约束的匹配规则", "主策划",
     [
         ("A", "候选 A：建立物品类型表作为类型体系的权威清单",
          "新建物品类型表，登记类型标识、类别名、父类型与适用说明，类型之间支持父子层级。允许内容约束按类型标识匹配，匹配规则为包含子类型。物品策划为每个元物品登记所属类型。",
          "类型体系有唯一权威清单，约束、条件判定与投掷组件都引用同一套标识，后续扩展有落点。代价是需要一轮类型梳理，且既有物品需要补录类型字段。"),
         ("B", "候选 B：类型由物品词条体系兼任",
          "不单独建类型表，用物品词条表达类型，允许内容约束匹配词条。词条体系已经服务于商人经营范围，可以复用。",
          "不新增体系，词条与类型统一，商人经营与容器约束共用一套标识。代价是词条面向经营与效果，语义较宽，用它表达严格的类型约束容易误配。"),
         ("C", "候选 C：约束逐容器直接列举允许的元物品",
          "允许内容约束不做类型抽象，直接在容器配置中列举允许的元物品清单。",
          "规则最直白，不需要类型体系，配置错误一眼可见。代价是每新增一种书页都要改所有法术书配置，物品池扩充时维护成本随容器数量增长。"),
     ]),
    ("CBT4-GAP-002", "物品三维数值仍未定义：重量参与投掷折算，但重量的取值口径与是否登记到属性表没有规则", "B1",
     "C-06-bb-02 第二轮回答 CBT2-GAP-004；第三轮回答 CBT3-GAP-003；05-05 §9",
     "05-05 物品系统、06-80 技能与库存联动、09-10 数值模型、投掷组件表",
     "确定物品重量的登记方式与取值口径", "数值策划",
     [
         ("A", "候选 A：重量作为元物品的标准属性登记，与体积分离",
          "重量作为元物品的一个标准字段登记，单位为统一量纲，与体积属性分离；重量影响投掷折算、载具带货与后续的重量限制，体积留给远期收纳玩法。",
          "重量有唯一来源，投掷与载具读取同一字段，远期收纳不会被重量口径绑住。代价是需要为全部物品补录重量，且重量与体积的配合关系要留给远期设计。"),
         ("B", "候选 B：重量由物品类型加尺寸档位推导",
          "不逐件登记重量，按物品类型与尺寸档位推导重量，同类同档物品重量一致。",
          "配置量最小，物品策划只需要选类型与档位，重量自动得出。代价是同类物品之间无法表达重量差异，投掷手感趋同。"),
         ("C", "候选 C：重量随体积一并留到远期收纳玩法立项",
          "重量与体积都不在当前版本登记，投掷折算暂以固定档位代替，待远期收纳玩法立项时一并设计。",
          "当前版本范围最小，避免为未定体系做两遍设计。代价是投掷的重物组件缺少实际输入，重物投掷在 Demo 内只能用档位近似。"),
     ]),
]

ARCHIVED_BY = "C-06-bb-02（第三轮）"
ARCHIVED_AT = "2026-09-25"


def main():
    dump = json.load(io.open(DUMP, encoding="utf-8"))
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    for item in dump["gaps"]:
        gap_id = item["gap_id"]
        conclusion, landed = ARCHIVE_INFO.get(gap_id, ("", ""))
        cur.execute(
            "INSERT OR REPLACE INTO gaps_archived (gap_id, title, level, priority_round,"
            " owner, decision_status, chosen_option_id, chosen_label, chosen_title,"
            " answer_text, decision_basis, extra_requirement, filled_at, conclusion,"
            " landed_at, archived_by, archived_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (gap_id, item["title"], item["level"], item["priority_round"], item["owner"],
             item["status"], item["chosen_option_id"] or None, item["chosen_label"] or None,
             item["chosen_title"] or None, item["answer_text"] or None,
             item["decision_basis"] or None, item["extra_requirement"] or None,
             item["filled_at"], conclusion, landed, ARCHIVED_BY, ARCHIVED_AT))

    cur.execute("PRAGMA foreign_keys = OFF")
    cur.execute("DELETE FROM solution_options")
    cur.execute("DELETE FROM decisions")
    cur.execute("DELETE FROM gaps")
    doc = "Dsh/Output/C-06-bb-01/C-06-bb-02_新问题清单_v3.md"
    for (gap_id, title, level, source_ref, impact, close_cond, owner, options) in NEW_GAPS:
        cur.execute(
            "INSERT INTO gaps (gap_id, title, level, status, source_ref, impact_scope,"
            " close_condition, owner, priority_round, analysis_doc) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (gap_id, title, level, "待裁定", source_ref, impact, close_cond, owner,
             "C-06-bb-02 第三轮后续澄清", doc))
        cur.execute("INSERT INTO decisions (gap_id, status) VALUES (?, '待裁定')", (gap_id,))
        for i, (label, summary, detail, tradeoff) in enumerate(options):
            cur.execute(
                "INSERT INTO solution_options (option_id, gap_id, seq, option_label,"
                " summary_title, detail, tradeoff, is_recommended) VALUES (?,?,?,?,?,?,?,0)",
                ("%s-OPT-%s" % (gap_id, label), gap_id, i + 1, label, summary, detail, tradeoff))
        cur.execute(
            "INSERT INTO solution_options (option_id, gap_id, seq, option_label,"
            " summary_title, detail, tradeoff, is_recommended, is_custom)"
            " VALUES (?,?,?,?,?,?,?,0,1)",
            ("%s-OPT-CUSTOM" % gap_id, gap_id, 99, "自定义", "自行填写预期设计方案", "", ""))
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    stats = {
        "归档总数": cur.execute("SELECT COUNT(*) FROM gaps_archived").fetchone()[0],
        "本轮归档": len(dump["gaps"]),
        "新问题": cur.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
        "新候选": cur.execute(
            "SELECT COUNT(*) FROM solution_options WHERE is_custom=0").fetchone()[0],
    }
    conn.close()
    print(json.dumps(stats, ensure_ascii=False, indent=1))

    # ---------------- 输出文档
    lines = [
        "# C-06-bb-02 回答归档（v3）", "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 文档定位 | 汇总 C-06-bb-01 决策库全部已裁定问题的结论与设计落点 |",
        "| 归档落点 | `C-06-bb-01_战斗系统缺口决策库_v1.sqlite` 的 gaps_archived 表 |",
        "| 构成 | 第一轮 45 项、第二轮 12 项、第三轮 6 项 |",
        "| 后续问题 | `C-06-bb-02_新问题清单_v3.md` |",
        "| 更新日期 | 2026-09-25 |", "",
        "第一轮结论见 `C-06-bb-02_回答归档_v1.md`，第二轮见 `C-06-bb-02_回答归档_v2.md`，本文档补充第三轮。",
        "", "---", "", "## 一、第三轮归档明细（CBT3-GAP-001 至 006）", "",
        "| 编号 | 原问题 | 裁定方式 | 结论摘要 | 设计落点 |", "| --- | --- | --- | --- | --- |",
    ]
    for item in dump["gaps"]:
        conclusion, landed = ARCHIVE_INFO.get(item["gap_id"], ("", ""))
        how = ("候选 %s" % item["chosen_label"]) if item["status"] == "已选候选" else "自定义方案"
        lines.append("| %s | %s | %s | %s | %s |"
                     % (item["gap_id"], item["title"].replace("|", "／"), how, conclusion, landed))
    lines += ["", "## 二、第三轮填写时留下的补充要求", "", "| 编号 | 补充要求 |", "| --- | --- |"]
    for item in dump["gaps"]:
        if item["extra_requirement"]:
            lines.append("| %s | %s |" % (item["gap_id"], item["extra_requirement"]))
    lines += ["", "## 三、归档总览", "", "| 项目 | 数量 |", "| --- | --- |",
              "| 归档问题总数 | %d |" % stats["归档总数"],
              "| 其中第一轮 | 45 |", "| 其中第二轮 | 12 |",
              "| 其中第三轮 | %d |" % stats["本轮归档"],
              "| 当前未澄清问题 | %d |" % stats["新问题"], "",
              "## 四、变更记录", "", "| 版本 | 日期 | 变更 | 依据任务 |", "| --- | --- | --- | --- |",
              "| v1 | 2026-09-25 | 归档第一轮 45 项 | C-06-bb-02 |",
              "| v2 | 2026-09-25 | 归档第二轮 12 项并给出归档总览 | C-06-bb-02（第二轮） |",
              "| v3 | 2026-09-25 | 归档第三轮 6 项（CBT3-GAP-001 至 006） | C-06-bb-02（第三轮） |"]
    io.open(ARCHIVE_DOC, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    lines = [
        "# C-06-bb-02 新问题清单（v3）", "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 文档定位 | 记录第三轮回答后仍未澄清到可直接实现粒度的问题，每项附三条候选 |",
        "| 裁定入口 | `C-06-bb-01_战斗系统缺口决策库_v1.sqlite`，可用填写器逐项裁定 |",
        "| 上一版本 | `C-06-bb-02_新问题清单_v2.md`（CBT3-GAP-001 至 006 已全部裁定并归档） |",
        "| 更新日期 | 2026-09-25 |", "",
        "共 %d 项，均为 B0 或 B1 级。" % len(NEW_GAPS), "", "---", "",
    ]
    for (gap_id, title, level, source, impact, close_cond, owner, options) in NEW_GAPS:
        lines += ["## %s %s" % (gap_id, title), "", "| 字段 | 内容 |", "| --- | --- |",
                  "| 等级 | %s |" % level, "| 责任方 | %s |" % owner,
                  "| 来源 | %s |" % source, "| 影响范围 | %s |" % impact,
                  "| 关闭条件 | %s |" % close_cond, ""]
        for (label, summary, detail, tradeoff) in options:
            lines += ["**候选 %s：%s**" % (label, summary), "", "方案：%s" % detail, "",
                      "代价与影响：%s" % tradeoff, ""]
        lines += ["---", ""]
    lines += ["## 变更记录", "", "| 版本 | 日期 | 变更 | 依据任务 |", "| --- | --- | --- | --- |",
              "| v1 | 2026-09-25 | 建立 12 项后续澄清问题，已全部裁定 | C-06-bb-02 |",
              "| v2 | 2026-09-25 | 重建为第二轮之后的 6 项问题，已全部裁定 | C-06-bb-02（第二轮） |",
              "| v3 | 2026-09-25 | 重建为第三轮之后的 %d 项问题（CBT4-GAP-001 至 00%d） | C-06-bb-02（第三轮） |"
              % (len(NEW_GAPS), len(NEW_GAPS))]
    io.open(NEW_DOC, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("已输出:", os.path.basename(ARCHIVE_DOC), os.path.basename(NEW_DOC))

    # ---------------- 归档目录说明更新
    readme = os.path.join(OUTPUT_DIR, "C-06-bb-02", "归档", "README.md")
    t = io.open(readme, encoding="utf-8").read()
    add = ("\n## 快照清理（2026-09-25）\n\n"
           "本目录原先保存的 39 份修改前文档快照已删除。本项目采用 Git 版本管理，"
           "全部快照内容都可以通过 `git show HEAD:<路径>` 取回，归档与版本库重复，予以清理以减少占用。"
           "本说明文件与撤项口径保留，因为撤项理由与复活条件不是快照内容。\n")
    if "快照清理" not in t:
        t = t.rstrip() + "\n" + add
        io.open(readme, "w", encoding="utf-8", newline="\n").write(t)
        print("归档说明已更新")

    # ---------------- 变更记录补充
    fixes = [
        (os.path.join(DESIGN, "05-运营与经济", "05_运营与经济索引_v2.md"),
         "| v2.1 | 2026-09-25 | 跨域关联要点补充符文书页与法术书：法术书是只能容纳书页的容器并属于武器，其物品侧规则归本域物品系统 | C-06-bb-02（第二轮） |",
         "| v2.1 | 2026-09-25 | 跨域关联要点补充符文书页与法术书 | C-06-bb-02（第二轮） |\n"
         "| v2.2 | 2026-09-25 | 扩展配置表章节登记投掷组件表；跨域关联要点补充容器允许内容约束与投掷组件 | C-06-bb-02（第三轮） |"),
        (os.path.join(DESIGN, "09-数值与配置", "10-数值模型", "10_数值模型设计_v1.md"),
         "| v1.6 | 2026-09-25 | 认领台账新增四项（角色属性取值范围与生效曲线、元效果强度与叠加参数、符文书页与法术书数值、投掷无效下限），投掷折算补充比值口径 | C-06-bb-02（第二轮） |",
         "| v1.6 | 2026-09-25 | 认领台账新增四项（角色属性取值范围与生效曲线、元效果强度与叠加参数、符文书页与法术书数值、投掷无效下限） | C-06-bb-02（第二轮） |\n"
         "| v1.7 | 2026-09-25 | 认领台账新增物品重量取值与投掷组件参数两项，物品类型体系归入物品系统 | C-06-bb-02（第三轮） |"),
    ]
    for path, old, new in fixes:
        t = io.open(path, encoding="utf-8").read()
        if old in t:
            io.open(path, "w", encoding="utf-8", newline="\n").write(t.replace(old, new, 1))
            print("已补变更记录:", os.path.basename(path))
        else:
            print("未命中:", os.path.basename(path))


if __name__ == "__main__":
    main()
