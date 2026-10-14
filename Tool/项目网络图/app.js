/* 项目网络图绘制与编辑工具：前端交互与实时渲染。 */
(function () {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const state = {
    model: null,
    config: null,
    datasetId: null,
    datasetBusy: false,
    layout: null,
    view: { k: 1, tx: 0, ty: 0 },
    history: [],
    redo: [],
    editingId: null,
    nodeEls: new Map(),
    edgeEls: new Map(),
    bandEls: new Map(),
    headEls: new Map(),
    highlight: null,
    drag: null,
    pan: null,
  };

  const el = (id) => document.getElementById(id);
  const canvas = el("canvas");
  const world = el("world");
  const layerBands = el("layer-bands");
  const layerHeads = el("layer-heads");
  const layerEdges = el("layer-edges");
  const layerNodes = el("layer-nodes");

  // ---------------------------------------------------------------- 工具
  function svgEl(tag, attrs) {
    const node = document.createElementNS(SVG_NS, tag);
    if (attrs) for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    return node;
  }

  let toastTimer = null;
  function toast(message, isError) {
    const box = el("toast");
    box.textContent = message;
    box.className = "toast" + (isError ? " error" : "");
    box.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { box.hidden = true; }, isError ? 6000 : 4200);
  }

  async function api(path, options) {
    const res = await fetch(path, options);
    let data = null;
    try {
      data = await res.json();
    } catch (err) {
      throw new Error("服务返回了无法解析的内容");
    }
    if (!res.ok || data.ok === false) {
      const error = new Error(data && data.error ? data.error : `请求失败（${res.status}）`);
      if (data && data.need_confirm) error.needConfirm = data.need_confirm;
      throw error;
    }
    if (["/api/op", "/api/import", "/api/reset", "/api/export"].includes(path) && data.dataset_id !== state.datasetId) {
      throw new Error("数据已切换，请在当前数据中继续操作");
    }
    return data;
  }

  function post(path, body) {
    if (state.datasetBusy && !path.startsWith("/api/datasets/")) {
      return Promise.reject(new Error("正在切换数据，请稍后再操作"));
    }
    return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.assign({ dataset_id: state.datasetId }, body || {})) });
  }

  async function op(name, args) {
    const snapshot = state.model ? JSON.parse(JSON.stringify(state.model)) : null;
    const data = await post("/api/op", { op: name, args: args || {} });
    if (snapshot) {
      state.history.push(snapshot);
      if (state.history.length > 80) state.history.shift();
      state.redo.length = 0;
    }
    applyModel(data.model);
    if (data.log && data.log.length) toast(data.log.join("\n"));
    return data;
  }

  function applyModel(model) {
    state.model = model;
    if (!model.nodes.some((n) => n.id === state.editingId)) {
      closeDialog(el("node-dialog"));
      state.editingId = null;
    }
    render();
  }

  // ---------------------------------------------------------------- 渲染入口
  function render() {
    renderGraph();
    renderSidebar();
    const empty = !state.model.nodes.length;
    el("empty-canvas").hidden = !empty;
    el("source-label").textContent = state.model.source ? `来源：${state.model.source}` : "未指定来源";
  }

  function renderGraph() {
    const layout = PNLayout.computeLayout(state.model);
    state.layout = layout;

    // 分组带
    const seenBands = new Set();
    for (const band of layout.bands) {
      seenBands.add(band.id);
      let g = state.bandEls.get(band.id);
      if (!g) {
        g = svgEl("g", { class: "band-group" });
        g.appendChild(svgEl("rect", { class: "band", rx: 8 }));
        g.appendChild(svgEl("text", { class: "band-title" }));
        layerBands.appendChild(g);
        state.bandEls.set(band.id, g);
      }
      const rect = g.firstChild;
      rect.setAttribute("x", band.x);
      rect.setAttribute("y", band.y);
      rect.setAttribute("width", band.w);
      rect.setAttribute("height", band.h);
      const text = g.lastChild;
      text.setAttribute("x", band.x + 12);
      text.setAttribute("y", band.y + 22);
      text.textContent = band.title;
    }
    for (const [id, g] of [...state.bandEls]) {
      if (!seenBands.has(id)) { g.remove(); state.bandEls.delete(id); }
    }

    // 列头（路线名）：每条带条目的路线、以及还没有条目的叶子路线都标出来
    const seenHeads = new Set();
    for (const head of layout.heads || []) {
      seenHeads.add(head.sectionId);
      let g = state.headEls.get(head.sectionId);
      if (!g) {
        g = svgEl("g", { class: "col-head" });
        g.appendChild(svgEl("text", { class: "col-head-title" }));
        g.appendChild(svgEl("rect", { class: "col-head-rule", rx: 1 }));
        g.appendChild(svgEl("text", { class: "col-head-empty" }));
        layerHeads.appendChild(g);
        state.headEls.set(head.sectionId, g);
      }
      g.setAttribute("transform", `translate(${head.x}, ${head.y})`);
      const [titleEl, ruleEl, emptyEl] = g.children;
      const label = PNLayout.truncateText(head.title, head.chars);
      titleEl.textContent = label;
      titleEl.setAttribute("title", head.path);
      const labelWidth = [...label].reduce((sum, ch) => sum + (/[\x00-\xff]/.test(ch) ? 0.56 : 1), 0) * 12;
      ruleEl.setAttribute("x", 0);
      ruleEl.setAttribute("y", 4);
      ruleEl.setAttribute("width", labelWidth + 6);
      ruleEl.setAttribute("height", 2.5);
      ruleEl.setAttribute("fill", head.color);
      emptyEl.setAttribute("x", labelWidth + 10);
      emptyEl.textContent = head.empty ? "（还没有条目）" : "";
    }
    for (const [id, g] of [...state.headEls]) {
      if (!seenHeads.has(id)) { g.remove(); state.headEls.delete(id); }
    }

    // 节点
    const seenNodes = new Set();
    for (const info of layout.positions.values()) {
      seenNodes.add(info.id);
      let g = state.nodeEls.get(info.id);
      if (!g) {
        g = buildNodeEl(info);
        layerNodes.appendChild(g);
        state.nodeEls.set(info.id, g);
      }
      updateNodeEl(g, info);
    }
    for (const [id, g] of [...state.nodeEls]) {
      if (!seenNodes.has(id)) { g.remove(); state.nodeEls.delete(id); }
    }

    // 边
    const seenEdges = new Set();
    for (const edge of layout.edges) {
      const id = edge.aId + ">" + edge.bId;
      seenEdges.add(id);
      let path = state.edgeEls.get(id);
      if (!path) {
        path = svgEl("path", { class: "edge" });
        layerEdges.appendChild(path);
        state.edgeEls.set(id, path);
      }
      const visual = edge.kind.indexOf("explicit") >= 0 ? "explicit" : "chain";
      path.setAttribute("d", edge.d);
      path.setAttribute("class", "edge edge-" + visual);
      path.setAttribute("marker-end", visual === "explicit" ? "url(#arrow-explicit)" : "url(#arrow-chain)");
      path.dataset.from = edge.aId;
      path.dataset.to = edge.bId;
    }
    for (const [id, path] of [...state.edgeEls]) {
      if (!seenEdges.has(id)) { path.remove(); state.edgeEls.delete(id); }
    }

    applyView();
    if (state.highlight) highlightNodes(state.highlight);
    else clearHighlight();
    syncDialogIfOpen();
  }

  function buildNodeEl(info) {
    const g = svgEl("g", { class: "node" });
    g.dataset.id = info.id;
    const box = svgEl("rect", { class: "node-box", rx: 10, width: info.w, height: info.h });
    const accent = svgEl("rect", { class: "node-accent", x: 0, y: 10, width: 3.5, height: Math.max(12, info.h - 20), rx: 1.75, fill: info.color });
    const idx = svgEl("text", { class: "node-index", x: 14, y: 18 });
    g.append(box, accent, idx);
    // 概要行数固定按 maxLines 建，行的显隐由 updateNodeEl 填文本决定；高度随实际行数变化
    const lineCount = Math.max(1, info.maxLines || 1);
    for (let i = 0; i < lineCount; i += 1) {
      g.append(svgEl("text", { class: "node-summary", x: 14, y: info.firstLineBase + i * info.lineStep }));
    }
    // 节点上只写章节索引与实现目标概要；未解析依赖只用左侧描边提示，不写额外文字
    g.addEventListener("pointerdown", onNodePointerDown);
    g.addEventListener("pointerenter", () => { if (!state.drag) highlightNodes(collectRelated(info.id)); });
    g.addEventListener("pointerleave", () => { if (!state.drag) { state.highlight = null; clearHighlight(); } });
    return g;
  }

  function updateNodeEl(g, info) {
    g.dataset.section = info.sectionId;
    g.querySelector(".node-box").setAttribute("width", info.w);
    g.querySelector(".node-box").setAttribute("height", info.h);
    const accent = g.querySelector(".node-accent");
    accent.setAttribute("height", Math.max(12, info.h - 20));
    accent.setAttribute("fill", info.color);
    g.querySelector(".node-index").textContent = PNLayout.truncateText(info.index_label, info.indexChars);
    const lines = info.lines || [];
    const summaryEls = g.querySelectorAll(".node-summary");
    for (let i = 0; i < summaryEls.length; i += 1) {
      summaryEls[i].textContent = lines[i] || "";
    }
    g.style.transform = `translate(${info.x}px, ${info.y}px)`;
    g.classList.toggle("error", info.has_error);
    g.classList.toggle("active", state.editingId === info.id);
  }

  // ---------------------------------------------------------------- 视图变换
  function applyView() {
    world.style.transform = `translate(${state.view.tx}px, ${state.view.ty}px) scale(${state.view.k})`;
  }

  function fitView() {
    if (!state.layout) return;
    const rect = canvas.getBoundingClientRect();
    const pad = 40;
    const k = Math.min((rect.width - pad * 2) / state.layout.width, (rect.height - pad * 2) / state.layout.height, 1.15);
    state.view.k = Math.max(0.2, k);
    state.view.tx = (rect.width - state.layout.width * state.view.k) / 2;
    state.view.ty = (rect.height - state.layout.height * state.view.k) / 2;
    applyView();
  }

  function focusNode(nodeId) {
    const info = state.layout && state.layout.positions.get(nodeId);
    if (!info) return;
    const rect = canvas.getBoundingClientRect();
    state.view.tx = rect.width / 2 - (info.x + info.w / 2) * state.view.k;
    state.view.ty = rect.height / 2 - (info.y + info.h / 2) * state.view.k;
    applyView();
  }

  // ---------------------------------------------------------------- 高亮
  function collectRelated(nodeId) {
    const ids = new Set([nodeId]);
    // 边从前置节点指向依赖它的节点；只取显式直接依赖，不沿路线链或依赖递归扩展。
    for (const edge of state.model.edges) {
      if (edge.to === nodeId && edge.kind.includes("explicit")) ids.add(edge.from);
    }
    return ids;
  }

  function highlightNodes(ids) {
    state.highlight = ids;
    for (const [id, g] of state.nodeEls) g.classList.toggle("dim", !ids.has(id));
    for (const path of state.edgeEls.values()) {
      const hot = ids.has(path.dataset.from) && ids.has(path.dataset.to);
      path.classList.toggle("hot", hot);
      path.classList.toggle("dim", !hot);
    }
  }

  function clearHighlight() {
    state.highlight = null;
    for (const g of state.nodeEls.values()) g.classList.remove("dim");
    for (const path of state.edgeEls.values()) path.classList.remove("hot", "dim");
  }

  // ---------------------------------------------------------------- 侧栏
  function renderSidebar() {
    renderRouteTree();
    renderIssues();
    renderObjects();
  }

  function renderRouteTree() {
    const tree = el("route-tree");
    tree.textContent = "";
    const nodes = new Map(state.model.nodes.map((n) => [n.id, n]));
    const childrenOf = new Map();
    for (const s of state.model.sections) {
      const key = s.parent_id || null;
      if (!childrenOf.has(key)) childrenOf.set(key, []);
      childrenOf.get(key).push(s);
    }
    const appendSection = (container, section, depth) => {
      const children = childrenOf.get(section.id) || [];
      const hasNodes = section.node_ids.length > 0;
      if (!hasNodes && children.length) {
        // 只作分组用的路线（例如「角色行为」）：只画标题与操作，不画成卡片
        container.appendChild(routeGroupHeader(section));
        for (const child of children) appendSection(container, child, depth + 1);
        return;
      }
      container.appendChild(routeBlock(section, nodes, depth));
      for (const child of children) appendSection(container, child, depth + 1);
    };
    for (const section of childrenOf.get(null) || []) appendSection(tree, section, 0);
  }

  function routeGroupHeader(section) {
    const wrap = document.createElement("div");
    wrap.className = "route-group";
    const root = document.createElement("div");
    root.className = "route-root";
    const title = document.createElement("span");
    title.className = "route-root-title";
    title.textContent = section.title;
    const actions = document.createElement("span");
    actions.className = "route-actions";
    actions.append(
      miniButton("＋", "在末尾新增条目", () => addNode(section.id, null)),
      miniButton("＋子", `在「${section.title}」下新增子路线`, () => addSubSection(section)),
      miniButton("✎", "重命名路线", () => renameSection(section)),
      miniButton("🗑", "删除路线", () => removeSection(section))
    );
    root.append(title, actions);
    wrap.appendChild(root);
    return wrap;
  }

  function routeBlock(section, nodes, depth) {
    const block = document.createElement("div");
    block.className = "route" + (depth > 0 ? " nested" : "");
    if (depth > 1) block.style.marginLeft = depth * 10 + "px";

    const head = document.createElement("div");
    head.className = "route-head";
    const swatch = document.createElement("span");
    swatch.className = "route-swatch";
    swatch.style.background = PNLayout.routeColor(section.id, state.model.sections);
    const title = document.createElement("span");
    title.className = "route-title";
    title.textContent = section.title;
    if (depth > 0) title.title = section.path;
    const count = document.createElement("span");
    count.className = "route-count";
    count.textContent = section.node_ids.length;
    const actions = document.createElement("span");
    actions.className = "route-actions";
    actions.append(
      miniButton("＋", "在末尾新增条目", () => addNode(section.id, null)),
      miniButton("＋子", `在「${section.title}」下新增子路线`, () => addSubSection(section)),
      miniButton("✎", "重命名路线", () => renameSection(section)),
      miniButton("↑", "前移路线", () => op("move_section", { section_id: section.id, direction: "up" }).catch(fail)),
      miniButton("↓", "后移路线", () => op("move_section", { section_id: section.id, direction: "down" }).catch(fail)),
      miniButton("🗑", "删除路线", () => removeSection(section))
    );
    head.append(swatch, title, count, actions);
    block.appendChild(head);

    const list = document.createElement("div");
    list.className = "route-nodes";
    for (const id of section.node_ids) {
      const node = nodes.get(id);
      if (!node) continue;
      const row = document.createElement("div");
      row.className = "node-row" + (state.editingId === id ? " active" : "");
      const num = document.createElement("span");
      num.className = "num";
      num.textContent = node.number;
      const label = document.createElement("span");
      label.className = "label";
      label.textContent = node.summary || "（未填概要）";
      row.append(num, label);
      if (node.refs.some((r) => !r.resolved)) {
        const flag = document.createElement("span");
        flag.className = "flag";
        flag.textContent = "!";
        flag.title = "存在未解析的依赖";
        row.appendChild(flag);
      }
      row.addEventListener("click", () => openNodeDialog(id));
      row.addEventListener("mouseenter", () => highlightNodes(collectRelated(id)));
      row.addEventListener("mouseleave", () => { state.highlight = null; clearHighlight(); });
      list.appendChild(row);
    }
    if (!section.node_ids.length) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "还没有条目";
      list.appendChild(empty);
    }
    block.appendChild(list);
    return block;
  }

  function miniButton(text, title, handler) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = text;
    b.title = title;
    b.addEventListener("click", (ev) => { ev.stopPropagation(); handler(); });
    return b;
  }

  function renderIssues() {
    const list = el("issue-list");
    list.textContent = "";
    const issues = state.model.issues;
    el("issue-counter").textContent = `${state.model.stats.errors} / ${issues.length}`;
    if (!issues.length) {
      const ok = document.createElement("div");
      ok.className = "hint";
      ok.textContent = "没有发现问题。";
      list.appendChild(ok);
      return;
    }
    for (const issue of issues) {
      const row = document.createElement("div");
      row.className = "issue " + issue.level;
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = issue.level === "error" ? "阻塞" : issue.level === "warning" ? "提醒" : "提示";
      const text = document.createElement("span");
      text.textContent = issue.text;
      row.append(badge, text);
      if (issue.node_id) {
        row.addEventListener("click", () => { openNodeDialog(issue.node_id); focusNode(issue.node_id); });
        row.addEventListener("mouseenter", () => highlightNodes(collectRelated(issue.node_id)));
        row.addEventListener("mouseleave", () => { state.highlight = null; clearHighlight(); });
      }
      list.appendChild(row);
    }
  }

  function renderObjects() {
    const list = el("object-list");
    list.textContent = "";
    const usage = state.model.object_usage || {};
    const names = Object.keys(usage).sort((a, b) => usage[b].length - usage[a].length || a.localeCompare(b));
    el("object-counter").textContent = names.length;
    if (!names.length) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "暂时没有声明对象。";
      list.appendChild(empty);
      return;
    }
    const byId = new Map(state.model.nodes.map((n) => [n.id, n]));
    for (const name of names) {
      const item = document.createElement("div");
      item.className = "object-item";
      const head = document.createElement("div");
      const nameEl = document.createElement("span");
      nameEl.className = "name";
      nameEl.textContent = name;
      const used = document.createElement("span");
      used.className = "used";
      const labels = usage[name].map((id) => (byId.get(id) ? byId.get(id).index_label : id));
      used.textContent = ` · ${labels.length} 处：${labels.join("、")}`;
      const paths = usage[name].map((id) => (byId.get(id) ? (byId.get(id).objects.find((o) => o.name === name) || {}).path : "") || "");
      const hasPath = paths.some((p) => p && p.trim());
      const flag = document.createElement("span");
      flag.className = hasPath ? "path-ok" : "path-missing";
      flag.textContent = hasPath ? " · 已写实现路径" : " · 未写实现路径";
      head.append(nameEl, used, flag);
      item.appendChild(head);
      const ids = usage[name];
      item.addEventListener("click", () => openNodeDialog(ids[0]));
      item.addEventListener("mouseenter", () => highlightNodes(new Set(ids)));
      item.addEventListener("mouseleave", () => { state.highlight = null; clearHighlight(); });
      list.appendChild(item);
    }
  }

  // ---------------------------------------------------------------- 画布交互
  canvas.addEventListener("pointerdown", (ev) => {
    if (ev.target.closest(".node")) return;
    state.pan = { x: ev.clientX, y: ev.clientY, tx: state.view.tx, ty: state.view.ty, moved: false };
    canvas.classList.add("dragging");
    canvas.setPointerCapture(ev.pointerId);
  });

  canvas.addEventListener("pointermove", (ev) => {
    if (state.pan) {
      const dx = ev.clientX - state.pan.x;
      const dy = ev.clientY - state.pan.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) state.pan.moved = true;
      state.view.tx = state.pan.tx + dx;
      state.view.ty = state.pan.ty + dy;
      applyView();
      return;
    }
    if (state.drag) {
      const dx = (ev.clientX - state.drag.startX) / state.view.k;
      const dy = (ev.clientY - state.drag.startY) / state.view.k;
      if (Math.abs(dx) + Math.abs(dy) > 3) state.drag.moved = true;
      const info = state.layout.positions.get(state.drag.id);
      if (!info) return;
      info.x = state.drag.baseX + dx;
      info.y = PNLayout.constrainNodeY(state.layout, state.drag.id, state.drag.baseY + dy);
      const g = state.nodeEls.get(state.drag.id);
      if (g) g.style.transform = `translate(${info.x}px, ${info.y}px)`;
      redrawEdgesFor(state.drag.id);
    }
  });

  canvas.addEventListener("pointerup", (ev) => {
    if (state.pan) {
      state.pan = null;
      canvas.classList.remove("dragging");
      return;
    }
    if (state.drag) {
      const drag = state.drag;
      state.drag = null;
      if (drag.moved) {
        const info = state.layout.positions.get(drag.id);
        const node = state.model.nodes.find((n) => n.id === drag.id);
        const dx = Math.round(info.x - info.baseX);
        const dy = Math.round(info.y - info.baseY);
        node.manual = { dx, dy };
        op("update_node", { node_id: drag.id, manual: { dx, dy }, reparse: false }).catch(fail);
      } else {
        openNodeDialog(drag.id);
      }
    }
  });

  canvas.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const my = ev.clientY - rect.top;
    const factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
    const k = Math.min(2.6, Math.max(0.15, state.view.k * factor));
    const wx = (mx - state.view.tx) / state.view.k;
    const wy = (my - state.view.ty) / state.view.k;
    state.view.k = k;
    state.view.tx = mx - wx * k;
    state.view.ty = my - wy * k;
    applyView();
  }, { passive: false });

  function redrawEdgesFor(nodeId) {
    if (!state.layout) return;
    for (const [id, path] of state.edgeEls) {
      const [from, to] = id.split(">");
      if (from !== nodeId && to !== nodeId) continue;
      const a = state.layout.positions.get(from);
      const b = state.layout.positions.get(to);
      if (a && b) path.setAttribute("d", PNLayout.edgePath(a, b, state.layout.options));
    }
  }

  function onNodePointerDown(ev) {
    if (ev.button !== 0) return;
    ev.stopPropagation();
    const id = ev.currentTarget.dataset.id;
    const info = state.layout.positions.get(id);
    state.drag = { id, startX: ev.clientX, startY: ev.clientY, baseX: info.x, baseY: info.y, moved: false };
    canvas.setPointerCapture(ev.pointerId);
  }

  // ---------------------------------------------------------------- 操作
  function fail(err) {
    toast(err && err.message ? err.message : String(err), true);
  }

  async function addNode(sectionId, afterNodeId) {
    try {
      const data = await op("insert_node", {
        section_id: sectionId,
        after_node_id: afterNodeId || null,
        summary: "新条目",
        body: "新条目",
      });
      if (data.node_id) openNodeDialog(data.node_id);
    } catch (err) {
      fail(err);
    }
  }

  async function removeSection(section) {
    const count = section.node_ids.length;
    if (!window.confirm(`删除路线「${section.title}」${count ? `及其 ${count} 个条目` : ""}？`)) return;
    try {
      await op("delete_section", { section_id: section.id });
    } catch (err) {
      fail(err);
    }
  }

  async function renameSection(section) {
    const title = window.prompt("新的路线名（章节标题）", section.title);
    if (title === null || !title.trim() || title === section.title) return;
    try {
      await op("update_section", { section_id: section.id, title: title.trim() });
    } catch (err) {
      fail(err);
    }
  }

  async function addSection() {
    const title = window.prompt("新开发路线的标题（顶层路线）", "新开发路线");
    if (title === null || !title.trim()) return;
    try {
      await op("insert_section", { title: title.trim(), level: 2 });
    } catch (err) {
      fail(err);
    }
  }

  // 找出某条路线整棵子树里文档顺序最靠后的那条路线，用于把新子路线追加在子树末尾
  function lastDescendantId(sectionId) {
    const sections = state.model.sections;
    const inSubtree = new Set([sectionId]);
    let grew = true;
    while (grew) {
      grew = false;
      for (const s of sections) {
        if (s.parent_id && inSubtree.has(s.parent_id) && !inSubtree.has(s.id)) {
          inSubtree.add(s.id);
          grew = true;
        }
      }
    }
    let anchor = sectionId;
    let anchorIndex = sections.findIndex((s) => s.id === sectionId);
    sections.forEach((s, i) => {
      if (inSubtree.has(s.id) && i > anchorIndex) {
        anchor = s.id;
        anchorIndex = i;
      }
    });
    return anchor;
  }

  async function addSubSection(section) {
    const path = section.path || section.title;
    const title = window.prompt(`在「${path}」下新增子路线的标题`, "新子路线");
    if (title === null || !title.trim()) return;
    try {
      await op("insert_section", {
        title: title.trim(),
        parent_id: section.id,
        level: section.level + 1,
        after_section_id: lastDescendantId(section.id),
      });
    } catch (err) {
      fail(err);
    }
  }

  // ---------------------------------------------------------------- 节点详情
  function openNodeDialog(nodeId) {
    const node = state.model.nodes.find((n) => n.id === nodeId);
    if (!node) return;
    state.editingId = nodeId;
    const section = state.model.sections.find((s) => s.id === node.section_id);
    el("nd-route").textContent = section ? section.path : "开发路线";
    el("nd-title").textContent = node.index_label;
    el("nd-summary").value = node.summary;
    el("nd-body").value = node.body;
    el("nd-notes-group").hidden = !node.notes.length;
    renderRefRows(node);
    renderObjectRows(node);
    renderNoteRows(node);
    const dialog = el("node-dialog");
    if (!dialog.open) dialog.showModal();
    for (const g of state.nodeEls.values()) g.classList.toggle("active", g.dataset.id === nodeId);
  }

  function syncDialogIfOpen() {
    if (state.editingId && el("node-dialog").open) openNodeDialog(state.editingId);
  }

  function nodeOptions(selected, includeAuto) {
    const select = document.createElement("select");
    if (includeAuto) {
      const auto = document.createElement("option");
      auto.value = "";
      auto.textContent = "自动按「依赖…」文本解析";
      select.appendChild(auto);
    }
    for (const section of state.model.sections) {
      const nodes = state.model.nodes.filter((n) => n.section_id === section.id);
      if (!nodes.length) continue;
      const group = document.createElement("optgroup");
      group.label = section.title;
      for (const n of nodes) {
        const option = document.createElement("option");
        option.value = n.id;
        option.textContent = `${n.number} · ${n.summary || "（未填概要）"}`;
        if (n.id === selected) option.selected = true;
        group.appendChild(option);
      }
      select.appendChild(group);
    }
    return select;
  }

  function makeHint(text) {
    const hint = document.createElement("div");
    hint.className = "hint";
    hint.textContent = text;
    return hint;
  }

  function appendRefRow(box, ref) {
    const hint = box.querySelector(".hint");
    if (hint) hint.remove();
    const row = document.createElement("div");
    row.className = "row";
    const raw = document.createElement("input");
    raw.type = "text";
    raw.className = "raw";
    raw.value = ref.raw || "";
    raw.placeholder = "依赖角色移动1";
    raw.dataset.targetId = ref.target_id || "";
    const select = nodeOptions(ref.target_id, true);
    select.className = "grow";
    const pill = document.createElement("span");
    pill.className = "pill " + (ref.target_id ? "ok" : ref.raw ? "bad" : "");
    pill.textContent = ref.target_id ? "已解析" : ref.raw ? "未解析" : "待填";
    pill.title = ref.reason || "";
    const del = document.createElement("button");
    del.type = "button";
    del.className = "del";
    del.textContent = "✕";
    del.title = "删除这条依赖";
    del.addEventListener("click", () => {
      // 只删这一行；删空时补一条占位提示，绝不能拿模型里的旧数据重画（那样这行会立刻复活，
      // 只剩一条依赖时就永远删不掉）
      row.remove();
      if (!box.querySelector('.row[data-role="ref"]')) {
        box.appendChild(makeHint("没有显式依赖。同路线内相邻条目已自动依次向上依赖。"));
      }
    });
    raw.addEventListener("input", () => {
      raw.dataset.targetId = "";
      select.value = "";
      pill.className = "pill";
      pill.textContent = "待解析";
      pill.title = "保存后按文本重新解析";
    });
    select.addEventListener("change", () => {
      raw.dataset.targetId = select.value;
      if (select.value) {
        const target = state.model.nodes.find((n) => n.id === select.value);
        if (target) {
          const sec = state.model.sections.find((s) => s.id === target.section_id);
          raw.value = `${sec ? sec.title : ""}${target.number}`;
        }
        pill.className = "pill ok";
        pill.textContent = "已指定";
      } else {
        pill.className = "pill";
        pill.textContent = "待解析";
      }
    });
    row.append(raw, select, pill, del);
    row.dataset.role = "ref";
    box.appendChild(row);
  }

  function renderRefRows(node) {
    const box = el("nd-refs");
    box.textContent = "";
    if (!node || !node.refs.length) {
      box.appendChild(makeHint("没有显式依赖。同路线内相邻条目已自动依次向上依赖。"));
      return;
    }
    node.refs.forEach((ref) => appendRefRow(box, ref));
  }

  function appendObjectRow(box, obj) {
    const hint = box.querySelector(".hint");
    if (hint) hint.remove();
    const row = document.createElement("div");
    row.className = "row obj-row";

    const head = document.createElement("div");
    head.className = "obj-head";
    const name = document.createElement("input");
    name.type = "text";
    name.className = "obj-name";
    name.value = obj.name || "";
    name.placeholder = "对象名，如 元对象-地格占用组件 / TilemapManager";
    const del = document.createElement("button");
    del.type = "button";
    del.className = "del";
    del.textContent = "✕";
    del.title = "删除这个对象";
    del.addEventListener("click", () => {
      // 同上：删空只补占位提示，不拿模型旧数据重画
      row.remove();
      if (!box.querySelector('.row[data-role="obj"]')) {
        box.appendChild(makeHint("没有声明对象。复杂对象的实现路径可以留空，之后补。"));
      }
    });
    head.append(name, del);

    const pathField = document.createElement("label");
    pathField.className = "obj-field";
    const pathLabel = document.createElement("span");
    pathLabel.textContent = "实现路径（可选）：落在哪个对象 / 程序集 / 文档";
    const path = document.createElement("textarea");
    path.className = "obj-path";
    path.rows = 2;
    path.value = obj.path || "";
    path.placeholder = "复杂对象写清落到谁头上；逻辑简单、暂不展开的可以留空";
    pathField.append(pathLabel, path);

    const noteField = document.createElement("label");
    noteField.className = "obj-field";
    const noteLabel = document.createElement("span");
    noteLabel.textContent = "说明 / 备注（正文长括号里的设计说明会归到这里）";
    const note = document.createElement("textarea");
    note.className = "obj-note";
    note.rows = 3;
    note.value = obj.note || "";
    note.placeholder = "这个对象要做什么、边界在哪";
    noteField.append(noteLabel, note);

    row.append(head, pathField, noteField);
    row.dataset.role = "obj";
    box.appendChild(row);
  }

  function renderObjectRows(node) {
    const box = el("nd-objs");
    box.textContent = "";
    if (!node || !node.objects.length) {
      box.appendChild(makeHint("没有声明对象。复杂对象的实现路径可以留空，之后补。"));
      return;
    }
    node.objects.forEach((obj) => appendObjectRow(box, obj));
  }

  function renderNoteRows(node) {
    const box = el("nd-notes");
    box.textContent = "";
    node.notes.forEach((text) => {
      const row = document.createElement("div");
      row.className = "row notes-row";
      const area = document.createElement("textarea");
      area.rows = 2;
      area.value = text;
      const del = document.createElement("button");
      del.type = "button";
      del.className = "del";
      del.textContent = "✕";
      del.addEventListener("click", () => {
        row.remove();
        // 说明删空后把整个分组收起来，免得留一个空标题
        if (!box.querySelector('.row[data-role="note"]')) el("nd-notes-group").hidden = true;
      });
      row.append(area, del);
      row.dataset.role = "note";
      box.appendChild(row);
    });
  }

  function collectRows(box, role) {
    const out = [];
    for (const row of box.querySelectorAll(`.row[data-role="${role}"]`)) {
      out.push(row);
    }
    return out;
  }

  async function saveNodeDialog() {
    const nodeId = state.editingId;
    if (!nodeId) return;
    const refs = collectRows(el("nd-refs"), "ref").map((row) => {
      const raw = row.querySelector("input.raw");
      const select = row.querySelector("select");
      const targetId = raw.dataset.targetId || (select ? select.value : "") || null;
      return { raw: raw.value.trim(), target_id: targetId };
    }).filter((r) => r.raw);
    const objects = collectRows(el("nd-objs"), "obj").map((row) => ({
      name: row.querySelector(".obj-name").value.trim(),
      path: row.querySelector(".obj-path").value.trim(),
      note: row.querySelector(".obj-note").value.trim(),
    })).filter((o) => o.name);
    const notes = collectRows(el("nd-notes"), "note").map((row) => row.querySelector("textarea").value.trim()).filter(Boolean);
    try {
      await op("update_node", {
        node_id: nodeId,
        summary: el("nd-summary").value,
        body: el("nd-body").value,
        refs,
        objects,
        notes,
        reparse: true,
      });
      closeDialog(el("node-dialog"));
    } catch (err) {
      fail(err);
    }
  }

  function closeDialog(dialog) {
    if (dialog.open) dialog.close();
  }

  // ---------------------------------------------------------------- 导入导出
  async function doImport(payload, mode) {
    const path = mode === "reset" ? "/api/reset" : "/api/import";
    try {
      const data = await post(path, payload);
      state.history.length = 0;
      state.redo.length = 0;
      applyModel(data.model);
      closeDialog(el("import-dialog"));
      if (data.warnings && data.warnings.length) toast("导入完成，但有以下偏差：\n" + data.warnings.join("\n"));
      else toast(`导入完成：${data.model.stats.sections} 条路线 / ${data.model.stats.nodes} 个条目`);
      fitView();
    } catch (err) {
      if (err.needConfirm === "empty_import") {
        // 该来源没有条目，确认后才允许覆盖
        if (window.confirm(`${err.message}\n\n确定要用这份内容覆盖吗？（旧数据仍在快照里可恢复）`)) {
          return doImport(Object.assign({}, payload, { allow_empty: true }), mode);
        }
        return;
      }
      fail(err);
    }
  }

  async function showMarkdownPreview() {
    try {
      const res = await fetch("/api/markdown");
      const text = await res.text();
      el("markdown-preview").textContent = text;
      el("markdown-path").textContent = "尚未写入文件";
      el("markdown-dialog").showModal();
    } catch (err) {
      fail(err);
    }
  }

  async function writeMarkdown() {
    try {
      const data = await post("/api/export", {});
      el("markdown-preview").textContent = data.markdown;
      el("markdown-path").textContent = `已写入 ${data.path}`;
      toast(`已导出到 ${data.path}`);
    } catch (err) {
      fail(err);
    }
  }

  async function exportImage() {
    if (!state.layout || !state.model.nodes.length) {
      toast("网络图是空的，暂时没有可导出的图片", true);
      return;
    }
    const button = el("btn-export-image");
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "正在生成…";
    let svgUrl = null;
    let pngUrl = null;
    try {
      const width = Math.ceil(state.layout.width);
      const height = Math.ceil(state.layout.height);
      const clone = canvas.cloneNode(true);
      clone.setAttribute("xmlns", SVG_NS);
      clone.setAttribute("width", width);
      clone.setAttribute("height", height);
      clone.setAttribute("viewBox", `0 0 ${width} ${height}`);
      clone.removeAttribute("class");

      // 导出完整自动布局，避免把当前屏幕的平移、缩放和交互状态带进图片。
      const clonedWorld = clone.querySelector("#world");
      clonedWorld.removeAttribute("style");
      clonedWorld.setAttribute("transform", "translate(0 0) scale(1)");
      clone.querySelectorAll(".dim, .hot, .active").forEach((node) => {
        node.classList.remove("dim", "hot", "active");
      });

      const styleResponse = await fetch("/app.css");
      if (!styleResponse.ok) throw new Error("读取网络图样式失败");
      const style = document.createElementNS(SVG_NS, "style");
      style.textContent = await styleResponse.text();
      clone.querySelector("defs").appendChild(style);
      const background = document.createElementNS(SVG_NS, "rect");
      background.setAttribute("x", "0");
      background.setAttribute("y", "0");
      background.setAttribute("width", width);
      background.setAttribute("height", height);
      background.setAttribute("fill", "#f5f6f8");
      clone.insertBefore(background, clonedWorld);

      const source = new XMLSerializer().serializeToString(clone);
      svgUrl = URL.createObjectURL(new Blob([source], { type: "image/svg+xml;charset=utf-8" }));
      const image = new Image();
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = () => reject(new Error("网络图图片渲染失败"));
        image.src = svgUrl;
      });

      // 默认以 2 倍像素导出；超大网络图自动缩小，避免超过浏览器画布限制。
      const scale = Math.min(2, 16384 / width, 16384 / height, Math.sqrt(32000000 / (width * height)));
      const output = document.createElement("canvas");
      output.width = Math.max(1, Math.floor(width * scale));
      output.height = Math.max(1, Math.floor(height * scale));
      const context = output.getContext("2d");
      if (!context) throw new Error("浏览器无法创建图片画布");
      context.scale(scale, scale);
      context.drawImage(image, 0, 0, width, height);
      const blob = await new Promise((resolve, reject) => {
        output.toBlob((value) => value ? resolve(value) : reject(new Error("PNG 编码失败")), "image/png");
      });
      pngUrl = URL.createObjectURL(blob);
      const now = new Date();
      const stamp = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("") +
        "-" + [String(now.getHours()).padStart(2, "0"), String(now.getMinutes()).padStart(2, "0"), String(now.getSeconds()).padStart(2, "0")].join("");
      const link = document.createElement("a");
      link.href = pngUrl;
      link.download = `项目网络图-${stamp}.png`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast(`已导出 PNG 图片（${output.width} × ${output.height}）`);
    } catch (err) {
      fail(err);
    } finally {
      if (svgUrl) URL.revokeObjectURL(svgUrl);
      if (pngUrl) setTimeout(() => URL.revokeObjectURL(pngUrl), 1000);
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  // ---------------------------------------------------------------- 数据管理
  function renderDatasets() {
    const entries = (state.config && state.config.datasets) || [];
    const select = el("dataset-select");
    select.textContent = "";
    if (!entries.length) {
      const option = document.createElement("option");
      option.textContent = "请新建网络图";
      option.value = "";
      select.appendChild(option);
    }
    const list = el("datasets-list");
    list.textContent = "";
    el("datasets-directory").textContent = `数据目录：${(state.config && state.config.data_dir) || ""}`;
    for (const entry of entries) {
      const name = entry.id.replace(/\.sqlite$/, "");
      const option = document.createElement("option");
      option.value = entry.id;
      option.textContent = name;
      select.appendChild(option);
      const row = document.createElement("div");
      row.className = "dataset-item" + (entry.id === state.datasetId ? " current" : "");
      const description = document.createElement("div");
      description.className = "dataset-description";
      const title = document.createElement("strong");
      title.textContent = name;
      const detail = document.createElement("span");
      detail.className = "hint";
      detail.textContent = `${entry.nodes} 个节点${entry.id === state.datasetId ? " · 当前打开" : ""}`;
      description.append(title, detail);
      const actions = document.createElement("div");
      actions.className = "dataset-actions";
      const open = document.createElement("button");
      open.type = "button";
      open.className = "button small";
      open.textContent = "打开";
      open.addEventListener("click", () => datasetAction("select", { id: entry.id }));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "button danger small";
      remove.textContent = "删除";
      remove.addEventListener("click", () => {
        if (window.confirm(`删除网络图「${name}」？文件将移入「已删除」目录，可恢复。`)) {
          datasetAction("delete", { id: entry.id });
        }
      });
      actions.append(open, remove);
      row.append(description, actions);
      list.appendChild(row);
    }
    select.value = state.datasetId || "";
  }

  function applyDataset(data) {
    const changed = state.datasetId !== data.dataset_id;
    if (changed) {
      for (const id of ["node-dialog", "import-dialog", "markdown-dialog"]) closeDialog(el(id));
      state.history.length = 0;
      state.redo.length = 0;
      state.editingId = null;
      state.drag = null;
      state.pan = null;
      clearHighlight();
      for (const node of state.nodeEls.values()) node.classList.remove("active");
      canvas.classList.remove("dragging");
    }
    state.datasetId = data.dataset_id || null;
    state.config = data.config;
    applyModel(data.model);
    renderDatasets();
    if (changed) fitView();
  }

  async function datasetAction(action, args) {
    if (state.datasetBusy) return;
    if (el("node-dialog").open && !window.confirm("当前条目有尚未保存的编辑，切换数据会丢弃这些编辑。继续？")) {
      renderDatasets();
      return;
    }
    state.datasetBusy = true;
    try {
      const data = await post(`/api/datasets/${action}`, args);
      applyDataset(data);
      if (action !== "delete") closeDialog(el("datasets-dialog"));
      if (action === "create") el("dataset-name").value = "";
      if (action === "add") el("dataset-path").value = "";
      toast(action === "delete" ? "已移入「已删除」目录" : "已打开网络图");
    } catch (err) {
      renderDatasets();
      fail(err);
    } finally {
      state.datasetBusy = false;
    }
  }

  async function showDatasets() {
    try {
      applyDataset(await api("/api/state"));
      el("datasets-dialog").showModal();
    } catch (err) {
      fail(err);
    }
  }

  // ---------------------------------------------------------------- 撤销
  async function undo() {
    if (!state.history.length) { toast("没有可撤销的操作"); return; }
    const previous = state.history.pop();
    state.redo.push(JSON.parse(JSON.stringify(state.model)));
    await replaceModel(previous);
  }

  async function redo() {
    if (!state.redo.length) { toast("没有可重做的操作"); return; }
    const next = state.redo.pop();
    state.history.push(JSON.parse(JSON.stringify(state.model)));
    await replaceModel(next);
  }

  async function replaceModel(model) {
    try {
      const data = await post("/api/op", { op: "replace", args: { model } });
      applyModel(data.model);
      toast("已切换版本");
    } catch (err) {
      fail(err);
    }
  }

  async function clearManualLayout() {
    try {
      for (const node of state.model.nodes) {
        if (node.manual && (node.manual.dx || node.manual.dy)) {
          await post("/api/op", { op: "update_node", args: { node_id: node.id, manual: {}, reparse: false } });
        }
      }
      const data = await api("/api/state");
      state.config = data.config;
      applyModel(data.model);
      fitView();
      toast("已清除手工挪位，恢复自动排版");
    } catch (err) {
      fail(err);
    }
  }

  // ---------------------------------------------------------------- 绑定
  function bind() {
    el("btn-datasets").addEventListener("click", showDatasets);
    el("datasets-close").addEventListener("click", () => closeDialog(el("datasets-dialog")));
    el("dataset-select").addEventListener("change", () => {
      if (el("dataset-select").value) datasetAction("select", { id: el("dataset-select").value });
    });
    el("dataset-create").addEventListener("click", () => datasetAction("create", { title: el("dataset-name").value.trim() }));
    el("dataset-add").addEventListener("click", () => datasetAction("add", { path: el("dataset-path").value.trim() }));
    el("btn-undo").addEventListener("click", undo);
    el("btn-redo").addEventListener("click", redo);
    el("btn-fit").addEventListener("click", fitView);
    el("btn-relayout").addEventListener("click", clearManualLayout);
    el("btn-add-section").addEventListener("click", addSection);

    const openImport = () => {
      el("import-path").value = (state.config && state.config.default_source) || "";
      el("import-text").value = "";
      el("import-dialog").showModal();
    };
    el("btn-import").addEventListener("click", openImport);
    el("btn-import-empty").addEventListener("click", openImport);
    el("import-close").addEventListener("click", () => closeDialog(el("import-dialog")));
    el("import-from-file").addEventListener("click", () => {
      if (!window.confirm("导入会替换当前网络图（当前版本已在历史里可撤销）。继续？")) return;
      doImport({ path: el("import-path").value.trim() }, "import");
    });
    el("import-reset").addEventListener("click", () => {
      if (!window.confirm("将丢弃当前网络图，按该文件重新建立。继续？")) return;
      doImport({ path: el("import-path").value.trim() }, "reset");
    });
    el("import-from-text").addEventListener("click", () => {
      const text = el("import-text").value;
      if (!text.trim()) { toast("请先粘贴 Markdown 内容", true); return; }
      if (!window.confirm("导入会替换当前网络图（当前版本已在历史里可撤销）。继续？")) return;
      doImport({ text, path: "（粘贴的文本）" }, "import");
    });

    el("btn-preview").addEventListener("click", showMarkdownPreview);
    el("btn-export").addEventListener("click", writeMarkdown);
    el("btn-export-image").addEventListener("click", exportImage);
    el("markdown-close").addEventListener("click", () => closeDialog(el("markdown-dialog")));
    el("markdown-write").addEventListener("click", writeMarkdown);
    el("markdown-copy").addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(el("markdown-preview").textContent);
        toast("已复制到剪贴板");
      } catch (err) {
        toast("复制失败，请手动选择文本", true);
      }
    });

    el("nd-close").addEventListener("click", () => closeDialog(el("node-dialog")));
    el("node-dialog").addEventListener("close", () => {
      state.editingId = null;
      for (const g of state.nodeEls.values()) g.classList.remove("active");
      renderSidebar();
    });
    el("nd-save").addEventListener("click", saveNodeDialog);
    el("nd-add-ref").addEventListener("click", () => {
      appendRefRow(el("nd-refs"), { raw: "", target_id: null });
    });
    el("nd-add-obj").addEventListener("click", () => {
      appendObjectRow(el("nd-objs"), { name: "", path: "", note: "" });
    });
    el("nd-insert-after").addEventListener("click", async () => {
      const node = state.model.nodes.find((n) => n.id === state.editingId);
      if (!node) return;
      await saveNodeDialogSilently();
      await addNode(node.section_id, node.id);
    });
    el("nd-move-up").addEventListener("click", async () => {
      await saveNodeDialogSilently();
      await op("move_node", { node_id: state.editingId, direction: "up" }).catch(fail);
    });
    el("nd-move-down").addEventListener("click", async () => {
      await saveNodeDialogSilently();
      await op("move_node", { node_id: state.editingId, direction: "down" }).catch(fail);
    });
    el("nd-delete").addEventListener("click", async () => {
      const node = state.model.nodes.find((n) => n.id === state.editingId);
      if (!node) return;
      if (!window.confirm(`删除条目「${node.index_label} ${node.summary}」？指向它的依赖会变成未解析。`)) return;
      const sectionId = node.section_id;
      const siblings = state.model.sections.find((s) => s.id === sectionId).node_ids.filter((id) => id !== node.id);
      state.editingId = null;
      closeDialog(el("node-dialog"));
      try {
        await op("delete_node", { node_id: node.id });
        if (siblings.length) {
          const next = state.model.nodes.find((n) => n.id === siblings[0]);
          if (next) openNodeDialog(next.id);
        }
      } catch (err) {
        fail(err);
      }
    });

    document.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "z") {
        ev.preventDefault();
        if (ev.shiftKey) redo(); else undo();
      }
    });
    window.addEventListener("resize", applyView);
  }

  async function saveNodeDialogSilently() {
    const dialog = el("node-dialog");
    if (!dialog.open || !state.editingId) return;
    const refs = collectRows(el("nd-refs"), "ref").map((row) => {
      const raw = row.querySelector("input.raw");
      const select = row.querySelector("select");
      return { raw: raw.value.trim(), target_id: raw.dataset.targetId || (select ? select.value : "") || null };
    }).filter((r) => r.raw);
    const objects = collectRows(el("nd-objs"), "obj").map((row) => ({
      name: row.querySelector(".obj-name").value.trim(),
      path: row.querySelector(".obj-path").value.trim(),
      note: row.querySelector(".obj-note").value.trim(),
    })).filter((o) => o.name);
    const notes = collectRows(el("nd-notes"), "note").map((row) => row.querySelector("textarea").value.trim()).filter(Boolean);
    try {
      await op("update_node", {
        node_id: state.editingId,
        summary: el("nd-summary").value,
        body: el("nd-body").value,
        refs,
        objects,
        notes,
        reparse: true,
      });
    } catch (err) {
      fail(err);
    }
  }

  // ---------------------------------------------------------------- 启动
  async function boot() {
    bind();
    try {
      const data = await api("/api/state");
      applyDataset(data);
      fitView();
      const s = data.model.stats;
      toast(`已载入：${s.sections} 条开发路线 / ${s.nodes} 个条目 / ${s.edges} 条依赖边`);
      el("datasets-dialog").showModal();
    } catch (err) {
      fail(err);
    }
  }

  boot();
})();
