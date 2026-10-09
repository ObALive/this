/* 决策库填写器前端：读取决策库、渲染缺口与四个选项、写回裁定结果。 */
(function () {
  "use strict";

  var state = {
    db: null,
    databases: [],
    questions: [],
    filter: "all"
  };

  var el = {
    select: document.getElementById("db-select"),
    dbMeta: document.getElementById("db-meta"),
    list: document.getElementById("list"),
    progressFill: document.getElementById("progress-fill"),
    progressText: document.getElementById("progress-text"),
    saveState: document.getElementById("save-state"),
    toast: document.getElementById("toast"),
    exportLink: document.getElementById("btn-export"),
    refresh: document.getElementById("btn-refresh"),
    filters: document.querySelectorAll(".chip"),
    footDb: document.getElementById("foot-db")
  };

  // ------------------------------------------------------------ 工具函数
  function api(path, options) {
    return fetch(path, options).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) {
          throw new Error(data.error || ("请求失败：" + res.status));
        }
        return data;
      });
    });
  }

  var toastTimer = null;
  function toast(message, isError) {
    el.toast.textContent = message;
    el.toast.className = "toast show" + (isError ? " error" : "");
    if (toastTimer) { clearTimeout(toastTimer); }
    toastTimer = setTimeout(function () { el.toast.className = "toast"; }, 2400);
  }

  function setSaveState(text, isError) {
    el.saveState.textContent = text || "";
    el.saveState.className = "save-state" +
      (text ? (isError ? " error" : " show") : "");
  }

  function mk(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined && text !== null) { node.textContent = text; }
    return node;
  }

  function statusOf(question) {
    return (question.decision && question.decision.status) || "待裁定";
  }

  // ------------------------------------------------------------ 数据加载
  function loadDatabases(preferPath) {
    return api("/api/databases").then(function (data) {
      state.databases = data.databases || [];
      el.select.textContent = "";
      if (!state.databases.length) {
        el.select.appendChild(mk("option", null, "未找到决策库"));
        el.select.disabled = true;
        el.list.textContent = "";
        el.list.appendChild(mk("div", "empty",
          "工作区 Dsh/Output 下没有找到符合规范的决策库，请先生成决策库。"));
        return null;
      }
      el.select.disabled = false;
      state.databases.forEach(function (item) {
        var option = mk("option", null,
          item.name + "　（" + item.decided + "/" + item.gaps + " 已裁定）");
        option.value = item.path;
        el.select.appendChild(option);
      });
      var target = preferPath || data.current || state.db || state.databases[0].path;
      var exists = state.databases.some(function (item) { return item.path === target; });
      state.db = exists ? target : state.databases[0].path;
      el.select.value = state.db;
      el.exportLink.href = "/api/export?db=" + encodeURIComponent(state.db);
      el.footDb.textContent = state.db;
      return state.db;
    });
  }

  function loadQuestions() {
    el.list.textContent = "";
    el.list.appendChild(mk("div", "loading", "正在载入 " + state.db + " …"));
    return api("/api/questions?db=" + encodeURIComponent(state.db))
      .then(function (data) {
        state.questions = data.questions || [];
        render();
      });
  }

  // ------------------------------------------------------------ 渲染
  function render() {
    var decided = state.questions.filter(function (q) {
      return statusOf(q) !== "待裁定";
    }).length;
    var total = state.questions.length;
    var percent = total ? Math.round(decided * 100 / total) : 0;
    el.progressFill.style.width = percent + "%";
    el.progressText.textContent = "共 " + total + " 项，已裁定 " + decided +
      " 项，未裁定 " + (total - decided) + " 项（" + percent + "%）";

    var database = state.databases.filter(function (d) { return d.path === state.db; })[0];
    el.dbMeta.textContent = database
      ? (database.gaps + " 项 / 已裁定 " + database.decided)
      : "";

    var visible = state.questions.filter(function (q) {
      var status = statusOf(q);
      if (state.filter === "pending") { return status === "待裁定"; }
      if (state.filter === "decided") { return status !== "待裁定"; }
      return true;
    });

    el.list.textContent = "";
    if (!visible.length) {
      el.list.appendChild(mk("div", "empty", "当前筛选下没有条目。"));
      return;
    }
    visible.forEach(function (question) {
      el.list.appendChild(renderCard(question));
    });
  }

  function renderCard(question) {
    var decision = question.decision || {};
    var status = statusOf(question);
    var card = mk("section", "card" + (status !== "待裁定" ? " decided" : ""));
    card.dataset.gapId = question.gap_id;

    // ---- 头部
    var head = mk("div", "card-head");
    var titleRow = mk("div", "card-title");
    titleRow.appendChild(mk("span", "gap-id mono", question.gap_id));
    titleRow.appendChild(mk("span", "gap-title", question.title));
    head.appendChild(titleRow);

    var tags = mk("div", "card-tags");
    if (question.level) {
      tags.appendChild(mk("span", "tag " + question.level.toLowerCase(), question.level));
    }
    if (question.owner) { tags.appendChild(mk("span", "tag", question.owner)); }
    if (question.priority_round) {
      tags.appendChild(mk("span", "tag round", question.priority_round));
    }
    tags.appendChild(mk("span", "tag" + (status !== "待裁定" ? " done" : ""),
      "状态：" + status));
    if (decision.needs_followup) {
      tags.appendChild(mk("span", "tag b0", "候选与预期方案同时存在，需复核"));
    }
    head.appendChild(tags);
    card.appendChild(head);

    // ---- 选项区
    var body = mk("div", "card-body");
    var groupName = "gap-" + question.gap_id;

    question.options.forEach(function (option) {
      body.appendChild(renderOption(question, option, groupName));
    });

    // ---- 备注区
    var extra = document.createElement("details");
    extra.className = "extra";
    if (decision.decision_basis || decision.extra_requirement) {
      extra.open = true;
    }
    extra.appendChild(mk("summary", null, "裁定理由与补充要求（可选）"));

    extra.appendChild(extraRow("裁定理由", "basis", question, decision.decision_basis,
      "为什么这样选，便于后续复核"));
    extra.appendChild(extraRow("补充要求", "extra", question, decision.extra_requirement,
      "候选未覆盖的细节，例如需要同时满足的例外"));
    body.appendChild(extra);

    card.appendChild(body);

    // ---- 底部
    var foot = mk("div", "card-foot");
    foot.appendChild(mk("span", null,
      "影响范围：" + (question.impact_scope || "未标注")));
    foot.appendChild(mk("span", "spacer"));
    if (decision.filled_at) {
      foot.appendChild(mk("span", null, "写入于 " + decision.filled_at));
    }
    var clearBtn = mk("button", "mini", "清除本项裁定");
    clearBtn.type = "button";
    clearBtn.addEventListener("click", function () { clearDecision(question); });
    foot.appendChild(clearBtn);
    card.appendChild(foot);

    return card;
  }

  function renderOption(question, option, groupName) {
    var decision = question.decision || {};
    var isChosen = decision.chosen_option_id === option.option_id;
    var isActive = option.custom
      ? (decision.answer_text && decision.answer_text.length > 0)
      : isChosen;
    var row = mk("label", "opt" + (option.custom ? " custom" : "") +
      (isActive ? " selected" : ""));

    var radio = document.createElement("input");
    radio.type = "radio";
    radio.name = groupName;
    radio.value = option.custom ? "__custom__" : option.option_id;
    radio.checked = !!isActive;
    radio.addEventListener("change", function () {
      if (option.custom) { onCustomRadio(question, radio); }
      else { chooseCandidate(question, option, radio); }
    });
    row.appendChild(radio);

    var main = mk("div", "opt-main");
    var head = mk("div", "opt-head");
    // 没有候选项的缺口：分析阶段认定属明显设计空缺，只有自定义预留行，
    // 提示语改为直接填写需要设计的内容。
    var openOnly = question.options && question.options.length === 1 &&
      question.options[0].custom;
    if (option.custom) {
      head.appendChild(mk("span", "opt-label", "自定义"));
      head.appendChild(mk("span", "opt-name", openOnly
        ? "本项没有候选，请直接填写需要设计的内容"
        : "候选都不符合时，在此填写预期设计方案"));
    } else {
      head.appendChild(mk("span", "opt-label", "候选 " + option.label));
      head.appendChild(mk("span", "opt-name", option.title));
      if (option.recommended) { head.appendChild(mk("span", "badge", "推荐")); }
    }
    main.appendChild(head);

    if (option.custom) {
      var area = document.createElement("textarea");
      area.className = "custom-area";
      area.placeholder = openOnly
        ? "写下需要设计的内容与期望的规则形态，越具体越好；保存后写入该库 decisions 表的 answer_text 字段。"
        : "写下你预期的设计规则，越具体越好；保存后写入该库 decisions 表的 answer_text 字段。";
      area.value = decision.answer_text || "";
      area.addEventListener("click", function (event) { event.preventDefault(); });
      area.addEventListener("input", function () {
        radio.checked = true;
        row.classList.add("selected");
        setSaveState("预期方案已修改，失焦或点击保存后写入");
      });
      area.addEventListener("blur", function () { saveCustom(question, area.value); });
      main.appendChild(area);

      var saveCustomBtn = mk("button", "mini", "保存预期方案");
      saveCustomBtn.type = "button";
      saveCustomBtn.style.marginTop = "8px";
      saveCustomBtn.addEventListener("click", function (event) {
        event.preventDefault();
        saveCustom(question, area.value);
      });
      main.appendChild(saveCustomBtn);
    } else {
      main.appendChild(mk("p", "opt-detail", option.detail));
      var tradeoff = mk("p", "opt-tradeoff");
      tradeoff.appendChild(mk("b", null, "代价与影响："));
      tradeoff.appendChild(document.createTextNode(option.tradeoff));
      main.appendChild(tradeoff);
    }

    row.appendChild(main);
    return row;
  }

  function extraRow(labelText, kind, question, value, placeholder) {
    var row = mk("div", "extra-row");
    var label = mk("label", null, labelText);
    var input = document.createElement("input");
    input.type = "text";
    input.value = value || "";
    input.placeholder = placeholder;
    input.dataset.kind = kind;
    var id = "extra-" + kind + "-" + question.gap_id;
    input.id = id;
    label.setAttribute("for", id);
    input.addEventListener("blur", function () { saveDecision(question); });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") { input.blur(); }
    });
    row.appendChild(label);
    row.appendChild(input);
    return row;
  }

  // ------------------------------------------------------------ 写入
  function collect(question) {
    var card = el.list.querySelector('[data-gap-id="' + question.gap_id + '"]');
    var payload = { db: state.db, gap_id: question.gap_id };
    if (card) {
      var checked = card.querySelector('input[type="radio"]:checked');
      if (checked && checked.value !== "__custom__") {
        payload.chosen_option_id = checked.value;
      }
      var area = card.querySelector(".custom-area");
      if (area && area.value.trim()) { payload.answer_text = area.value.trim(); }
      var basis = card.querySelector('input[data-kind="basis"]');
      if (basis && basis.value.trim()) { payload.decision_basis = basis.value.trim(); }
      var extra = card.querySelector('input[data-kind="extra"]');
      if (extra && extra.value.trim()) { payload.extra_requirement = extra.value.trim(); }
    }
    return payload;
  }

  function saveDecision(question) {
    var payload = collect(question);
    if (!payload.chosen_option_id && !payload.answer_text) {
      payload.chosen_option_id = null;
    }
    setSaveState("正在保存…");
    return api("/api/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (data) {
      applyDecision(question, data.decision);
      setSaveState("已保存 " + question.gap_id + "　" + data.decision.status);
      refreshDatabaseMeta();
    }).catch(function (error) {
      setSaveState("保存失败：" + error.message, true);
      toast("保存失败：" + error.message, true);
    });
  }

  function chooseCandidate(question, option, radio) {
    var payload = {
      db: state.db,
      gap_id: question.gap_id,
      chosen_option_id: option.option_id
    };
    var card = radio.closest(".card");
    var area = card && card.querySelector(".custom-area");
    if (area && area.value.trim()) { payload.answer_text = area.value.trim(); }
    var basis = card && card.querySelector('input[data-kind="basis"]');
    if (basis && basis.value.trim()) { payload.decision_basis = basis.value.trim(); }
    var extra = card && card.querySelector('input[data-kind="extra"]');
    if (extra && extra.value.trim()) { payload.extra_requirement = extra.value.trim(); }

    setSaveState("正在保存…");
    api("/api/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (data) {
      applyDecision(question, data.decision);
      setSaveState("已保存 " + question.gap_id + "　候选 " + option.label);
      refreshDatabaseMeta();
    }).catch(function (error) {
      radio.checked = false;
      setSaveState("保存失败：" + error.message, true);
      toast("保存失败：" + error.message, true);
    });
  }

  function onCustomRadio(question, radio) {
    var card = radio.closest(".card");
    var area = card && card.querySelector(".custom-area");
    if (area) { area.focus(); }
    setSaveState("已选中自定义方案，填写内容后失焦或点击保存");
  }

  function saveCustom(question, text) {
    var payload = collect(question);
    if (!payload.answer_text) {
      toast("预期方案为空，未写入", true);
      return;
    }
    setSaveState("正在保存…");
    api("/api/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (data) {
      applyDecision(question, data.decision);
      setSaveState("已保存 " + question.gap_id + "　自定义方案");
      refreshDatabaseMeta();
    }).catch(function (error) {
      setSaveState("保存失败：" + error.message, true);
      toast("保存失败：" + error.message, true);
    });
  }

  function clearDecision(question) {
    api("/api/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ db: state.db, gap_id: question.gap_id })
    }).then(function () {
      question.decision = {
        chosen_option_id: "", answer_text: "", decision_basis: "",
        extra_requirement: "", status: "待裁定", filled_at: "", needs_followup: false
      };
      render();
      setSaveState("已清除 " + question.gap_id);
      refreshDatabaseMeta();
    }).catch(function (error) {
      toast("清除失败：" + error.message, true);
    });
  }

  function applyDecision(question, decision) {
    question.decision = {
      chosen_option_id: decision.chosen_option_id || "",
      answer_text: (collect(question).answer_text) || "",
      decision_basis: question.decision && question.decision.decision_basis || "",
      extra_requirement: question.decision && question.decision.extra_requirement || "",
      status: decision.status,
      filled_at: question.decision && question.decision.filled_at || "",
      needs_followup: decision.needs_followup
    };
    var card = el.list.querySelector('[data-gap-id="' + question.gap_id + '"]');
    if (card) {
      var area = card.querySelector(".custom-area");
      if (area) { question.decision.answer_text = area.value.trim(); }
      var basis = card.querySelector('input[data-kind="basis"]');
      if (basis) { question.decision.decision_basis = basis.value.trim(); }
      var extra = card.querySelector('input[data-kind="extra"]');
      if (extra) { question.decision.extra_requirement = extra.value.trim(); }
      updateCardState(question, card);
    }
    updateProgressOnly();
  }

  function updateCardState(question, card) {
    var decision = question.decision;
    var status = decision.status;
    card.classList.toggle("decided", status !== "待裁定");
    var statusTag = card.querySelector(".card-tags .tag:last-child");
    if (statusTag) {
      statusTag.textContent = "状态：" + status;
      statusTag.classList.toggle("done", status !== "待裁定");
    }
    var rows = card.querySelectorAll(".opt");
    question.options.forEach(function (option, index) {
      var row = rows[index];
      if (!row) { return; }
      var active = option.custom
        ? !!(decision.answer_text && decision.answer_text.length)
        : decision.chosen_option_id === option.option_id;
      row.classList.toggle("selected", active);
      var radio = row.querySelector('input[type="radio"]');
      if (radio) { radio.checked = active; }
    });
  }

  function updateProgressOnly() {
    var decided = state.questions.filter(function (q) {
      return statusOf(q) !== "待裁定";
    }).length;
    var total = state.questions.length;
    var percent = total ? Math.round(decided * 100 / total) : 0;
    el.progressFill.style.width = percent + "%";
    el.progressText.textContent = "共 " + total + " 项，已裁定 " + decided +
      " 项，未裁定 " + (total - decided) + " 项（" + percent + "%）";
  }

  function refreshDatabaseMeta() {
    return api("/api/databases").then(function (data) {
      state.databases = data.databases || [];
      var current = state.databases.filter(function (d) { return d.path === state.db; })[0];
      if (!current) { return; }
      el.dbMeta.textContent = current.gaps + " 项 / 已裁定 " + current.decided;
      var option = el.select.querySelector('option[value="' + current.path + '"]');
      if (option) {
        option.textContent = current.name + "　（" + current.decided + "/" +
          current.gaps + " 已裁定）";
      }
    }).catch(function () { /* 元信息刷新失败不影响填写 */ });
  }

  // ------------------------------------------------------------ 事件绑定
  el.select.addEventListener("change", function () {
    state.db = el.select.value;
    el.exportLink.href = "/api/export?db=" + encodeURIComponent(state.db);
    el.footDb.textContent = state.db;
    api("/api/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ db: state.db })
    }).catch(function () { /* 选择失败时仍按路径读取 */ })
      .then(loadQuestions);
  });

  el.refresh.addEventListener("click", function () {
    loadDatabases(state.db).then(loadQuestions);
  });

  Array.prototype.forEach.call(el.filters, function (chip) {
    chip.addEventListener("click", function () {
      Array.prototype.forEach.call(el.filters, function (other) {
        other.classList.remove("active");
      });
      chip.classList.add("active");
      state.filter = chip.dataset.filter;
      render();
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") { el.toast.className = "toast"; }
  });

  // ------------------------------------------------------------ 启动
  loadDatabases().then(function (db) {
    if (db) { return loadQuestions(); }
    return null;
  }).catch(function (error) {
    el.list.textContent = "";
    el.list.appendChild(mk("div", "empty", "载入失败：" + error.message));
  });
})();
