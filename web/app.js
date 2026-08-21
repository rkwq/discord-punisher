const state = {
  config: null,
};

const $ = (id) => document.getElementById(id);

function setStatus(message) {
  $("status").textContent = message;
}

function getValue(id) {
  return $(id).value.trim();
}

function setValue(id, value) {
  $(id).value = value || "";
}

function renderFields(fields) {
  const container = $("fields");
  container.innerHTML = "";

  fields.slice(0, 5).forEach((field, index) => {
    const row = document.createElement("div");
    row.className = "field-row";
    row.innerHTML = `
      <div class="grid two">
        <label>Label<input data-field="label" value="${escapeHtml(field.label || "")}" maxlength="45"></label>
        <label>Placeholder<input data-field="placeholder" value="${escapeHtml(field.placeholder || "")}" maxlength="100"></label>
      </div>
      <div class="field-actions">
        <label><input data-field="required" type="checkbox" ${field.required ? "checked" : ""}> Required</label>
        <button type="button" class="remove-field">Remove</button>
      </div>
    `;
    row.querySelector(".remove-field").addEventListener("click", () => {
      state.config.role_request.fields.splice(index, 1);
      renderFields(state.config.role_request.fields);
      updatePreview();
    });
    row.querySelectorAll("input").forEach((input) => {
      input.addEventListener("input", () => {
        const key = input.dataset.field;
        state.config.role_request.fields[index][key] = input.type === "checkbox" ? input.checked : input.value;
        updatePreview();
      });
    });
    container.appendChild(row);
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function populate(config) {
  $("welcomeEnabled").checked = !!config.welcome.enabled;
  setValue("welcomeChannel", config.welcome.channel_id);
  setValue("welcomeTitle", config.welcome.title);
  setValue("welcomeMessage", config.welcome.message);
  setValue("welcomeImage", config.welcome.image_url);
  setValue("welcomeThumb", config.welcome.thumbnail_url);
  setValue("welcomeColor", config.welcome.color || "#5865F2");

  $("roleEnabled").checked = !!config.role_request.enabled;
  setValue("panelChannel", config.role_request.panel_channel_id);
  setValue("submissionChannel", config.role_request.submission_channel_id);
  setValue("reviewerRole", config.role_request.reviewer_role_id);
  setValue("assignRole", config.role_request.assign_role_id);
  setValue("panelTitle", config.role_request.panel_title);
  setValue("panelMessage", config.role_request.panel_message);
  setValue("panelImage", config.role_request.panel_image_url);
  setValue("panelThumb", config.role_request.panel_thumbnail_url);
  setValue("roleColor", config.role_request.color || "#C81E3A");
  setValue("buttonLabel", config.role_request.button_label);
  setValue("buttonEmoji", config.role_request.button_emoji);
  setValue("formTitle", config.role_request.form_title);
  setValue("formWarning", config.role_request.form_warning);

  renderFields(config.role_request.fields || []);
  updatePreview();
}

function collect() {
  const fields = Array.from($("fields").querySelectorAll(".field-row")).map((row) => ({
    label: row.querySelector('[data-field="label"]').value.trim(),
    placeholder: row.querySelector('[data-field="placeholder"]').value.trim(),
    required: row.querySelector('[data-field="required"]').checked,
  })).filter((field) => field.label);

  return {
    welcome: {
      enabled: $("welcomeEnabled").checked,
      channel_id: getValue("welcomeChannel"),
      title: getValue("welcomeTitle"),
      message: getValue("welcomeMessage"),
      image_url: getValue("welcomeImage"),
      thumbnail_url: getValue("welcomeThumb"),
      color: getValue("welcomeColor") || "#5865F2",
    },
    role_request: {
      enabled: $("roleEnabled").checked,
      panel_channel_id: getValue("panelChannel"),
      submission_channel_id: getValue("submissionChannel"),
      reviewer_role_id: getValue("reviewerRole"),
      assign_role_id: getValue("assignRole"),
      panel_title: getValue("panelTitle"),
      panel_message: getValue("panelMessage"),
      panel_image_url: getValue("panelImage"),
      panel_thumbnail_url: getValue("panelThumb"),
      color: getValue("roleColor") || "#C81E3A",
      button_label: getValue("buttonLabel"),
      button_emoji: getValue("buttonEmoji"),
      form_title: getValue("formTitle"),
      form_warning: getValue("formWarning"),
      fields,
    },
  };
}

function messageHead(appName) {
  return `
    <div class="discord-msg-head">
      <div class="discord-avatar">P</div>
      <div>
        <span class="discord-author">${escapeHtml(appName)}</span><span class="discord-app-badge">APP</span>
        <span class="discord-time">Today at 11:17 AM</span>
      </div>
    </div>
  `;
}

function updatePreview() {
  const config = collect();
  const welcomeText = config.welcome.message
    .replaceAll("{member}", "@Member")
    .replaceAll("{server}", "Your Server")
    .replaceAll("{count}", "120")
    .replaceAll("{name}", "Member");

  $("welcomePreview").style.setProperty("--embed-color", config.welcome.color || "#5865F2");
  $("welcomePreview").innerHTML = `
    ${messageHead("Punisher Manager")}
    <div class="discord-embed">
      <h3>${escapeHtml(config.welcome.title || "Welcome")}</h3>
      <p>${escapeHtml(welcomeText || "Welcome message preview")}</p>
      ${config.welcome.image_url ? `<img class="preview-image" src="${escapeHtml(config.welcome.image_url)}" alt="">` : ""}
    </div>
  `;

  const fields = config.role_request.fields
    .map((field) => `<div class="preview-field"><span class="field-dot"></span>${escapeHtml(field.label)}${field.required ? '<span class="field-req">*</span>' : ""}</div>`)
    .join("");
  $("rolePreview").style.setProperty("--embed-color", config.role_request.color || "#C81E3A");
  $("rolePreview").innerHTML = `
    ${messageHead("Punisher Manager")}
    <div class="discord-embed">
      <h3>${escapeHtml(config.role_request.panel_title || "Role Request System")}</h3>
      <p>${escapeHtml(config.role_request.panel_message || "")}</p>
      ${config.role_request.panel_image_url ? `<img class="preview-image" src="${escapeHtml(config.role_request.panel_image_url)}" alt="">` : ""}
      <div class="preview-fields">${fields || '<p class="muted">No form fields configured.</p>'}</div>
    </div>
    <span class="preview-button">${escapeHtml(config.role_request.button_emoji || "")} ${escapeHtml(config.role_request.button_label || "Submit Request")}</span>
  `;
}

async function loadConfig() {
  const response = await fetch("/api/config");
  state.config = await response.json();
  populate(state.config);
  setStatus("Ready");
}

async function saveConfig() {
  const config = collect();
  const response = await fetch("/api/config", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    setStatus("Save failed");
    return;
  }
  const result = await response.json();
  state.config = result.config;
  populate(state.config);
  setStatus("Saved. Restart the bot or repost the panel if needed.");
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
    button.classList.add("active");
    $(button.dataset.tab).classList.add("active");
    updatePreview();
  });
});

document.querySelectorAll("input, textarea").forEach((input) => {
  input.addEventListener("input", updatePreview);
});

$("addField").addEventListener("click", () => {
  const fields = state.config.role_request.fields;
  if (fields.length >= 5) {
    setStatus("Discord modals allow up to 5 fields.");
    return;
  }
  fields.push({label: "New Field", placeholder: "Enter a value", required: true});
  renderFields(fields);
  updatePreview();
});

$("saveBtn").addEventListener("click", saveConfig);
loadConfig().catch(() => setStatus("Could not load settings."));
