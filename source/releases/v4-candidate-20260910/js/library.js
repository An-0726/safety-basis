/* V4 candidate: hazard detail view (library.html?id=H_xxx). */
"use strict";
async function loadDetail() {
  const id = new URLSearchParams(location.search).get("id");
  const box = document.getElementById("detail");
  if (!id) { box.innerHTML = "<p>缺少 id 参数。</p>"; return; }
  try {
    const r = await fetch("data/hazards/" + id + ".json");
    if (!r.ok) throw new Error("not found");
    const h = await r.json();
    const esc = s => (s == null ? "" : String(s).replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])));
    const rows = [
      ["隐患", h.title],
      ["描述", h.description],
      ["分类", h.category],
      ["适用场所", (h.places || []).join("、")],
      ["检查条件", h.conditions],
      ["整改措施", h.measures],
      ["备注", h.note],
    ].filter(r2 => r2[1]).map(r2 => `<div class="row"><div class="k">${esc(r2[0])}</div><div class="v">${esc(r2[1])}</div></div>`).join("");
    box.innerHTML = `<h1>${esc(h.title)}</h1><div class="card">${rows}</div>` +
      `<p><a href="index.html">← 返回搜索</a></p>`;
  } catch (e) {
    box.innerHTML = "<p>未找到该记录（candidate 数据不完整或 id 有误）。</p>";
  }
}
document.addEventListener("DOMContentLoaded", loadDetail);
