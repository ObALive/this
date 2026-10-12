/* 项目网络图绘制与编辑工具：前端交互与实时渲染。 */
(function () {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const state = {
    model: null,
    config: null,
    layout: null,
    view: { k: 1, tx: 0, ty: 0 },
    history: [],
    redo: [],
    editingId: null,
    nodeEls: new Map(),
    edgeEls: new Map(),
    bandEls: new Map(),
    highlight: null,
    drag: null,
    pan: null,
  };

  const el = (id) => document.getElementById(id);
  const canvas = el("canvas");
  const world = el("world");
  const layerBands = el("layer-bands");
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
    if (!res.ok || data.ok === false) throw new Error(data && data.error ? data.error : `请求失败（${res.status}）`);
    return data;
  }

  function post(path, body) {
    return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
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
    const accent = svgEl("rect", { class: "node-accent", x: 0, y: 10, width: 3.5, height: info.h - 20, rx: 1.75, fill: info.color });
    const idx = svgEl("text", { class: "node-index", x: 14, y: 18 });
    const s1 = svgEl("text", { class: "node-summary", x: 14, y: 39 });
    const s2 = svgEl("text", { class: "node-summary", x: 14, y: 56 });
    // 节点上只写章节索引与实现目标概要；未解析依赖只用左侧描边提示，不写额外文字
    g.append(box, accent, idx, s1, s2);
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
    accent.setAttribute("height", info.h - 20);
    accent.setAttribute("fill", info.color);
    g.querySelector(".node-index").textContent = info.index_label;
    const lines = PNLayout.wrapSummary(info.summary, 15, 2);
    g.children[3].textContent = lines[0] || "";
    g.children[4].textContent = lines[1] || "";
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
    const up = new Set([nodeId]);
    const down = new Set([nodeId]);
    const edges = state.model.edges;
    let changed = true;
    while (changed) {
      changed = false;
      for (const e of edges) {
        if (up.has(e.to) && !up.has(e.from)) { up.add(e.from); changed = true; }
        if (down.has(e.from) && !down.has(e.to)) { down.add(e.to); changed = true; }
      }
    }
    return new Set([...up, ...down]);
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
    const sections = state.model.sections;
    const nodes = new Map(state.model.nodes.map((n) => [n.id, n]));
    const groups = new Map();
    for (const s of sections) {
      const key = s.parent_id || "__root__";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(s);
    }
    const topLevel = groups.get("__root__") || [];
    for (const section of topLevel) {
      const wrap = document.createElement("div");
      wrap.className = "route-group";
      const children = groups.get(section.id) || [];
      if (section.node_ids.length === 0 && children.length) {
        const root = document.createElement("div");
        root.className = "route-root";
        root.textContent = section.title;
        wrap.appendChild(root);
        for (const child of children) wrap.appendChild(routeBlock(child, nodes, true));
      } else {
        wrap.appendChild(routeBlock(section, nodes, false));
        for (const child of children) wrap.appendChild(routeBlock(child, nodes, true));
      }
      tree.appendChild(wrap);
    }
  }

  function routeBlock(section, nodes, nested) {
    const block = document.createElement("div");
    block.className = "route" + (nested ? " nested" : "");

    const head = document.createElement("div");
    head.className = "route-head";
    const swatch = document.createElement("span");
    swatch.className = "route-swatch";
    swatch.style.background = PNLayout.routeColor(section.id, state.model.sections);
    const title = document.createElement("span");
    title.className = "route-title";
    title.textContent = section.title;
    const count = document.createElement("span");
    count.className = "route-count";
    count.textContent = section.node_ids.length;
    const actions = document.createElement("span");
    actions.className = "route-actions";
    actions.append(
      miniButton("＋", "在末尾新增条目", () => addNode(section.id, null)),
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
      info.y = state.drag.baseY + dy;
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
    const title = window.prompt("新开发路线的标题（二级标题）", "新开发路线");
    if (title === null || !title.trim()) return;
    try {
      await op("insert_section", { title: title.trim(), level: 2 });
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
      row.remove();
      if (!box.querySelector('.row[data-role="ref"]')) renderRefRows(state.model.nodes.find((n) => n.id === state.editingId));
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
      const hint = document.createElement("div");
      hint.className = "hint";
      hint.textContent = "没有显式依赖。同路线内相邻条目已自动依次向上依赖。";
      box.appendChild(hint);
      return;
    }
    node.refs.forEach((ref) => appendRefRow(box, ref));
  }

  function appendObjectRow(box, obj) {
    const hint = box.querySelector(".hint");
    if (hint) hint.remove();
    const row = document.createElement("div");
    row.className = "row";
    const name = document.createElement("input");
    name.type = "text";
    name.className = "obj-name";
    name.value = obj.name || "";
    name.placeholder = "元对象-某组件";
    const path = document.createElement("input");
    path.type = "text";
    path.className = "obj-path";
    path.value = obj.path || "";
    path.placeholder = "实现路径（可选）：落在哪个对象/程序集";
    const note = document.createElement("input");
    note.type = "text";
    note.className = "obj-note";
    note.value = obj.note || "";
    note.placeholder = "备注";
    const del = document.createElement("button");
    del.type = "button";
    del.className = "del";
    del.textContent = "✕";
    del.title = "删除这个对象";
    del.addEventListener("click", () => {
      row.remove();
      if (!box.querySelector('.row[data-role="obj"]')) renderObjectRows(state.model.nodes.find((n) => n.id === state.editingId));
    });
    row.append(name, path, note, del);
    row.dataset.role = "obj";
    box.appendChild(row);
  }

  function renderObjectRows(node) {
    const box = el("nd-objs");
    box.textContent = "";
    if (!node || !node.objects.length) {
      const hint = document.createElement("div");
      hint.className = "hint";
      hint.textContent = "没有声明对象。复杂对象的实现路径可以留空，之后补。";
      box.appendChild(hint);
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
      del.addEventListener("click", () => row.remove());
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
    try {
      const data = await post(mode === "reset" ? "/api/reset" : "/api/import", payload);
      state.history.length = 0;
      state.redo.length = 0;
      applyModel(data.model);
      closeDialog(el("import-dialog"));
      if (data.warnings && data.warnings.length) toast("导入完成，但有以下偏差：\n" + data.warnings.join("\n"));
      else toast(`导入完成：${data.model.stats.sections} 条路线 / ${data.model.stats.nodes} 个条目`);
      fitView();
    } catch (err) {
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
      state.config = data.config;
      applyModel(data.model);
      fitView();
      const s = data.model.stats;
      toast(`已载入：${s.sections} 条开发路线 / ${s.nodes} 个条目 / ${s.edges} 条依赖边`);
    } catch (err) {
      fail(err);
    }
  }

  boot();
})();
