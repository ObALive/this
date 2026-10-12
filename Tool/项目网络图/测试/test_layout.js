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
  "手工挪位叠加在自动坐标上",
  layout2.positions.get("n1").x === layout.positions.get("n1").x + 30 &&
    layout2.positions.get("n1").y === layout.positions.get("n1").y - 12
);

const lines = PN.wrapSummary("禁行地块，部分瓦片地图纹理笔刷设置禁止通过", 15, 2);
check("概要折行不超过两行", lines.length <= 2);
const longLines = PN.wrapSummary("这是一段非常非常非常漫长的实现目标概要描述文字用于测试截断", 8, 2);
check("超长概要截断并加省略号", longLines.length === 2 && longLines[1].endsWith("…"));

check("同根路线颜色一致", PN.routeColor("s1", sampleModel().sections) === PN.routeColor("s1", sampleModel().sections));
check("不同路线颜色不同", PN.routeColor("s1", sampleModel().sections) !== PN.routeColor("s2", sampleModel().sections));

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
