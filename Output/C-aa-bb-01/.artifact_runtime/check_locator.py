"""只读探针：确认决策库可被填写器的库发现机制识别，并核对缺口数与候选数。"""
import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "..", "Tool", "缺口决策系统", "建库工具")))

import db_locator  # noqa: E402

found = []
for name in dir(db_locator):
    if "discover" in name.lower() or "list" in name.lower() or "find" in name.lower():
        found.append(name)
print("db_locator 可用入口：", found)

for name in found:
    func = getattr(db_locator, name)
    if not callable(func):
        continue
    try:
        result = func()
    except TypeError:
        continue
    text = repr(result)
    hit = [line for line in text.split(",") if "C-aa-bb-01" in line]
    print("%s -> 命中 %d 条" % (name, len(hit)))
    for line in hit:
        print("   ", line.strip()[:160])
