# -*- coding: utf-8 -*-
"""C-06-bb-02 第二轮：配置表搬家与内容更新。

1. 新建 06-战斗/75-元效果系统/ 与 06-战斗/85-战斗行为系统/ 两个系统目录；
2. 元效果表迁至 75-元效果系统，战斗行为表迁至 85-战斗行为系统；
3. 战斗行为表移除紧急救治记录，并同步行动机会口径；
4. 新建角色属性表到 10-战斗总览。
"""
import io
import os

DESIGN = r"D:\myspace\Git\mygame\Dsh\Design"
COMBAT = os.path.join(DESIGN, "06-战斗")

META_OLD = os.path.join(COMBAT, "70-遗物系统", "70_元效果表_v1.csv")
META_NEW_DIR = os.path.join(COMBAT, "75-元效果系统")
META_NEW = os.path.join(META_NEW_DIR, "75_元效果表_v2.csv")

BHV_OLD = os.path.join(COMBAT, "10-战斗总览", "10_战斗行为表_v1.csv")
BHV_NEW_DIR = os.path.join(COMBAT, "85-战斗行为系统")
BHV_NEW = os.path.join(BHV_NEW_DIR, "85_战斗行为表_v2.csv")

ATTR_NEW = os.path.join(COMBAT, "10-战斗总览", "10_角色属性表_v1.csv")

ATTR_HEADER = ("属性ID,属性名称,类别,含义,取值范围出处,生效系统,生效方式,关联机制,"
               "Demo状态,扩展说明,依据")

ATTR_ROWS = [
    "ATTR-HP-001,生命,单位状态,单位当前可承受的损伤总量；归零时进入失去行动能力状态,"
    "角色配置与数值侧,战斗总览、战斗目标与结果、存档,"
    "在战斗中随伤害与恢复实时变化；在事件内实时结算,"
    "生命状态三档判定、倒地与被击倒、死亡结局判定,已确认,"
    "生命上限的成长途径与恢复道具的恢复量由数值与内容侧给出,回答37",

    "ATTR-WOUND-001,伤势,单位状态,生命之外的持续影响；分轻伤、重伤与致残三档,"
    "角色配置与数值侧,战斗总览、战斗目标与结果、存档,"
    "生命值低于配置限度时档位提升一档；不随战斗结束自动清除,"
    "轻伤状态下生命归零视为被击倒、战斗外恢复流程、下一次进入战斗终止恢复,已确认,"
    "三档的判断限度与恢复速度由数值侧给出,回答37、CBT2-GAP-009",

    "ATTR-ACT-001,行动力,数值属性,决定自由探图阶段的活动范围大小与战斗内的行动范围,"
    "角色配置与数值侧,移动系统、战场与战棋规则,"
    "移动系统读取用于划定以基点为中心的活动范围；战斗内读取用于确定行动范围,"
    "活动范围划定、战场移动范围,已确认,"
    "活动范围与行动范围的换算关系由数值侧给出,回答40、45",

    "ATTR-STR-001,力量,数值属性,决定无伤害组件物品的投掷效果,"
    "角色配置与数值侧,技能与库存联动,"
    "投掷结算时与物品重量的比值决定伤害与后摇档位,"
    "投掷折算、比值低于下限时投掷无效,已确认,"
    "比值到伤害与后摇的换算曲线由数值侧给出,回答10、CBT2-GAP-004",

    "ATTR-SPD-001,行动速度,数值属性,参与行动延迟的补正计算,"
    "角色配置与数值侧,时间轴与行动顺序,"
    "与行为后摇和技能后摇共同决定单位的下一次行动时机,"
    "时间轴推进、时间轴预览,已确认,"
    "补正公式与后摇的合成规则由数值侧给出,回答7、8",

    "ATTR-TBD-001,待补充属性,待定义,待定义,待定义,待定义,待定义,待定义,待补充,"
    "角色拥有的属性不止当前登记的五类，每个属性的效果也有尚未编写到位的部分；"
    "新增属性前补齐全部字段并登记到战斗总览正文,CBT2-GAP-002",
]

BHV_HEADER_KEEP = True  # 沿用原表头，只删行与改字段取值


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def main():
    # 1. 目录
    os.makedirs(META_NEW_DIR, exist_ok=True)
    os.makedirs(BHV_NEW_DIR, exist_ok=True)
    print("新建目录: 75-元效果系统、85-战斗行为系统")

    # 2. 元效果表搬家
    meta = read(META_OLD)
    meta = meta.replace("元效果ID,", "元效果ID,", 1)
    write(META_NEW, meta)
    print("元效果表: 70-遗物系统 -> 75-元效果系统, %d 行" % len(meta.strip().splitlines()))

    # 3. 战斗行为表搬家 + 删除紧急救治 + 行动机会口径
    bhv = read(BHV_OLD)
    lines = [l for l in bhv.strip().splitlines()]
    header, rows = lines[0], lines[1:]
    kept = [r for r in rows if not r.startswith("BHV-COMBAT-001")]
    removed = len(rows) - len(kept)
    # 移动行改为可与技能合并
    new_rows = []
    for r in kept:
        if r.startswith("BHV-MOVE-001"):
            r = r.replace("独立消耗一次行动机会", "与一项技能合并占用同一次行动机会，也可单独占用一次行动机会")
            r = r.replace("移动与连携爆发互斥：槽内已有 M 时，后续任何行动清空 M 及其之前的字母",
                          "移动与连携爆发互斥：槽内已有 M 时，后续任何行动清空 M 及其之前的字母；"
                          "与技能合并时按动作顺序追加字母，移动与技能同处一次行动内")
        if r.startswith("BHV-SKILL-001"):
            r = r.replace("消耗一次行动机会", "占用一次行动机会，可与一次移动合并")
        new_rows.append(r)
    write(BHV_NEW, "\n".join([header] + new_rows) + "\n")
    print("战斗行为表: 10-战斗总览 -> 85-战斗行为系统, 删除 %d 行（紧急救治），剩 %d 行"
          % (removed, len(new_rows)))

    # 4. 角色属性表
    attr = "\n".join([ATTR_HEADER] + ATTR_ROWS) + "\n"
    write(ATTR_NEW, attr)
    print("角色属性表: 新建 %d 行 %d 列"
          % (len(attr.strip().splitlines()), len(ATTR_HEADER.split(","))))

    # 5. 移除旧路径文件
    for old in (META_OLD, BHV_OLD):
        if os.path.exists(old):
            os.remove(old)
            print("已移除旧位置:", os.path.relpath(old, COMBAT))


if __name__ == "__main__":
    main()
