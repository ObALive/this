# -*- coding: utf-8 -*-
"""第四轮：商人配置表措辞、触发条件词条规则、决策 35-36、文件重命名与决策库更新。"""
import io
import json
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(OUTPUT_DIR, "C-06-bb-01", "C-06-bb-01_战斗系统缺口决策库_v1.sqlite")
DUMP = os.path.join(HERE, "decisions_dump.json")
ARCHIVE_DOC = os.path.join(OUTPUT_DIR, "C-06-bb-01", "C-06-bb-02_回答归档_v4.md")
NEW_DOC = os.path.join(OUTPUT_DIR, "C-06-bb-01", "C-06-bb-02_新问题清单_v4.md")
DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"

ARCHIVE_INFO = {
    "CBT4-GAP-001": ("不另建类型表，物品词条作为统一分类标识：一个物品可挂载多个互不排斥的词条，商人经营范围按用途词条匹配、容器允许内容约束按内容约束词条匹配；新建物品词条表作为权威清单",
                     "05-05 §2.3 与 §2.4；新建 05_物品词条表_v1.csv；06-60 §6；决策 35；交互逻辑 56"),
    "CBT4-GAP-002": ("重量作为元物品的标准字段登记并采用统一量纲，参与投掷折算、载具带货与后续重量限制；体积与重量分离，只保留字段留给远期收纳",
                     "05-05 §2.2；06-80 §5；投掷组件表 THROW-BULK-001；决策 36；交互逻辑 57"),
}

NEW_GAPS = [
    ("CBT5-GAP-001", "词条表与商人原型配置表的衔接未闭环：商人配置表仍写法为主营词条，未指明使用哪一类词条与如何组合", "B1",
     "C-06-bb-02 第四轮回答 CBT4-GAP-001；05_商人原型配置表_v1.csv；05-10 §4.2",
     "05-10 金钱与货物、05-05 物品系统、物品词条表、商人原型配置表",
     "明确商人主营词条的来源、组合方式与匹配范围", "主策划",
     [
         ("A", "候选 A：主营词条取自用途词条，允许配置多条并按同时满足匹配",
          "商人原型的主营词条从用途词条中选取，可以配置一条或多条；配置多条时按同时满足匹配，即商品需要挂载全部所列词条才进入经营范围。回收范围采用同一规则。",
          "表达力足够，可以组合出常规货物回收、装备出售这类精确范围，词条体系只有一套。代价是组合较多时配置容易过窄，可能找不到符合条件的商品。"),
         ("B", "候选 B：主营词条允许多条并按任一满足匹配",
          "主营词条可以配置多条，商品挂载其中任意一条即进入经营范围；需要收窄范围时靠物品池进一步限定。",
          "配置宽容，不容易出现空经营范围，内容侧填写成本低。代价是范围容易过宽，同类商人之间的差异要靠物品池区分，词条的筛选作用被削弱。"),
         ("C", "候选 C：主营词条只允许一条，差异靠物品池表达",
          "每个商人原型只配置一条主营词条，用它划定大范围，具体经营内容的差异全部由物品池决定。",
          "规则最简，匹配逻辑不需要处理组合。代价是商人的经营范围只能按单一维度划分，无法表达同时回收装备与遗物这类需求。"),
     ]),
    ("CBT5-GAP-002", "词条与物品池的层级关系未定义：词条划定范围之后，具体商品从哪一层物品池抽取没有规则", "B1",
     "C-06-bb-02 第四轮回答 CBT4-GAP-001；05-10 §4.2；05_商人原型配置表_v1.csv",
     "05-10 金钱与货物、05-05 物品系统、07-30 概率池联动、商人原型配置表",
     "定义词条到物品池的映射与抽取层级", "主策划",
     [
         ("A", "候选 A：词条直接对应物品池，一个词条一个池",
          "每个用途词条对应一个物品池，商人按主营词条取对应池并从中随机抽取经营内容。词条与池一一对应，映射关系固定。",
          "映射简单，内容侧只需要维护每类的物品池，新增词条时新开一个池。代价是同一物品可能属于多个池，需要规定跨池物品的去重口径。"),
         ("B", "候选 B：物品池独立维护，池内以词条标注适用商人范围",
          "物品池不按词条划分，由内容侧按主题维护池并给池标注适用的词条范围，商人在符合标注的池中抽取。",
          "池的组织自由，可以按大关或主题组织内容，不必被词条结构绑住。代价是池与词条的对应关系需要人工维护，容易出现标注遗漏。"),
         ("C", "候选 C：抽取由概率池联动系统统一负责",
          "词条与物品池的映射交给概率池联动系统，商人只声明主营词条，具体抽取由该系统按概率池配置执行，与事件池刷新共用一套机制。",
          "与既有的概率池体系统一，商人内容随线索树解锁自动变化。代价是把商人经营内容的抽取耦合进概率池系统，跨系统接口变多。"),
     ]),
]

ARCHIVED_BY = "C-06-bb-02（第四轮）"
ARCHIVED_AT = "2026-09-25"


def edit(path, pairs, label):
    if not os.path.isfile(path):
        print("跳过（不存在）:", label)
        return 0
    t = io.open(path, encoding="utf-8").read()
    hits = 0
    for old, new in pairs:
        if old == new:
            continue
        if old not in t:
            print("  未命中:", label, "|", old[:34].replace("\n", " "))
            continue
        t = t.replace(old, new, 1)
        hits += 1
    if hits:
        io.open(path, "w", encoding="utf-8", newline="\n").write(t)
    return hits


def main():
    # 1. 商人原型配置表：明确主营词条取自用途词条
    p = os.path.join(DESIGN, "05-运营与经济", "05-物品系统", "05_商人原型配置表_v1.csv")
    t = io.open(p, encoding="utf-8").read()
    t = t.replace("主营词条决定经营范围或收购范围，从对应物品池随机选取若干样作为本次经营内容",
                  "主营词条取自物品词条表中的用途词条，决定经营范围或收购范围，从对应物品池随机选取若干样作为本次经营内容")
    t = t.replace("主营词条限定在常规物品的物品池", "主营词条取自用途词条并限定在常规物品的物品池")
    t = t.replace("主营词条限定在装备的物品池", "主营词条取自用途词条并限定在装备的物品池")
    t = t.replace("主营词条限定在遗物的物品池", "主营词条取自用途词条并限定在遗物的物品池")
    t = t.replace("主营词条限定收购范围", "主营词条取自用途词条并限定收购范围")
    t = t.replace("出售范围与收购范围分别按主营词条确定", "出售范围与收购范围分别按取自用途词条的主营词条确定")
    t = t.replace("主营词条限定可订购的商品池", "主营词条取自用途词条并限定可订购的商品池")
    t = t.replace("主营词条限定拍品池", "主营词条取自用途词条并限定拍品池")
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("商人原型配置表：主营词条改为取自用途词条")

    # 2. 触发条件：按词条判断物品资格
    p = os.path.join(DESIGN, "02-时间与事件", "30-事件系统", "30-10-触发条件", "30-10_触发条件设计_v2.md")
    n = edit(p, [
        ("## 6 关联系统",
         "## 6 物品词条与条件\n\n条件判定中涉及物品资格的部分按物品词条判断：需要限定某类物品时，条件引用词条标识，物品挂载了所要求词条即满足。需要组合时按条件模块的与或非规则组合多条词条条件。\n\n词条清单与匹配用途见 `05-运营与经济/05-物品系统/05_物品词条表_v1.csv`，新增词条条件时不需要扩展本系统的条件类型。\n\n## 7 关联系统"),
        ("## 7 变更记录", "## 8 变更记录"),
    ], "触发条件")
    print("触发条件：新增物品词条与条件章节，替换 %d 处" % n)
    p = os.path.join(DESIGN, "02-时间与事件", "30-事件系统", "30-10-触发条件", "30-10_触发条件设计_v2.md")
    t = io.open(p, encoding="utf-8").read()
    t = t.replace("| v2.1 | 2026-09-19 |", "| v2.2 | 2026-09-25 | 新增物品词条与条件章节：涉及物品资格的条件按物品词条判断，词条清单由物品系统维护 | C-06-bb-02（第四轮） |\n| v2.1 | 2026-09-19 |", 1)
    t = t.replace("| 版本 | v2.1 |", "| 版本 | v2.2 |", 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

    # 3. 决策记录：新增决策 35、36 与回填
    p = os.path.join(DESIGN, "00-总览", "03_设计决策记录_v1.md")
    t = io.open(p, encoding="utf-8").read()
    anchor = "| 34 | 内容清单与系统框架的产出分界 |"
    end = t.find("\n", t.find(anchor))
    rows = (
        "\n| 35 | 物品类型的表达方式 | **定案** | C-06-bb-02 第四轮回答 CBT4-GAP-001：另建类型表会与词条体系并行造成两套标识；词条已经服务于商人经营范围，复用它可以让分类只维护一处 | "
        "不另建物品类型表，物品词条作为统一分类标识；一个物品可挂载多个互不排斥的词条，词条分用途词条与内容约束词条两类；商人经营范围按用途词条匹配，容器允许内容约束按内容约束词条匹配，涉及物品资格的条件按词条判断；建立物品词条表作为权威清单 | 2026-09-25 | C-06-bb-02（第四轮） |"
        "\n| 36 | 物品重量与体积 | **定案** | C-06-bb-02 第四轮回答 CBT4-GAP-002：重物投掷需要重量输入，而体积属于尚未立项的收纳玩法，两者若绑定会让投掷依赖未定体系 | "
        "重量作为元物品的标准字段登记并采用统一量纲，参与投掷折算、载具带货与后续重量限制；体积与重量分离，当前版本只保留字段不启用限制，留给远期收纳玩法 | 2026-09-25 | C-06-bb-02（第四轮） |"
    )
    t = t[:end] + rows + t[end:]
    anchor2 = "| 34 | `06-战斗/40-技能系统/40_技能系统设计_v4.md`（§5）"
    idx2 = t.find(anchor2)
    if idx2 >= 0:
        end2 = t.find("\n", idx2)
        t = t[:end2] + (
            "\n| 35 | `05-运营与经济/05-物品系统/05_物品系统设计_v1.md`（§2.3、§2.4、§8）、新建 `05-运营与经济/05-物品系统/05_物品词条表_v1.csv`、`05-运营与经济/05-物品系统/05_商人原型配置表_v1.csv`、`06-战斗/60-装备系统/60_装备系统设计_v7.md`（§6）、`02-时间与事件/30-事件系统/30-10-触发条件/30-10_触发条件设计_v2.md`（§6）、`00-总览/01_设计原则与跨系统交互逻辑_v1.md`（交互逻辑 56） |"
            "\n| 36 | `05-运营与经济/05-物品系统/05_物品系统设计_v1.md`（§2.2）、`06-战斗/80-技能与库存联动/80_技能与库存联动设计_v6.md`（§5）、`06-战斗/80-技能与库存联动/80_投掷组件表_v1.csv`、`00-总览/01_设计原则与跨系统交互逻辑_v1.md`（交互逻辑 57）、`09-数值与配置/10-数值模型/10_数值模型设计_v1.md` |"
        ) + t[end2:]
    t = t.replace("| 版本 | v1.12 |", "| 版本 | v1.12 |", 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    print("决策记录：新增决策 35、36")

    # 4. README 配置表清单
    p = os.path.join(DESIGN, "README.md")
    t = io.open(p, encoding="utf-8").read()
    old = "库内当前实例是 `05-运营与经济/05-物品系统/05_物品操作总表_v1.csv`"
    new = "库内当前实例是 `05-运营与经济/05-物品系统/05_物品词条表_v1.csv`、`05-运营与经济/05-物品系统/05_物品操作总表_v1.csv`"
    if old in t:
        io.open(p, "w", encoding="utf-8", newline="\n").write(t.replace(old, new, 1))
        print("README：配置表清单已补充物品词条表")

    # 5. 文件重命名（文件名与内部版本一致）
    renames = [
        ("05-运营与经济/05_运营与经济索引_v2.2.md", "05-运营与经济/05_运营与经济索引_v2.3.md"),
        ("06-战斗/60-装备系统/60_装备系统设计_v6.md", "06-战斗/60-装备系统/60_装备系统设计_v7.md"),
        ("06-战斗/80-技能与库存联动/80_技能与库存联动设计_v5.md", "06-战斗/80-技能与库存联动/80_技能与库存联动设计_v6.md"),
    ]
    for old_rel, new_rel in renames:
        src = os.path.join(DESIGN, *old_rel.split("/"))
        dst = os.path.join(DESIGN, *new_rel.split("/"))
        if os.path.isfile(src):
            os.replace(src, dst)
            print("重命名:", old_rel.split("/")[-1], "->", new_rel.split("/")[-1])

    # 6. 决策库更新
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
    doc = "Dsh/Output/C-06-bb-01/C-06-bb-02_新问题清单_v4.md"
    for (gap_id, title, level, source_ref, impact, close_cond, owner, options) in NEW_GAPS:
        cur.execute(
            "INSERT INTO gaps (gap_id, title, level, status, source_ref, impact_scope,"
            " close_condition, owner, priority_round, analysis_doc) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (gap_id, title, level, "待裁定", source_ref, impact, close_cond, owner,
             "C-06-bb-02 第四轮后续澄清", doc))
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

    # 7. 输出文档
    lines = [
        "# C-06-bb-02 回答归档（v4）", "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 文档定位 | 汇总 C-06-bb-01 决策库全部已裁定问题的结论与设计落点 |",
        "| 归档落点 | `C-06-bb-01_战斗系统缺口决策库_v1.sqlite` 的 gaps_archived 表 |",
        "| 构成 | 第一轮 45 项、第二轮 12 项、第三轮 6 项、第四轮 2 项 |",
        "| 后续问题 | `C-06-bb-02_新问题清单_v4.md` |",
        "| 更新日期 | 2026-09-25 |", "",
        "前几轮结论见 `C-06-bb-02_回答归档_v1.md` 至 `_v3.md`，本文档补充第四轮。",
        "", "---", "", "## 一、第四轮归档明细", "",
        "| 编号 | 原问题 | 裁定方式 | 结论摘要 | 设计落点 |", "| --- | --- | --- | --- | --- |",
    ]
    for item in dump["gaps"]:
        conclusion, landed = ARCHIVE_INFO.get(item["gap_id"], ("", ""))
        how = ("候选 %s" % item["chosen_label"]) if item["status"] == "已选候选" else "自定义方案"
        lines.append("| %s | %s | %s | %s | %s |"
                     % (item["gap_id"], item["title"].replace("|", "／"), how, conclusion, landed))
    lines += ["", "## 二、归档总览", "", "| 项目 | 数量 |", "| --- | --- |",
              "| 归档问题总数 | %d |" % stats["归档总数"],
              "| 其中第一轮 | 45 |", "| 其中第二轮 | 12 |",
              "| 其中第三轮 | 6 |", "| 其中第四轮 | %d |" % stats["本轮归档"],
              "| 当前未澄清问题 | %d |" % stats["新问题"], "",
              "## 三、变更记录", "", "| 版本 | 日期 | 变更 | 依据任务 |", "| --- | --- | --- | --- |",
              "| v1 | 2026-09-25 | 归档第一轮 45 项 | C-06-bb-02 |",
              "| v2 | 2026-09-25 | 归档第二轮 12 项 | C-06-bb-02（第二轮） |",
              "| v3 | 2026-09-25 | 归档第三轮 6 项 | C-06-bb-02（第三轮） |",
              "| v4 | 2026-09-25 | 归档第四轮 2 项 | C-06-bb-02（第四轮） |"]
    io.open(ARCHIVE_DOC, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    lines = [
        "# C-06-bb-02 新问题清单（v4）", "",
        "| 项目 | 内容 |", "| --- | --- |",
        "| 文档定位 | 记录第四轮回答后仍未澄清到可直接实现粒度的问题，每项附三条候选 |",
        "| 裁定入口 | `C-06-bb-01_战斗系统缺口决策库_v1.sqlite`，可用填写器逐项裁定 |",
        "| 上一版本 | `C-06-bb-02_新问题清单_v3.md`（CBT4-GAP-001、002 已裁定并归档） |",
        "| 更新日期 | 2026-09-25 |", "",
        "共 %d 项，均为 B1 级。" % len(NEW_GAPS), "", "---", "",
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
              "| v1 | 2026-09-25 | 建立 12 项后续澄清问题 | C-06-bb-02 |",
              "| v2 | 2026-09-25 | 重建为 6 项 | C-06-bb-02（第二轮） |",
              "| v3 | 2026-09-25 | 重建为 2 项 | C-06-bb-02（第三轮） |",
              "| v4 | 2026-09-25 | 重建为 %d 项（CBT5-GAP-001、002） | C-06-bb-02（第四轮） |" % len(NEW_GAPS)]
    io.open(NEW_DOC, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("已输出:", os.path.basename(ARCHIVE_DOC), os.path.basename(NEW_DOC))


if __name__ == "__main__":
    main()
