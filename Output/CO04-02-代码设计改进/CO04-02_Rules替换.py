"""Apply the approved stage-three documents; validate all anchors before writing."""
from pathlib import Path
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Output' / 'CO04-02-代码设计改进'
DATE = '2026-10-17'


def read(path):
    return path.read_text(encoding='utf-8-sig')


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one occurrence: {old[:100]!r}; got {text.count(old)}')
    return text.replace(old, new, 1)


def between(text, start, end):
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j].strip()


def splice(text, start, end, replacement):
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[:i] + replacement.rstrip() + '\n\n' + text[j:]


def date(text):
    result, count = re.subn(r'(?m)^\| 更新日期 \| \d{4}-\d{2}-\d{2} \|$', f'| 更新日期 | {DATE} |', text)
    if count != 1:
        raise ValueError(f'Expected one metadata date; got {count}')
    return result


linked = read(OUT / 'CO04-02_第三步_关联规范联动修订稿.md')
candidate = read(OUT / 'CO04-02_第三步_代码设计案编辑规范_候选稿.md')
names = {
    '01': '01_规范总则.md',
    '03': '03_文档编辑规范.md',
    '04': '04_规范目录维护规范.md',
    '05': '05_文档库组织规范.md',
    '06': '06_代码设计案编辑规范.md',
    '07': '07_架构设计案编辑规范.md',
    '08': '08_交互原语与交互语义设计规范.md',
    'index': 'README.md',
    'base': 'BaseRules.md',
}
baseline = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
originals = {}
for key, name in names.items():
    subprocess.run(['git', 'cat-file', '-e', f'HEAD:Rules/{name}'], cwd=ROOT, check=True)
    originals[key] = read(ROOT / 'Rules' / name)
updated = dict(originals)

# NR-06: adopt the complete approved text, removing candidate-only metadata.
s = once(candidate, '| 拟用规范编号 | NR-06，整体替换稿 |', '| 规范编号 | NR-06 |')
s = once(s, '| 文本状态 | 候选正文，尚未替换现行规范 |', f'| 状态 | 生效 |\n| 生效日期 | {DATE} |')
s = once(s, '本候选正文与关联规范修订稿构成一组采用文本。正式采用前，本文不自动撤销现行规范或架构约束。附录中的示例只说明写法，不定义项目业务架构。', '附录中的示例只说明写法，不定义项目业务架构。')
updated['06'] = s

# NR-01: stage responsibilities, read-only excerpts, authorized technical decisions.
s = originals['01']
layer_text = between(linked, '| 层 | 文档 | 消除的歧义 |', '### 2. 在 §二.3')
s = splice(s, '| 层 | 文档 | 消除的歧义 |', '## 2. 上层定约束，下层定细节', layer_text)
excerpt = between(linked, '唯一事实来源规定定义与修改权的归属。', '### 3. 整体替换 §二.5')
s = once(s, '## 4. 保留未决', excerpt + '\n\n## 4. 保留未决')
s = once(s, '| 重大取舍 | 上游设计稿与架构设计案 |', '| 重大取舍 | 游戏规则取舍归对应系统设计稿，全局结构取舍归架构设计案，类型实现取舍归对应代码设计案 |')
decision = between(linked, '## 5. 游戏规则、技术设计与规范的边界', '## 二、NR-03')
s = splice(s, '## 5. 不擅自设计', '# 三、冲突优先级', decision + '\n\n---')
updated['01'] = date(s)

# NR-03: keep game-writing requirements, replace the six-stage boundary chapter.
s = originals['03']
s = once(s, '至于用 Dictionary、数据库还是 Addressables，由架构阶段决定。', '全局机制和公共约束由架构设计确定；具体类型的数据结构、技术接口及局部实现选择由代码设计确定，分别按两类规范执行。')
scope = between(linked, '本章对游戏设计正文的举例处理和未决内容要求，', '### 3. 整体替换第七章')
s = once(s, '# 七、六层文档的职责边界', scope + '\n\n---\n\n# 七、六层文档的职责边界')
chapter = between(linked, '# 七、六层文档的职责边界', '### 4. 同步引用')
s = splice(s, '# 七、六层文档的职责边界', '# 八、系统设计稿的写法', chapter + '\n\n---')
s = once(s, '重大取舍必须登记 上游设计稿与架构设计案。「不做」与「砍掉」须记录理由与复活条件，「悬置」须记录到期日。', '游戏规则的重大取舍登记到对应系统设计稿，全局结构取舍登记到架构设计案，代码技术取舍登记到对应实现总览或类型稿。游戏设计中的「不做」与「砍掉」须记录理由与复活条件，「悬置」须记录到期日。')
updated['03'] = date(s)

# NR-05: physical organization, type naming and transition; source boundaries.
s = originals['05']
s = once(s, '| 适用范围 | `系统设计文档/` 设计文档库；`Output/` 的分析、方案与归档类文档；`Report/` 的任务报告 |', '| 适用范围 | `系统设计文档/`、`架构设计文档/`、`Code_Design/`；`Output/` 的分析、方案与归档类文档；`Report/` 的任务报告 |')
s = once(s, '按系统编制、持续维护的程序实现规格', '按程序模块与类型组织、持续维护的技术实施规格')
s = once(s, '| 代码设计案库 | 某个系统在程序里有什么、负责什么、依赖什么 |', '| 代码设计案库 | 类型、实例、成员、装配、技术机制与独立实施契约 |')
s = once(s, '三者各自的文档不重复对方的内容。', '三者分别拥有本层定义权；允许按既定来源整理实施所需的只读摘录，摘录要求见《代码设计案编辑规范》第十二章。')
chapter = between(linked, '# 七、代码设计案库的组织', '### 3. 补充 §四.7')
s = splice(s, '# 七、代码设计案库的组织', '# 八、架构设计案库的组织', chapter + '\n\n---')
excerpt_scope = between(linked, '引用边界约束权威定义的依赖方向。', '## 四、NR-07')
s = once(s, '## 8. 过程编号不进设计文档', excerpt_scope + '\n\n## 8. 过程编号不进设计文档')
updated['05'] = date(s)

# NR-07: technical choice timing, algorithm boundary and type-based counterpart.
s = originals['07']
replacement = between(linked, '全局公共机制和统一入口在架构中确定。', '### 2. 修改 §四 禁止项表')
s = once(s, '具体的第三方技术选型可以留到实际技术方案，但「程序需要统一经过某个基础设施」这一条属于架构约束。', replacement)
s = once(s, '| 3 | 描述具体算法 | 出现遍历、深度优先搜索这类执行步骤 | 该项判定为伪代码设计的内容 |', '| 3 | 展开函数体 | 逐行描述某类型方法的全部执行步骤 | 架构确定跨模块协作与全局策略；类型的必要算法选择由代码设计确定，方法体由伪代码展开 |')
s = once(s, '第 4 项的判据是「这个选择是否对全部系统成立」。对全部系统成立的是架构约束，只对某一个系统成立的是实现选择。', '全局统一的技术形式可以由架构确定；只影响局部类型的实现选择由代码设计确定，不因其具体而视为越界。')
handoff = between(linked, '架构设计规定全局结构与公共入口约束；', '### 4. 整体替换 §八.4')
s = splice(s, '举例说明三层如何衔接：', '## 2. 代码设计案的服从要求', handoff)
counterpart = between(linked, '架构设计案提供全局约束。代码设计案按实际类型组织，', '## 五、规范索引与交叉引用')
s = splice(s, '架构设计案是单份全局文档，代码设计案是每系统一份，', '## 5. 落定后的同步', counterpart)
s = once(s, '架构设计案的目录组织见本文第十二章与', '架构设计案的目录组织见本文第八章与')
s = once(s, '| 9 | 未出现游戏规则、单系统接口清单、具体算法 |', '| 9 | 未重新定义游戏规则、未展开单系统全部接口或逐行函数体 |')
s = once(s, '| 2 | 未出现游戏规则、单系统接口清单、具体算法 |', '| 2 | 未重新定义游戏规则、未展开单系统全部接口或逐行函数体 |')
updated['07'] = date(s)

# Ancillary active descriptions and method-contract chapter references.
s = once(originals['04'], '代码设计案的章节结构、契约模板与验收标准', '类型与实例设计、准确契约、独立分发及验收')
updated['04'] = date(s)
s = once(originals['08'], '《文档库组织规范》§二.6；《代码设计案编辑规范》§六', '《文档库组织规范》§二.6；《代码设计案编辑规范》§八、§九')
s = once(s, '函数契约的输入输出四类划分由《代码设计案编辑规范》§六、§七 规定', '成员契约与调用、事件协议由《代码设计案编辑规范》§八、§九 规定')
s = once(s, '界面取数与提交接口的函数契约按该规范 §六、§七 编写', '界面取数与提交接口的成员契约及交互协议按该规范 §八、§九 编写')
updated['08'] = date(s)

# Index: update live routing; keep historical rows intact and append adoption record.
s = originals['index']
old = '| NR-06 | 代码设计案编辑规范 | `Rules/06_代码设计案编辑规范.md` | 编制、修订或评审 `Code_Design/` 下的代码设计案 | 任务涉及程序契约、接口契约、数据所有权、外部依赖或伪代码上游 | 生效 | 2026-10-06 | 2026-10-06 |'
new = f'| NR-06 | 代码设计案编辑规范 | `Rules/06_代码设计案编辑规范.md` | 类型、实例、成员、技术机制、共用契约与单类独立实施设计 | 任务涉及类拆分、实例装配、技术选型、准确契约或独立分发 | 生效 | {DATE} | {DATE} |'
s = once(s, old, new)
for number in ['01', '03', '04', '05', '07', '08']:
    pattern = rf'(?m)^(\| NR-{number} \|[^\n]*\| )2026-10-\d{{2}}( \|)$'
    s, count = re.subn(pattern, lambda m: m[1] + DATE + m[2], s)
    if count != 1:
        raise ValueError(f'Index date row NR-{number}: {count}')
s = once(s, 'NR-06 给出章节模板、函数契约模板、依赖表与验收标准；文档落点由 NR-05 第七章约束；架构设计案已定稿时须先按其核对', 'NR-06 规定实现总览、类型稿、共用契约、独立分发与验收；NR-05 第七章规定目录与索引；架构约束按 NR-07 核对')
s = once(s, '界面侧接口契约由 NR-06 §六、§七 约束', '界面侧成员与交互契约由 NR-06 §八、§九 约束')
s = once(s, '含内容归属矩阵与各层禁止项', '含内容归属与各层边界')
signal_table = between(linked, '| 把系统规则与架构转化为实施设计 |', '### 2. NR-08 的引用')
new_signals = '## 3. NR-06 代码设计案编辑规范\n\n| 触发信号 | 追加阅读 |\n| --- | --- |\n' + signal_table
s = splice(s, '## 3. NR-06 代码设计案编辑规范', '## 4. NR-05 文档库组织规范', new_signals)
s = once(s, '| 代码设计案定义与模板 | `Task/06-任务规范增加.md` | 代码设计案的定义、功能边界、系统章节标准模板、外部依赖表、编号与依赖对象索引、验收标准 | 已由 NR-06 全篇承接；六层边界并入 NR-03 §七 |', '| 代码设计案定义与模板的历史来源 | `Task/06-任务规范增加.md` | 初期系统级契约与模板 | 历史参考；现行类型级实施规范以 NR-06 为准，阶段边界见 NR-03 §七 |')
s = once(s, '两维关系并入 NR-03 §七', '输入关系并入 NR-03 §七')
retired = '| 2026-10-17 | NR-06 的系统级实施单位、技术形式禁令、旧十节模板与一一对应要求 | 整体重构 | 不能支撑类型、实例与技术实施设计及单类独立分发 | NR-06 全篇；NR-01 §二、NR-03 §七、NR-05 §七、NR-07 §六与§八 |\n\n'
s = once(s, '\n历史原文与改动通过 git 提交记录追溯。', retired + '历史原文与改动通过 git 提交记录追溯。')
s = s.rstrip() + '\n| v12 | 2026-10-17 | 整体替换 NR-06；联动 NR-01、NR-03、NR-05、NR-07 的阶段分工与目录要求，更新 NR-04、NR-08 及入口、索引和章节路由 | 用户确认第三步正文及联动修订稿并要求替换 Rules；类型与实例实施设计、准确契约和单类独立分发成为现行要求 |\n'
updated['index'] = date(s)

# BaseRules remains a pointer, with current description updated, history preserved.
s = originals['base']
s = once(s, '系统章节标准结构、函数契约模板、输入输出四类划分、外部依赖表、编号与依赖对象索引、功能与实现要求、验收标准、文档组织', '类型与实例设计、准确成员契约、技术选型、独立分发、内容模板与实施验收')
updated['base'] = s

# All anchors have passed. No originals or manual history copies are written.
for key, content in updated.items():
    if content == originals[key]:
        raise ValueError(f'No planned change for {key}')
    if len(content) < 500:
        raise ValueError(f'Unexpected short document: {key}')
assert '候选正文' not in updated['06']
assert '一个类 = 一个章节' not in updated['06']
protected = (ROOT / 'Rules' / '02_任务执行规范.md').read_bytes()
for key, content in updated.items():
    path = ROOT / 'Rules' / names[key]
    raw = path.read_bytes()
    newline = '\r\n' if b'\r\n' in raw else '\n'
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    path.write_bytes(bom + content.replace('\n', newline).encode('utf-8'))
assert protected == (ROOT / 'Rules' / '02_任务执行规范.md').read_bytes()
print(json.dumps({'baseline': baseline, 'changed': [f'Rules/{names[k]}' for k in updated], 'nr02_unchanged': True}, ensure_ascii=False, indent=2))
