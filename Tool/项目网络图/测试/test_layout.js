/* 布局模块的纯函数测试：node Tool/项目网络图/测试/test_layout.js */
"use strict";

const path = require("path");
const PN = require(path.join(__dirname, "..", "graph.js"));

let passed = 0;
let failed = 0;

function check(name, condition, detail) {
  if (condition) {
    passed += 1;
    console.log("  ok   " + name);
  } else {
    failed += 1;
    console.log("  FAIL " + name + (detail ? " -> " + detail : ""));
  }
}

function sampleModel() {
  const sections = [
    { id: "s1", title: "瓦片地图", parent_id: null, node_ids: ["n1", "n2", "n3"] },
    { id: "s2", title: "角色移动", parent_id: null, node_ids: ["n4", "n5"] },
  ];
  const nodes = [
    { id: "n1", section_id: "s1", number: 1, index_label: "瓦片地图 1", summary: "平铺的地图绘制", refs: [] },
    { id: "n2", section_id: "s1", number: 2, index_label: "瓦片地图 2", summary: "禁行地块", refs: [{ resolved: true }] },
    { id: "n3", section_id: "s1", number: 3, index_label: "瓦片地图 3", summary: "场景道具摆放", refs: [{ resolved: false, reason: "x" }] },
    { id: "n4", section_id: "s2", number: 0, index_label: "角色移动 0", summary: "元对象约定", refs: [] },
    { id: "n5", section_id: "s2", number: 1, index_label: "角色移动 1", summary: "点击地格", refs: [] },
  ];
  const edges = [
    { from: "n1", to: "n2", kind: "chain" },
    { from: "n2", to: "n3", kind: "chain" },
    { from: "n4", to: "n5", kind: "chain" },
    { from: "n5", to: "n1", kind: "explicit", raw: "地图1" },
  ];
  return { sections, nodes, edges };
}

const layout = PN.computeLayout(sampleModel());

check("列数等于路线数", layout.columns.length === 2);
check("同列内条目纵向顺排", layout.positions.get("n1").y < layout.positions.get("n2").y);
check("跨列横坐标递增", layout.positions.get("n1").x < layout.positions.get("n4").x);
check("列内编号不连续也能定位", layout.positions.get("n4").row === 0 && layout.positions.get("n5").row === 1);
check("相邻条目走直线", /^M [\d.]+ [\d.]+ L [\d.]+ [\d.]+$/.test(layout.edges.find((e) => e.from === "n1").d));
check("跨列依赖走曲线", layout.edges.find((e) => e.kind === "explicit").d.includes("C"));
check("未解析依赖被标记在节点上", layout.positions.get("n3").has_error === true);
check("已解析依赖不标记", layout.positions.get("n2").has_error === false);
check("画布尺寸覆盖所有节点", layout.width > 0 && layout.height > 0);

const manualModel = sampleModel();
manualModel.nodes[0].manual = { dx: 30, dy: -12 };
const layout2 = PN.computeLayout(manualModel);
check(
  "横向偏移保留，向上偏移不能越过依赖",
  layout2.positions.get("n1").x === layout.positions.get("n1").x + 30 &&
    layout2.positions.get("n1").y === layout.positions.get("n1").y
);

// 核心约束直接检查节点矩形的上下边界，不依赖布局算法的实现步骤。
function dependenciesBelow(model, result) {
  return model.edges.every((edge) => {
    const from = result.positions.get(edge.from);
    const to = result.positions.get(edge.to);
    return !from || !to || to.y >= from.y + from.h + result.options.gapY;
  });
}
check("所有直接依赖都在依赖者上方", dependenciesBelow(sampleModel(), layout));
check("跨路线前置会推迟整条后续路线", layout.positions.get("n1").y >= layout.positions.get("n5").y + layout.positions.get("n5").h + layout.options.gapY);

const dependencyModel = {
  sections: [
    { id: "a", title: "依赖者", node_ids: ["a0", "a1", "a2"] },
    { id: "b", title: "前置路线一", node_ids: ["b0", "b1"] },
    { id: "c", title: "前置路线二", node_ids: ["c0", "c1"] },
    { id: "d", title: "并行路线", node_ids: ["d0"] },
  ],
  nodes: ["a0", "a1", "a2", "b0", "b1", "c0", "c1", "d0"].map((id) => ({
    id, summary: id === "c1" ? "较高的前置节点".repeat(12) : id, refs: [],
  })),
  edges: [
    { from: "a0", to: "a1", kind: "chain" },
    { from: "a1", to: "a2", kind: "chain" },
    { from: "b0", to: "b1", kind: "chain" },
    { from: "c0", to: "c1", kind: "chain" },
    { from: "b1", to: "a0", kind: "explicit" },
    { from: "c1", to: "a0", kind: "explicit" },
    { from: "b0", to: "d0", kind: "explicit" },
  ],
};
const depLayout = PN.computeLayout(dependencyModel);
const latestDependency = depLayout.positions.get("c1");
check("多个依赖按最靠下节点的底部排布", depLayout.positions.get("a0").y === latestDependency.y + latestDependency.h + depLayout.options.gapY);
check("不同高度、多前置、多层依赖均满足上下约束", dependenciesBelow(dependencyModel, depLayout));
check("无依赖节点在顶部并行开始", depLayout.positions.get("b0").y === depLayout.options.padTop && depLayout.positions.get("c0").y === depLayout.options.padTop);
check("并行分支不等待无关路线", depLayout.positions.get("d0").y === depLayout.positions.get("b1").y && depLayout.positions.get("d0").y < depLayout.positions.get("a0").y);
check("重新排布后画布覆盖全部节点", [...depLayout.positions.values()].every((p) => depLayout.height >= p.y + p.h + depLayout.options.padBottom));
check("列底部反映依赖排布后的实际位置", depLayout.columns.every((column) => column.bottom === Math.max(...column.nodeIds.map((id) => { const p = depLayout.positions.get(id); return p.y + p.h; }))));

const shuffled = JSON.parse(JSON.stringify(dependencyModel));
shuffled.sections.reverse();
shuffled.nodes.reverse();
shuffled.edges.reverse();
const shuffledLayout = PN.computeLayout(shuffled);
check("路线、节点和边的遍历顺序不影响纵坐标", [...depLayout.positions].every(([id, p]) => shuffledLayout.positions.get(id).y === p.y));

const shifted = JSON.parse(JSON.stringify(dependencyModel));
shifted.nodes.find((n) => n.id === "c1").manual = { dy: 200 };
shifted.nodes.find((n) => n.id === "a0").manual = { dx: 40, dy: -2000 };
const shiftedLayout = PN.computeLayout(shifted);
check("前置向下微调后后续节点随之下移", shiftedLayout.positions.get("a0").y === depLayout.positions.get("a0").y + 200 && shiftedLayout.positions.get("a2").y === depLayout.positions.get("a2").y + 200);
check("已有手工偏移不能破坏依赖顺序", dependenciesBelow(shifted, shiftedLayout));
check("手工下移计入画布高度", shiftedLayout.height === depLayout.height + 200);
check("拖动依赖者不能越过前置", PN.constrainNodeY(depLayout, "a0", -1000) === depLayout.positions.get("a0").y);
check("拖动前置不能越过后续节点", PN.constrainNodeY(depLayout, "c1", 100000) === depLayout.positions.get("c1").y);
check("末端节点允许向下拖动", PN.constrainNodeY(depLayout, "a2", 100000) === 100000);
const freeSpace = shiftedLayout.positions.get("c0").y + 20;
check("有空隙时允许纵向微调", PN.constrainNodeY(shiftedLayout, "c0", freeSpace) === freeSpace);

const invalidEdges = JSON.parse(JSON.stringify(dependencyModel));
invalidEdges.edges.push(invalidEdges.edges[0], { from: "missing", to: "a0", kind: "explicit" });
const invalidLayout = PN.computeLayout(invalidEdges);
check("重复边和缺失节点不影响布局", [...depLayout.positions].every(([id, p]) => invalidLayout.positions.get(id).y === p.y) && invalidLayout.edges.length === dependencyModel.edges.length);

const cyclicModel = {
  sections: [
    { id: "x", title: "环一", node_ids: ["x"] },
    { id: "y", title: "环二", node_ids: ["y"] },
    { id: "z", title: "环的下游", node_ids: ["z"] },
  ],
  nodes: ["x", "y", "z"].map((id) => ({ id, summary: id })),
  edges: [
    { from: "x", to: "y", kind: "explicit" },
    { from: "y", to: "x", kind: "explicit" },
    { from: "y", to: "z", kind: "explicit" },
  ],
};
const cycleLayout = PN.computeLayout(cyclicModel);
check("依赖环不会无限扩展或阻止绘图", [...cycleLayout.positions.values()].every((p) => Number.isFinite(p.y)) && cycleLayout.constraints.some((c) => c.cyclic));
check("环外的直接依赖仍满足上下约束", cycleLayout.positions.get("z").y >= cycleLayout.positions.get("y").y + cycleLayout.positions.get("y").h + cycleLayout.options.gapY);
const selfModel = { sections: [{ id: "s", node_ids: ["self"] }], nodes: [{ id: "self" }], edges: [{ from: "self", to: "self" }] };
check("自身依赖有有限的回退位置", Number.isFinite(PN.computeLayout(selfModel).positions.get("self").y));
const emptyLayout = PN.computeLayout({});
check("空图仍能绘制", emptyLayout.positions.size === 0 && emptyLayout.height > 0 && emptyLayout.width > 0);

// 深依赖链：第一列的起点依赖第二列的最后一项。
const deepIds = Array.from({ length: 6000 }, (_, i) => `deep-${i}`);
const deepModel = {
  sections: [{ id: "first", node_ids: ["end"] }, { id: "long", node_ids: deepIds }],
  nodes: ["end", ...deepIds].map((id) => ({ id, summary: id })),
  edges: [{ from: deepIds[deepIds.length - 1], to: "end", kind: "explicit" }],
};
const deepLayout = PN.computeLayout(deepModel);
check("六千项深依赖链不溢出", Number.isFinite(deepLayout.height) && deepLayout.positions.get("end").y > deepLayout.positions.get(deepIds[deepIds.length - 1]).y);

const lines = PN.wrapSummary("禁行地块，部分瓦片地图纹理笔刷设置禁止通过", 15, 2);
check("概要折行不超过两行", lines.length <= 2);
const longLines = PN.wrapSummary("这是一段非常非常非常漫长的实现目标概要描述文字用于测试截断", 8, 2);
check("超长概要截断并加省略号", longLines.length === 2 && longLines[1].endsWith("…"));

// 版面：节点更窄、高度随文字自适应、同列纵向间距为原来的三倍
const OLD_GAP_Y = 26;
const OLD_COL_WIDTH = 232;
const heightModel = {
  sections: [{ id: "s1", title: "瓦片地图", parent_id: null, node_ids: ["a", "b", "c"] }],
  nodes: [
    { id: "a", section_id: "s1", number: 1, index_label: "瓦片地图 1", summary: "平铺的地图绘制", refs: [] },
    { id: "b", section_id: "s1", number: 2, index_label: "瓦片地图 2", summary: "禁行地块，部分瓦片地图纹理笔刷设置禁止通过", refs: [] },
    { id: "c", section_id: "s1", number: 3, index_label: "瓦片地图 3", summary: "场景道具摆放。当部分场景道具摆放到地图上的时候，摆放位置自动设置不可移动，且设置多个角色不可处于同一格", refs: [] },
  ],
  edges: [],
};
const hLayout = PN.computeLayout(heightModel);
const na = hLayout.positions.get("a");
const nb = hLayout.positions.get("b");
const nc = hLayout.positions.get("c");
check("节点宽度已收窄", na.w === hLayout.options.colWidth && na.w < OLD_COL_WIDTH, na.w);
check("纵向间距为原来的三倍", hLayout.options.gapY === OLD_GAP_Y * 3, hLayout.options.gapY);
check(
  "节点高度随概要行数自适应",
  na.lines.length === 1 && nb.lines.length === 2 && nc.lines.length >= 3 &&
    na.h < nb.h && nb.h < nc.h,
  [na.h, nb.h, nc.h].join("/")
);
check(
  "高度等于行数公式值",
  na.h === PN.nodeHeightFor(1) && nb.h === PN.nodeHeightFor(2) && nc.h === PN.nodeHeightFor(nc.lines.length)
);
check("同列节点依次排在间距之后", nb.y === na.y + na.h + hLayout.options.gapY && nc.y === nb.y + nb.h + hLayout.options.gapY);
check("画布高度覆盖最后一个节点", hLayout.height === nc.y + nc.h + hLayout.options.padBottom, hLayout.height);
check("单行节点不低于最小高度", na.h >= hLayout.options.minHeight);
check("超宽章节索引被截断", PN.truncateText("角色行为/角色移动/子路线 12", 10).endsWith("…"));
check("未超宽章节索引保持原文", PN.truncateText("瓦片地图 1", 12) === "瓦片地图 1");

// 列头与嵌套：纯分组路线不占列，空的叶子子路线要能被看到
const nestedModel = {
  sections: [
    { id: "p", title: "角色行为", parent_id: null, level: 1, path: "角色行为", node_ids: [] },
    { id: "c1", title: "角色技能", parent_id: "p", level: 2, path: "角色行为/角色技能", node_ids: ["x"] },
    { id: "c2", title: "技能子路线", parent_id: "c1", level: 3, path: "角色行为/角色技能/技能子路线", node_ids: [] },
    { id: "d", title: "时间轴", parent_id: null, level: 1, path: "时间轴", node_ids: ["y"] },
  ],
  nodes: [
    { id: "x", section_id: "c1", number: 1, index_label: "角色行为/角色技能 1", summary: "制作元技能", refs: [] },
    { id: "y", section_id: "d", number: 1, index_label: "时间轴 1", summary: "速度属性", refs: [] },
  ],
  edges: [],
};
const nLayout = PN.computeLayout(nestedModel);
check("纯分组路线不占列", nLayout.columns.length === 3, nLayout.columns.length);
check("子路线排在父级之后、同级之前", nLayout.positions.get("x").column === 0 && nLayout.columns[1].title === "技能子路线");
check("列头覆盖全部非分组路线", nLayout.heads.length === 3, nLayout.heads.length);
check("空的叶子子路线标为还没有条目", nLayout.heads.find((h) => h.title === "技能子路线").empty === true);
check("非空路线不标空", nLayout.heads.find((h) => h.title === "角色技能").empty === false);
check("列头带完整章节路径", nLayout.heads.find((h) => h.title === "技能子路线").path === "角色行为/角色技能/技能子路线");
check("列头有颜色与截断宽度", !!nLayout.heads[0].color && nLayout.heads[0].chars > 0);

check("同根路线颜色一致", PN.routeColor("s1", sampleModel().sections) === PN.routeColor("s1", sampleModel().sections));
check("不同路线颜色不同", PN.routeColor("s1", sampleModel().sections) !== PN.routeColor("s2", sampleModel().sections));

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
