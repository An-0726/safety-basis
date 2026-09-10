/* V4 candidate search: relevance-ranked, loads data/search-index.json once. */
"use strict";
let INDEX = [];

async function loadIndex() {
  const r = await fetch("data/search-index.json");
  INDEX = await r.json();
}

function score(q, rec) {
  const qs = q.trim().toLowerCase();
  if (!qs) return 0;
  const title = (rec.title || "").toLowerCase();
  const aliases = (rec.aliases || []).join(" ").toLowerCase();
  const keywords = (rec.keywords || []).join(" ").toLowerCase();
  const law = (rec.lawNames || []).join(" ").toLowerCase();
  const stds = (rec.stdNumbers || []).map(s => s.replace(/[\s\-—–/]/g, "").toLowerCase());
  const qsN = qs.replace(/[\s\-—–/]/g, "");
  let s = 0;
  if (title === qs) s += 120;
  if (title.includes(qs)) s += 80;
  if (aliases.includes(qs)) s += 70;
  if (keywords.includes(qs)) s += 60;
  if (law.includes(qs)) s += 40;
  if (stds.some(st => st === qsN || st.startsWith(qsN))) s += 60;
  if (qs.length >= 2 && title.split(qs).length > 2) s += 20;
  return s;
}

function search(q) {
  const qs = q.trim();
  if (!qs) return [];
  return INDEX
    .map(r => ({ r, s: score(qs, r) }))
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .map(x => x.r);
}

function renderResults(q) {
  const box = document.getElementById("results");
  const stat = document.getElementById("stat");
  const list = search(q);
  stat.textContent = `“${q}” 相关记录 ${list.length} 条（按相关度排序）`;
  box.innerHTML = "";
  list.slice(0, 60).forEach(r => {
    const d = document.createElement("div");
    d.className = "item";
    d.innerHTML =
      `<a href="library.html?id=${r.id}"><b>${r.title}</b></a>` +
      `<span class="tag ${r.status === "已核验" ? "ok" : r.status === "待定" ? "pd" : "rj"}">${r.status}</span>` +
      `<div class="meta">${r.category || ""}${r.places && r.places.length ? " · " + r.places.join("、") : ""}` +
      `${r.lawNames && r.lawNames.length ? " · 依据：" + r.lawNames.join("、") : ""}</div>`;
    box.appendChild(d);
  });
  if (!list.length) box.innerHTML = "<div class='empty'>未找到相关记录。可尝试更口语的表述或标准号。</div>";
}

document.addEventListener("DOMContentLoaded", () => {
  loadIndex().then(() => {
    const q = new URLSearchParams(location.search).get("q") || "";
    const input = document.getElementById("q");
    input.value = q;
    if (q) renderResults(q);
    let t;
    input.addEventListener("input", e => {
      clearTimeout(t);
      t = setTimeout(() => renderResults(e.target.value), 150);
    });
  });
});
