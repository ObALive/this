/* 前端冒烟测试：用一个极简 DOM 垫片加载 index.html + app.js，
 * 通过真实 HTTP 接口跑一遍「载入 → 渲染 → 打开详情框 → 读字段」的路径。
 * 运行： node Tool/项目网络图/测试/smoke_dom.js [baseUrl]
 * 需要先启动服务：python3 Tool/项目网络图/server.py --no-browser
 */
"use strict";

const fs = require("fs");
const path = require("path");

const BASE = process.argv[2] || "http://127.0.0.1:8791";
const TOOL = path.join(__dirname, "..");

let passed = 0;
let failed = 0;
function check(name, condition, detail) {
  if (condition) {
    passed += 1;
    console.log("  ok   " + name);
  } else {
    failed += 1;
    console.log("  FAIL " + name + (detail !== undefined ? " -> " + detail : ""));
  }
}

// ------------------------------------------------------------ 极简 DOM
const VOID_TAGS = new Set(["meta", "link", "br", "hr", "img", "input", "source"]);

class ClassList {
  constructor(el) { this.el = el; this.set = new Set(); }
  add(...names) { names.forEach((n) => n && this.set.add(n)); this._sync(); }
  remove(...names) { names.forEach((n) => this.set.delete(n)); this._sync(); }
  contains(name) { return this.set.has(name); }
  toggle(name, force) {
    const on = force === undefined ? !this.set.has(name) : !!force;
    if (on) this.set.add(name); else this.set.delete(name);
    this._sync();
    return on;
  }
  _sync() { this.el._className = [...this.set].join(" "); }
  _fromString(value) {
    this.set = new Set(String(value || "").split(/\s+/).filter(Boolean));
    this.el._className = [...this.set].join(" ");
  }
}

class Element {
  constructor(tag) {
    this.tagName = String(tag).toLowerCase();
    this.children = [];
    this.parent = null;
    this.attributes = {};
    this.dataset = {};
    this.style = {};
    this._texts = [];
    this._listeners = {};
    this.classList = new ClassList(this);
    this._className = "";
    this.hidden = false;
    this.open = false;
    this.scrollTop = 0;
    this._props = {};
  }
  get className() { return this._className; }
  set className(value) { this.classList._fromString(value); }
  get id() { return this.attributes.id || ""; }
  get firstChild() { return this.children[0] || null; }
  get lastChild() { return this.children[this.children.length - 1] || null; }
  get textContent() { return this._texts.join("") + this.children.map((c) => c.textContent).join(""); }
  set textContent(value) {
    this.children.length = 0;
    this._texts = value === "" || value === null || value === undefined ? [] : [String(value)];
  }
  append(...items) { items.forEach((i) => this.appendChild(i)); }
  appendChild(child) {
    if (child == null) return child;
    child.parent = this;
    this.children.push(child);
    return child;
  }
  remove() {
    if (this.parent) {
      const i = this.parent.children.indexOf(this);
      if (i >= 0) this.parent.children.splice(i, 1);
      this.parent = null;
    }
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === "class") this.className = value;
    if (name.startsWith("data-")) this.dataset[name.slice(5).replace(/-([a-z])/g, (m, c) => c.toUpperCase())] = String(value);
  }
  getAttribute(name) { return this.attributes[name] !== undefined ? this.attributes[name] : null; }
  addEventListener(type, fn) { (this._listeners[type] = this._listeners[type] || []).push(fn); }
  dispatch(type, ev) {
    const event = Object.assign({ type, target: this, currentTarget: this, preventDefault() {}, stopPropagation() {} }, ev || {});
    for (const fn of this._listeners[type] || []) fn(event);
  }
  getBoundingClientRect() { return { left: 0, top: 0, width: 1200, height: 800, right: 1200, bottom: 800 }; }
  setPointerCapture() {}
  releasePointerCapture() {}
  showModal() { this.open = true; }
  close() { this.open = false; this.dispatch("close"); }
  closest(selector) {
    let node = this;
    while (node) {
      if (matches(node, selector)) return node;
      node = node.parent;
    }
    return null;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  querySelectorAll(selector) {
    const out = [];
    const chain = String(selector).trim().split(/\s+/).filter(Boolean);
    const walk = (node) => {
      for (const child of node.children) {
        if (matchesChain(child, chain)) out.push(child);
        walk(child);
      }
    };
    walk(this);
    return out;
  }
  descendants() {
    const out = [];
    const walk = (node) => { for (const c of node.children) { out.push(c); walk(c); } };
    walk(this);
    return out;
  }
}

function matches(el, selector) {
  const m = /^([a-zA-Z]*)((?:\.[\w-]+)*)(?:\[data-([\w-]+)="([^"]*)"\])?$/.exec(selector.trim());
  if (!m) return false;
  const [, tag, classes, dataKey, dataValue] = m;
  if (tag && el.tagName !== tag.toLowerCase()) return false;
  for (const cls of (classes || "").split(".").filter(Boolean)) {
    if (!el.classList.contains(cls)) return false;
  }
  if (dataKey) {
    const key = dataKey.replace(/-([a-z])/g, (x, c) => c.toUpperCase());
    if (el.dataset[key] !== dataValue) return false;
  }
  return true;
}

// 支持「祖先 后代」这种带空格的选择器（只做后代匹配，够冒烟测试用）
function matchesChain(el, chain) {
  if (!matches(el, chain[chain.length - 1])) return false;
  let node = el.parent;
  for (let i = chain.length - 2; i >= 0; i -= 1) {
    let found = false;
    while (node) {
      if (matches(node, chain[i])) { found = true; node = node.parent; break; }
      node = node.parent;
    }
    if (!found) return false;
  }
  return true;
}

function parseHTML(html) {
  const root = new Element("root");
  const stack = [root];
  const token = /<!--[\s\S]*?-->|<\/?[a-zA-Z][^>]*>/g;
  let last = 0;
  let m;
  const pushText = (text) => {
    const clean = text.replace(/\s+/g, " ");
    if (clean.trim()) stack[stack.length - 1]._texts.push(clean);
  };
  while ((m = token.exec(html))) {
    pushText(html.slice(last, m.index));
    last = token.lastIndex;
    const raw = m[0];
    if (raw.startsWith("<!--")) continue;
    if (raw.startsWith("</")) {
      if (stack.length > 1) stack.pop();
      continue;
    }
    const nameMatch = /^<([a-zA-Z][\w-]*)/.exec(raw);
    const tag = nameMatch[1].toLowerCase();
    const el = new Element(tag);
    const attrRe = /([a-zA-Z_:][\w:.-]*)(?:="([^"]*)")?/g;
    let a;
    const attrPart = raw.replace(/^<[a-zA-Z][\w-]*/, "").replace(/\/?>$/, "");
    while ((a = attrRe.exec(attrPart))) {
      if (!a[1] || a[1] === "/") continue;
      el.setAttribute(a[1], a[2] === undefined ? "" : a[2]);
    }
    stack[stack.length - 1].appendChild(el);
    if (!VOID_TAGS.has(tag) && !raw.endsWith("/>")) stack.push(el);
  }
  pushText(html.slice(last));
  return root;
}

const html = fs.readFileSync(path.join(TOOL, "index.html"), "utf-8");
const domRoot = parseHTML(html);

const documentShim = {
  getElementById(id) { return domRoot.descendants().find((e) => e.id === id) || null; },
  createElement(tag) { return new Element(tag); },
  createElementNS(_ns, tag) { return new Element(tag); },
  addEventListener() {},
  querySelector(sel) { return domRoot.querySelector(sel); },
};
documentShim.body = domRoot;

global.document = documentShim;
const realFetch = global.fetch;
global.fetch = (url, opts) => realFetch(new URL(url, BASE).toString(), opts);
global.window = global;
global.window.confirm = () => true;
global.window.prompt = () => null;
global.window.addEventListener = () => {};
try {
  global.navigator = Object.assign({}, global.navigator, { clipboard: { writeText: async () => {} } });
} catch (err) {
  Object.defineProperty(global, "navigator", { value: { clipboard: { writeText: async () => {} } }, configurable: true });
}

// ------------------------------------------------------------ 载入前端
require(path.join(TOOL, "graph.js"));
require(path.join(TOOL, "app.js"));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  await sleep(900);
  const byId = (id) => documentShim.getElementById(id);
  // 期望值全部由接口现算，避免内容增删后测试数字过期
  const stateData = await (await fetch("/api/state")).json();
  const model = stateData.model;
  const rootIds = new Set(
    model.sections.map((s) => {
      let cur = s;
      const seen = new Set();
      while (cur && cur.parent_id && !seen.has(cur.id)) {
        seen.add(cur.id);
        cur = model.sections.find((x) => x.id === cur.parent_id);
      }
      return cur ? cur.id : s.id;
    })
  );

  const nodeEls = byId("layer-nodes").children;
  const edgeEls = byId("layer-edges").children;
  const bandEls = byId("layer-bands").children;
  check("渲染出全部节点", nodeEls.length === model.nodes.length, nodeEls.length);
  check("渲染出全部依赖边", edgeEls.length === model.edges.length, edgeEls.length);
  check("渲染出路线分组带", bandEls.length === rootIds.size, bandEls.length);
  check(
    "节点上只写章节索引与概要",
    nodeEls[0].children.filter((c) => c.tagName === "text").length === 1 + PNLayout.LAYOUT.maxSummaryLines
  );
  check("侧栏列出条目", byId("route-tree").querySelectorAll(".node-row").length === model.nodes.length);
  check("有数据时隐藏空状态遮罩", byId("empty-canvas").hidden === true);
  // 回归：作者样式里的 display 会盖掉 [hidden]，必须有显式兜底
  const css = fs.readFileSync(path.join(TOOL, "app.css"), "utf-8");
  check("样式表为 [hidden] 提供兜底", /\[hidden\]\s*\{[^}]*display:\s*none/.test(css));
  check(
    "侧栏覆盖全部路线",
    byId("route-tree").querySelectorAll(".route").length +
      byId("route-tree").querySelectorAll(".route-root").length === model.sections.length
  );
  check("校验面板有内容", byId("issue-list").querySelectorAll(".issue").length > 0);
  const expectedHeads = model.sections.filter(
    (s) => s.node_ids.length > 0 || !model.sections.some((c) => c.parent_id === s.id)
  ).length;
  check("列头覆盖带条目的路线与空的叶子路线", byId("layer-heads").children.length === expectedHeads, byId("layer-heads").children.length);
  check("对象索引列出对象", byId("object-list").querySelectorAll(".object-item").length === model.stats.objects);
  check("对象计数正确", byId("object-counter").textContent === String(model.stats.objects), byId("object-counter").textContent);

  // 打开某个节点的详情框
  const rows = byId("route-tree").querySelectorAll(".node-row");
  const row = rows.find((r) => r.textContent.includes("场景道具摆放")) || rows[0];
  row.dispatch("click");
  const dialog = byId("node-dialog");
  check("点击条目打开详情编辑框", dialog.open === true);
  check("详情框填了概要", byId("nd-summary").value.length > 0, byId("nd-summary").value);
  check("详情框填了正文", byId("nd-body").value.length > 0);
  const objNode = model.nodes.find((n) => String(n.summary).indexOf("场景道具摆放") >= 0);
  if (objNode) {
    check(
      "详情框列出对象行",
      byId("nd-objs").querySelectorAll('.row[data-role="obj"]').length === objNode.objects.length
    );
  } else {
    check("详情框列出对象行", false, "未找到「场景道具摆放」条目");
  }
  check("其中一条带备注", byId("nd-objs").querySelectorAll(".obj-note").some((i) => i.value.length > 0));
  const objRowEls = byId("nd-objs").querySelectorAll('.row[data-role="obj"]');
  check(
    "实现路径是可调高度的文本框",
    objRowEls.length > 0 && objRowEls.every((r) => r.querySelector(".obj-path").tagName === "textarea")
  );
  check(
    "对象说明也是文本框",
    objRowEls.length > 0 && objRowEls.every((r) => r.querySelector(".obj-note").tagName === "textarea")
  );

  // 设计说明归位：说明里点名了程序对象的节点，不该再出现「设计方式说明」分组
  const proseNode = model.nodes.find((n) => String(n.summary).indexOf("禁行地块") >= 0);
  if (proseNode && proseNode.notes.length === 0) {
    const proseRow = rows.find((r) => r.textContent.indexOf("禁行地块") >= 0);
    if (proseRow) {
      proseRow.dispatch("click");
      check("点名对象的说明不再单立「设计方式说明」", byId("nd-notes-group").hidden === true);
      check(
        "说明已归到对象下（含 Manager 标识符）",
        byId("nd-objs").querySelectorAll(".obj-name").some((i) => /Manager/i.test(i.value)),
        byId("nd-objs").querySelectorAll(".obj-name").map((i) => i.value).join("/")
      );
      check(
        "对象里带着原正文（说明或实现路径）",
        byId("nd-objs").querySelectorAll('.row[data-role="obj"]').some((r) =>
          (r.querySelector(".obj-note").value + "\n" + r.querySelector(".obj-path").value).indexOf("TilemapManager") >= 0
        )
      );
    }
  } else {
    check("点名对象的说明不再单立「设计方式说明」", true, "当前库还没做归位（服务未重启时会这样）");
  }

  // 打开一个带依赖的节点
  const depRow = rows.find((r) => r.textContent.includes("禁行地块"));
  depRow.dispatch("click");
  const depNode = model.nodes.find((n) => String(n.summary).indexOf("禁行地块") >= 0);
  const refs = byId("nd-refs").querySelectorAll('.row[data-role="ref"]');
  check("详情框列出依赖行", refs.length === (depNode ? depNode.refs.length : 1), refs.length);
  check("依赖行显示已解析", refs[0].querySelector(".pill").textContent === "已解析");
  // 下拉里除全部条目外，还有一个「自动按依赖文本解析」的空值项
  check(
    "依赖下拉可选到全部条目",
    refs[0].querySelectorAll("option").length === model.nodes.length + 1,
    refs[0].querySelectorAll("option").length
  );

  // 添加/删除依赖行、对象行
  byId("nd-add-ref").dispatch("click");
  check("可以添加依赖行", byId("nd-refs").querySelectorAll('.row[data-role="ref"]').length === 2);
  byId("nd-refs").querySelectorAll('.row[data-role="ref"]')[1].querySelector(".del").dispatch("click");
  check("可以删除依赖行", byId("nd-refs").querySelectorAll('.row[data-role="ref"]').length === 1);

  const objCountBefore = byId("nd-objs").querySelectorAll('.row[data-role="obj"]').length;
  byId("nd-add-obj").dispatch("click");
  const objRows = byId("nd-objs").querySelectorAll('.row[data-role="obj"]');
  check("可以添加对象行", objRows.length === objCountBefore + 1, objRows.length);
  objRows[objRows.length - 1].querySelector(".del").dispatch("click");
  check("可以删除对象行", byId("nd-objs").querySelectorAll('.row[data-role="obj"]').length === objCountBefore);

  // 保存（不改动内容）
  byId("nd-save").dispatch("click");
  await sleep(500);
  check("保存后详情框关闭", dialog.open === false);
  check("保存后节点数不变", byId("layer-nodes").children.length === model.nodes.length);

  // 侧栏高亮联动
  rows[0].dispatch("mouseenter");
  check("悬停时其余节点变暗", byId("layer-nodes").children.some((c) => c.classList.contains("dim")));
  rows[0].dispatch("mouseleave");
  check("离开后恢复", !byId("layer-nodes").children.some((c) => c.classList.contains("dim")));

  // 校验面板点击可打开对应条目
  const issue = byId("issue-list").querySelector(".issue");
  if (issue && issue.textContent.includes("元效果")) {
    issue.dispatch("click");
    check("点击校验项打开对应条目", byId("node-dialog").open === true);
    byId("nd-close").dispatch("click");
  } else {
    check("点击校验项打开对应条目", false, "未找到元效果校验项");
  }

  // ---- 子路线：在已有路线下新增一条三级路线，跑完还原，避免污染数据 ----
  const parentSection = model.sections.find((s) => s.parent_id) || null;
  if (!parentSection) {
    check("存在可加子路线的路线", false, "当前数据里没有带父级的路线");
  } else {
    const newTitle = "冒烟测试子路线";
    const blocks = byId("route-tree").querySelectorAll(".route");
    const parentBlock =
      blocks.find((b) => b.querySelector(".route-title") && b.querySelector(".route-title").textContent === parentSection.title) ||
      blocks[0];
    const addChildBtn =
      parentBlock &&
      parentBlock.querySelectorAll(".route-actions button").find((b) => String(b.title).indexOf("新增子路线") >= 0);
    check("路线标题栏有「新增子路线」入口", !!addChildBtn);
    if (addChildBtn) {
      window.prompt = () => newTitle;
      addChildBtn.dispatch("click");
      await sleep(700);
      const after = (await (await fetch("/api/state")).json()).model;
      const created = after.sections.find((s) => s.title === newTitle);
      check("子路线已创建", !!created);
      if (created) {
        check("子路线挂在所选路线下", created.parent_id === parentSection.id, created.parent_id);
        check("子路线层级为父级 + 1", created.level === parentSection.level + 1, created.level);
        check("子路线路径包含父级", String(created.path).indexOf(parentSection.title) >= 0, created.path);
        check(
          "侧栏出现三级路线",
          byId("route-tree").querySelectorAll(".route-title").some((t) => t.textContent === newTitle)
        );
        check(
          "画布出现该路线的列头",
          byId("layer-heads").children.some((g) => g.children[0] && g.children[0].textContent === newTitle)
        );
      }
      // 还原到测试开始前的模型
      await fetch("/api/op", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ op: "replace", args: { model } }),
      });
      await sleep(500);
      const restored = (await (await fetch("/api/state")).json()).model;
      check("测试后数据已还原", !restored.sections.some((s) => s.title === newTitle));
    }
  }

  // ---- 删除最后一条依赖：删完不能立刻从旧模型复活（跑完还原）----
  const oneRefNode = model.nodes.find((n) => n.refs.length === 1) || null;
  if (!oneRefNode) {
    check("存在只有一条依赖的条目", false, "当前数据里没有单依赖条目");
  } else {
    const g = byId("layer-nodes").children.find((el) => el.dataset.id === oneRefNode.id);
    check("能在画布上找到该节点", !!g);
    if (g) {
      g.dispatch("pointerdown", { button: 0, clientX: 120, clientY: 120, pointerId: 1 });
      byId("canvas").dispatch("pointerup", { clientX: 120, clientY: 120, pointerId: 1 });
      const before = byId("nd-refs").querySelectorAll('.row[data-role="ref"]').length;
      check("详情框里正好一条依赖", before === 1, before);
      byId("nd-refs").querySelector('.row[data-role="ref"]').querySelector(".del").dispatch("click");
      check(
        "删掉最后一条依赖后不会复活",
        byId("nd-refs").querySelectorAll('.row[data-role="ref"]').length === 0,
        byId("nd-refs").querySelectorAll('.row[data-role="ref"]').length
      );
      check("删空后显示占位提示", !!byId("nd-refs").querySelector(".hint"));
      byId("nd-save").dispatch("click");
      await sleep(700);
      const after = (await (await fetch("/api/state")).json()).model;
      const saved = after.nodes.find((n) => n.id === oneRefNode.id);
      check("保存后依赖确实从库里删掉了", saved.refs.length === 0, JSON.stringify(saved.refs));
      // 还原
      await fetch("/api/op", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ op: "replace", args: { model } }),
      });
      await sleep(500);
      const restored = (await (await fetch("/api/state")).json()).model;
      check("测试后依赖已还原", restored.nodes.find((n) => n.id === oneRefNode.id).refs.length === 1);
    }
  }

  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})().catch((err) => {
  console.error("冒烟测试异常：", err);
  process.exit(2);
});
