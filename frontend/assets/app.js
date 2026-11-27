"use strict";
/* EMS frontend — vanilla JS, no external dependencies.
 * Rules: every API string goes into the DOM through textContent / setAttribute (never innerHTML),
 * all calls go through api(), a 401 sends the user back to the login page. */

const API = "/api/v1";
const TOKEN_KEY = "ems_token";
const TZ = "Asia/Taipei";

// ---------- helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

function svgEl(tag, attrs = {}, text) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  if (text !== undefined) node.textContent = text;
  return node;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }
const fmt = (n, d = 1) => Number(n).toLocaleString("zh-TW", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (x) => (x * 100).toFixed(1) + "%";

function taipeiToday() {
  // Assemble from numeric parts; locale-formatted strings are not guaranteed to be YYYY-MM-DD.
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", {
    timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date()).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}
function addDays(iso, n) {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

// ---------- session / api ----------
const getToken = () => sessionStorage.getItem(TOKEN_KEY);
function logout() { sessionStorage.removeItem(TOKEN_KEY); location.href = "index.html"; }

async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;
  let payload;
  if (form) payload = new URLSearchParams(form);
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  const res = await fetch(API + path, { method, headers, body: payload });
  if (res.status === 401 && !path.startsWith("/auth/login")) { logout(); throw new Error("登入已過期"); }
  let data = null;
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok) {
    const d = data && data.detail;
    const msg = typeof d === "string" ? d : d && d.detail ? d.detail : Array.isArray(d) ? d.map((e) => e.msg || e.error || JSON.stringify(e)).join("；") : "請求失敗 (" + res.status + ")";
    const err = new Error(msg); err.status = res.status; err.data = data; throw err;
  }
  return data;
}

function requireLogin() {
  if (!getToken()) { location.href = "index.html"; return false; }
  const btn = $("#logout");
  if (btn) btn.addEventListener("click", logout);
  return true;
}

// ---------- shared widgets ----------
async function fillMeterPicker(siteSel, meterSel, onChange) {
  const sites = await api("/sites");
  clear(siteSel);
  for (const s of sites) siteSel.append(el("option", { value: s.id }, s.name));
  let gen = 0;
  async function loadMeters() {
    const mine = ++gen;
    // Drop the previous site's meter and results immediately (also invalidates pending calculations).
    clear(meterSel);
    meterSel._meters = [];
    onChange();
    if (!siteSel.value) return;
    let meters;
    try {
      meters = await api("/meters?site_id=" + encodeURIComponent(siteSel.value));
    } catch (e) {
      if (mine === gen) $("#err").textContent = e.message;   // only for the still-selected site
      return;
    }
    if (mine !== gen) return;           // a newer site selection superseded this response
    meterSel._meters = meters;
    for (const m of meters) meterSel.append(el("option", { value: m.id }, m.name + (m.is_demo && !m.name.includes("模擬") ? "（模擬）" : "")));
    onChange();
  }
  siteSel.addEventListener("change", loadMeters);
  meterSel.addEventListener("change", onChange);
  await loadMeters();
}
const selectedMeter = (meterSel) => (meterSel._meters || []).find((m) => String(m.id) === meterSel.value);

function notes(items, cls) {
  return items && items.length ? el("ul", { class: "notes " + (cls || "") }, items.map((t) => el("li", {}, t))) : null;
}

// ---------- charts (inline SVG) ----------
function barChart(target, bars, { unit, height = 220, yMax } = {}) {
  /* bars: [{label, value, muted, title}] */
  const W = 900, H = height, pad = { l: 48, r: 10, t: 24, b: 28 };
  const svg = svgEl("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img" });
  const max = yMax || Math.max(1, ...bars.map((b) => b.value)) * 1.1;
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + ih - (ih * i) / 4;
    svg.append(svgEl("line", { x1: pad.l, x2: W - pad.r, y1: y, y2: y, stroke: "#e3e8ee" }));
    svg.append(svgEl("text", { x: pad.l - 6, y: y + 4, "text-anchor": "end", "font-size": 11, fill: "#5b6776" }, fmt((max * i) / 4, 0)));
  }
  svg.append(svgEl("text", { x: 4, y: 12, "font-size": 11, fill: "#5b6776" }, unit || ""));
  const bw = iw / Math.max(bars.length, 1);
  bars.forEach((b, i) => {
    const h = (ih * b.value) / max;
    const r = svgEl("rect", { x: pad.l + i * bw + 1, y: pad.t + ih - h, width: Math.max(bw - 2, 1), height: Math.max(h, 0), fill: b.muted ? "#b8c2cc" : "#0b6e4f" });
    r.append(svgEl("title", {}, b.title || `${b.label}: ${fmt(b.value)}`));
    svg.append(r);
    if (b.tick) svg.append(svgEl("text", { x: pad.l + i * bw, y: H - 10, "font-size": 11, fill: "#5b6776" }, b.label));
  });
  clear(target).append(svg);
}

// ---------- pages ----------
function loginPage() {
  const form = $("#login-form"), msg = $("#msg");
  if (getToken()) { location.href = "dashboard.html"; return; }
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    msg.textContent = "";
    try {
      const r = await api("/auth/login", { method: "POST", form: { username: form.email.value, password: form.password.value } });
      sessionStorage.setItem(TOKEN_KEY, r.access_token);
      location.href = "dashboard.html";
    } catch (e) { msg.textContent = e.status === 401 ? "帳號或密碼錯誤" : e.message; }
  });
}

async function dashboardPage() {
  if (!requireLogin()) return;
  const siteSel = $("#site"), meterSel = $("#meter"), days = $("#days");
  const state = { range: 7, gen: 0 };
  function clearAll() {
    for (const id of ["#today-kwh", "#today-coverage", "#max-demand", "#incomplete", "#today-date",
                      "#demand-chart", "#daily-chart", "#daily-body"]) clear($(id));
  }
  async function refresh() {
    // Only the latest request may render: a slower response for a previous meter/range is dropped.
    const gen = ++state.gen;
    const m = selectedMeter(meterSel);
    const badge = $("#demo-badge");
    clear(badge);
    clearAll();
    $("#err").textContent = "";
    if (!m) return;
    if (m.is_demo) badge.append(el("span", { class: "badge" }, "模擬資料"));
    const today = taipeiToday();
    $("#today-date").textContent = today + "（Asia/Taipei）";
    try {
      const [dayRes, dem, hist] = await Promise.all([
        api(`/meters/${m.id}/daily?start=${today}&end=${today}`),
        api(`/meters/${m.id}/demand?date=${today}`),
        api(`/meters/${m.id}/daily?start=${addDays(today, -(state.range - 1))}&end=${today}`),
      ]);
      if (gen !== state.gen) return;
      $("#today-kwh").textContent = fmt(dayRes[0].kwh) + " kWh";
      $("#today-coverage").textContent = "資料覆蓋率 " + pct(dayRes[0].coverage);
      $("#max-demand").textContent = fmt(dem.max_demand_kw) + " kW";
      $("#incomplete").textContent = `不完整區間 ${dem.incomplete_blocks} / 96（不納入最高需量）`;
      barChart($("#demand-chart"), dem.blocks.map((b, i) => ({
        label: String(Math.floor(i / 4)).padStart(2, "0") + ":" + String((i % 4) * 15).padStart(2, "0"),
        value: b.demand_kw, muted: !b.complete, tick: i % 8 === 0,
        title: `${b.start.slice(11, 16)}  ${fmt(b.demand_kw)} kW` + (b.complete ? "" : "（資料不完整）"),
      })), { unit: "kW" });
      barChart($("#daily-chart"), hist.map((d, i) => ({
        label: d.date.slice(5), value: d.kwh, muted: d.coverage < 1, tick: i % Math.ceil(hist.length / 8) === 0,
        title: `${d.date}  ${fmt(d.kwh)} kWh  覆蓋率 ${pct(d.coverage)}`,
      })), { unit: "kWh" });
      const body = clear($("#daily-body"));
      for (const d of [...hist].reverse()) body.append(el("tr", {}, el("td", {}, d.date), el("td", {}, fmt(d.kwh)), el("td", {}, pct(d.coverage))));
    } catch (e) { if (gen === state.gen) $("#err").textContent = e.message; }
  }
  for (const b of days.querySelectorAll("button")) {
    b.addEventListener("click", () => { state.range = Number(b.dataset.days); refresh(); });
  }
  $("#forecast").textContent = "預測：未啟用";
  try { await fillMeterPicker(siteSel, meterSel, refresh); } catch (e) { $("#err").textContent = e.message; }
}

async function billPage() {
  if (!requireLogin()) return;
  const siteSel = $("#site"), meterSel = $("#meter");
  const now = taipeiToday();
  $("#month").value = now.slice(0, 7);
  $("#year").value = now.slice(0, 4);
  let gen = 0;
  async function run() {
    // One generation per run(): both panels render only if this is still the latest selection.
    const mine = ++gen;
    const m = selectedMeter(meterSel);
    clear($("#bill")); clear($("#carbon")); $("#err").textContent = "";
    if (!m) return;
    const month = $("#month").value, year = $("#year").value;
    const current = () => mine === gen;
    const bill = (async () => {
      try {
        const b = await api(`/meters/${m.id}/bill?month=${encodeURIComponent(month)}`);
        if (current()) renderBill(b, m);
      } catch (e) { if (current()) $("#bill").append(el("p", { class: "err" }, "電費：" + e.message)); }
    })();
    const carbon = (async () => {
      try {
        const c = await api(`/meters/${m.id}/scope2?year=${encodeURIComponent(year)}`);
        if (current()) renderCarbon(c);
      } catch (e) { if (current()) $("#carbon").append(el("p", { class: "err" }, "碳排：" + e.message)); }
    })();
    await Promise.all([bill, carbon]);
  }
  $("#run").addEventListener("click", run);
  try { await fillMeterPicker(siteSel, meterSel, run); } catch (e) { $("#err").textContent = e.message; }
}

const PERIOD = { peak: "尖峰", semi_peak: "半尖峰", sat_semi_peak: "週六半尖峰", off_peak: "離峰" };
function renderBill(b, meter) {
  const t = clear($("#bill"));
  t.append(el("h2", {}, `電費試算 ${b.month}`, meter.is_demo ? el("span", { class: "badge" }, "模擬資料") : null));
  t.append(el("p", { class: "muted" }, `電價版本：${b.tariff_versions.join("、")}　${b.voltage === "high" ? "高壓" : "特高壓"}／${b.scheme === "two_stage" ? "二段式" : "三段式"}　資料覆蓋率 ${pct(b.coverage)}`));
  const rows = [
    ["基本電費", b.basic_charge], ["流動電費", b.energy_charge],
    ["行業別調整係數" + (b.coefficient.defaulted ? "（預設 1.0，待確認）" : ""), b.coefficient.value, true],
    ["功率因數調整" + (b.pf_adjustment.available ? `（${b.pf_adjustment.points}%）` : "（無資料）"), b.pf_adjustment.amount],
    ["超約附加費", b.over_contract.amount],
  ];
  const tbl = el("table", {}, el("tbody", {}, rows.map(([k, v, raw]) => el("tr", {}, el("td", {}, k), el("td", {}, raw ? String(v) : fmt(v, 2))))));
  tbl.append(el("tfoot", {}, el("tr", {}, el("th", {}, "合計（新台幣，含 5% 營業稅）"), el("th", {}, fmt(b.total, 2)))));
  t.append(tbl);
  const per = el("table", {}, el("thead", {}, el("tr", {}, el("th", {}, "時段"), el("th", {}, "度數 kWh"), el("th", {}, "最高需量 kW"))),
    el("tbody", {}, Object.keys(PERIOD).filter((p) => b.kwh_by_period[p] || b.max_demand_kw_by_period[p]).map((p) =>
      el("tr", {}, el("td", {}, PERIOD[p]), el("td", {}, fmt(b.kwh_by_period[p])), el("td", {}, fmt(b.max_demand_kw_by_period[p]))))));
  t.append(el("h2", {}, "各時段"), per);
  if (b.warnings.length) t.append(el("h2", {}, "警告 / TODO"), notes(b.warnings, "warn"));
  if (b.assumptions.length) t.append(el("h2", {}, "假設與待核實"), notes(b.assumptions));
}

function renderCarbon(c) {
  const t = clear($("#carbon"));
  t.append(el("h2", {}, `範疇二排碳 ${c.year}`, c.is_demo ? el("span", { class: "badge" }, "模擬資料") : null));
  t.append(el("div", { class: "big" }, fmt(c.scope2_tco2e, 3) + " tCO2e"));
  t.append(el("p", { class: "muted" }, `用電 ${fmt(c.kwh)} kWh　資料覆蓋率 ${pct(c.coverage)}　係數 ${c.factor_kg_per_kwh} kgCO2e/kWh（${c.factor_year} 年度，${c.customer_category === "industrial" ? "產業" : "民生"}）` + (c.provisional ? "　⚠ 暫用係數（provisional）" : "")));
  t.append(notes(c.warnings, "warn"));
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "login") loginPage();
  else if (page === "dashboard") dashboardPage();
  else if (page === "bill") billPage();
});
