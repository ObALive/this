"use strict";

const state = { token: "", topics: [], selectedId: null, current: null, newTopic: false, editMappingId: null, searchTimer: null };
const $ = (id) => document.getElementById(id);

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    headers["X-Tool-Token"] = state.token;
  } else if (options.method && options.method !== "GET") {
    headers["X-Tool-Token"] = state.token;
  }
  const response = await fetch(path, { ...options, headers, cache: "no-store" });
  let data;
  try { data = await response.json(); } catch { throw new Error(`服务器返回了无法读取的结果（${response.status}）`); }
  if (!response.ok) throw new Error(data.error || `操作失败（${response.status}）`);
  return data;
}

let noticeTimer;
function notice(message, error = false) {
  const el = $("notice");
  el.textContent = message;
  el.classList.toggle("error", error);
  el.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { el.hidden = true; }, 4300);
}

function handleError(error) { console.error(error); notice(error.message || String(error), true); }

function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

async function loadTopics() {
  const q = $("search").value.trim();
  const data = await request(`/api/topics?q=${encodeURIComponent(q)}`);
  state.topics = data.topics;
  renderTopicList();
}

function renderTopicList() {
  const list = $("topic-list");
  list.replaceChildren();
  $("topic-count").textContent = `${state.topics.length} 个主题`;
  if (!state.topics.length) {
    list.append(node("div", "empty-mappings", "没有符合条件的主题"));
    return;
  }
  for (const topic of state.topics) {
    const button = node("button", `topic-button${topic.topic_id === state.selectedId ? " active" : ""}`);
    button.type = "button";
    const top = node("span", "topic-top");
    top.append(node("span", "", topic.topic_id), node("span", "", `${topic.mapping_count} 条映射`));
    button.append(top, node("span", "topic-behavior", topic.player_behavior), node("span", "topic-feedback", topic.feedback_topic));
    button.addEventListener("click", () => selectTopic(topic.topic_id).catch(handleError));
    list.append(button);
  }
}

function setView(visible) {
  $("empty-state").hidden = visible;
  $("topic-view").hidden = !visible;
}

function fillTopicForm(topic) {
  $("topic-id").value = topic.topic_id || "";
  $("topic-id").readOnly = !state.newTopic;
  $("topic-order").value = topic.sort_order ?? 0;
  $("topic-behavior").value = topic.player_behavior || "";
  $("topic-feedback").value = topic.feedback_topic || "";
  $("topic-owner").value = topic.code_owner || "";
  $("topic-source").value = topic.source_ref || "";
  $("topic-updated").textContent = topic.updated_at ? `上次保存：${topic.updated_at}` : "";
  $("topic-heading").textContent = state.newTopic ? "新建主题" : `${topic.topic_id} · 编辑主题`;
  $("delete-topic-button").hidden = state.newTopic;
  $("mappings-section").hidden = state.newTopic;
}

async function selectTopic(topicId) {
  const topic = await request(`/api/topics/${encodeURIComponent(topicId)}`);
  state.selectedId = topicId;
  state.current = topic;
  state.newTopic = false;
  setView(true);
  fillTopicForm(topic);
  renderMappings();
  renderTopicList();
}

function startNewTopic() {
  state.newTopic = true;
  state.selectedId = null;
  state.current = null;
  setView(true);
  fillTopicForm({ sort_order: state.topics.length + 1 });
  renderTopicList();
  $("topic-id").focus();
}

async function saveTopic(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  data.sort_order = Number(data.sort_order || 0);
  const created = state.newTopic;
  const path = created ? "/api/topics" : `/api/topics/${encodeURIComponent(state.selectedId)}`;
  const item = await request(path, { method: created ? "POST" : "PUT", body: JSON.stringify(data) });
  await loadTopics();
  await selectTopic(item.topic_id);
  notice(created ? "主题已创建" : "主题已保存");
}

async function deleteTopic() {
  if (!state.current) return;
  const count = state.current.mappings.length;
  const message = `删除 ${state.current.topic_id}？${count ? `其下 ${count} 条具体映射也会被删除。` : ""}此操作无法在页面内撤销。`;
  if (!window.confirm(message)) return;
  await request(`/api/topics/${encodeURIComponent(state.selectedId)}`, { method: "DELETE" });
  state.selectedId = null;
  state.current = null;
  setView(false);
  await loadTopics();
  notice("主题已删除");
}

function renderMappings() {
  const list = $("mapping-list");
  list.replaceChildren();
  const mappings = state.current?.mappings || [];
  $("mapping-count").textContent = mappings.length;
  if (!mappings.length) {
    list.append(node("div", "empty-mappings", "还没有具体映射。点击“添加映射”开始填写。"));
    return;
  }
  for (const mapping of mappings) {
    const card = node("article", "mapping-card");
    const head = node("div", "mapping-card-head");
    const main = node("div", "");
    main.append(node("div", "mapping-id", `#${mapping.mapping_id}`), node("div", "mapping-title", mapping.player_action));
    const actions = node("div", "mapping-actions");
    const edit = node("button", "", "编辑"); edit.type = "button";
    edit.addEventListener("click", () => openMapping(mapping));
    const remove = node("button", "delete", "删除"); remove.type = "button";
    remove.addEventListener("click", () => removeMapping(mapping).catch(handleError));
    actions.append(edit, remove);
    head.append(main, actions);
    card.append(head, node("p", "mapping-feedback", mapping.program_feedback));
    const extra = node("div", "mapping-extra");
    if (mapping.context) extra.append(node("span", "", `阶段：${mapping.context}`));
    if (mapping.condition_text) extra.append(node("span", "", `条件：${mapping.condition_text}`));
    if (mapping.notes) extra.append(node("span", "", `备注：${mapping.notes}`));
    if (extra.childNodes.length) card.append(extra);
    list.append(card);
  }
}

function openMapping(mapping = null) {
  state.editMappingId = mapping?.mapping_id || null;
  $("mapping-heading").textContent = mapping ? `编辑具体映射 #${mapping.mapping_id}` : "添加具体映射";
  $("mapping-action").value = mapping?.player_action || "";
  $("mapping-feedback").value = mapping?.program_feedback || "";
  $("mapping-context").value = mapping?.context || "";
  $("mapping-condition").value = mapping?.condition_text || "";
  $("mapping-notes").value = mapping?.notes || "";
  $("mapping-order").value = mapping?.sort_order ?? ((state.current?.mappings.length || 0) + 1);
  $("mapping-dialog").showModal();
  $("mapping-action").focus();
}

async function saveMapping(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  data.sort_order = Number(data.sort_order || 0);
  const editing = state.editMappingId !== null;
  const path = editing ? `/api/mappings/${state.editMappingId}` : `/api/topics/${encodeURIComponent(state.selectedId)}/mappings`;
  await request(path, { method: editing ? "PUT" : "POST", body: JSON.stringify(data) });
  $("mapping-dialog").close();
  await selectTopic(state.selectedId);
  await loadTopics();
  notice(editing ? "映射已保存" : "映射已添加");
}

async function removeMapping(mapping) {
  if (!window.confirm(`删除具体映射 #${mapping.mapping_id}？此操作无法在页面内撤销。`)) return;
  await request(`/api/mappings/${mapping.mapping_id}`, { method: "DELETE" });
  await selectTopic(state.selectedId);
  await loadTopics();
  notice("映射已删除");
}

async function exportJson() {
  const data = await request("/api/export");
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = node("a", "");
  link.href = url;
  link.download = `玩家反馈映射备份_${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  notice("已导出 JSON");
}

async function boot() {
  const config = await request("/api/config");
  state.token = config.edit_token;
  $("db-label").textContent = config.database.split(/[\\/]/).pop();
  await loadTopics();
  if (state.topics.length) await selectTopic(state.topics[0].topic_id);
}

$("new-topic-button").addEventListener("click", startNewTopic);
$("delete-topic-button").addEventListener("click", () => deleteTopic().catch(handleError));
$("topic-form").addEventListener("submit", (event) => saveTopic(event).catch(handleError));
$("new-mapping-button").addEventListener("click", () => openMapping());
$("mapping-form").addEventListener("submit", (event) => saveMapping(event).catch(handleError));
$("close-dialog-button").addEventListener("click", () => $("mapping-dialog").close());
$("cancel-dialog-button").addEventListener("click", () => $("mapping-dialog").close());
$("export-button").addEventListener("click", () => exportJson().catch(handleError));
$("search").addEventListener("input", () => {
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(() => loadTopics().catch(handleError), 180);
});
boot().catch(handleError);
