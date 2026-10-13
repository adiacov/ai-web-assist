"use strict";
// AI Web Assist UI: file tree + viewer + chat. No build step; vendored libs are globals (marked, DOMPurify, hljs).

const $ = (id) => document.getElementById(id);
const mainEl = document.querySelector("main");

// ---- browser storage: global keys for display settings, workspace-scoped keys for per-project state ----
const storage = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
  del(k) { try { localStorage.removeItem(k); } catch {} },
  json(k, fallback) { try { return JSON.parse(this.get(k)) ?? fallback; } catch { return fallback; } },
};
let workspaceId = "", title = document.title;
const gkey = (k) => "awa." + k;
const wkey = (k) => `awa.${workspaceId}.${k}`;

const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const renderMarkdown = (s) => DOMPurify.sanitize(marked.parse(s || ""));
const MAX_HIGHLIGHT_CHARS = 300_000;

// ---- file tree ----
let files = [], fileSet = new Set(), treeTruncated = false, treeSig = "";
let current = null, currentMtime = 0;
let seen = {};               // path -> mtime the user last saw; files changed after that get a green dot
let expanded = new Set();    // open folders

const isFresh = (f) => f.path !== current && (seen[f.path] === undefined || f.mtime > seen[f.path]);
const saveSeen = () => storage.set(wkey("seen"), JSON.stringify(seen));
const saveExpanded = () => storage.set(wkey("expanded"), JSON.stringify([...expanded]));

function buildTree() {
  const root = { dirs: new Map(), files: [] };
  for (const f of files) {
    const parts = f.path.split("/");
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!node.dirs.has(parts[i])) node.dirs.set(parts[i], { path: parts.slice(0, i + 1).join("/"), dirs: new Map(), files: [] });
      node = node.dirs.get(parts[i]);
    }
    node.files.push(f);
  }
  return root;
}

const anyFresh = (node) => node.files.some(isFresh) || [...node.dirs.values()].some(anyFresh);
const byName = (a, b) => a.localeCompare(b, undefined, { sensitivity: "base", numeric: true });

function renderNode(node, depth, out) {
  for (const name of [...node.dirs.keys()].sort(byName)) {
    const d = node.dirs.get(name), open = expanded.has(d.path);
    const cls = ["dir", open ? "" : "folded", !open && anyFresh(d) ? "fresh" : ""].join(" ");
    out.push(`<div class="${cls}" data-dir="${escapeHtml(d.path)}" style="--depth:${depth}" role="treeitem" aria-expanded="${open}">` +
      `<span class="chev">▾</span><span class="name">${escapeHtml(name)}</span><span class="dot"></span></div>`);
    if (open) renderNode(d, depth + 1, out);
  }
  for (const f of [...node.files].sort((a, b) => byName(a.path, b.path))) {
    const cls = ["file", f.path === current ? "active" : "", isFresh(f) ? "fresh" : ""].join(" ");
    out.push(`<div class="${cls}" data-path="${escapeHtml(f.path)}" style="--depth:${depth}" role="treeitem" title="${escapeHtml(f.path)}">` +
      `<span class="ico"></span><span class="name">${escapeHtml(f.path.split("/").pop())}</span><span class="dot"></span></div>`);
  }
}

function renderTree() {
  const out = [];
  renderNode(buildTree(), 0, out);
  if (treeTruncated) out.push(`<p class="notice tree-note">Showing the first ${files.length} files.</p>`);
  $("tree").innerHTML = out.join("");
}

function expandTo(path) {
  const parts = path.split("/");
  let changed = false;
  for (let i = 1; i < parts.length; i++) {
    const d = parts.slice(0, i).join("/");
    if (!expanded.has(d)) { expanded.add(d); changed = true; }
  }
  if (changed) saveExpanded();
}

$("tree").addEventListener("click", (e) => {
  const file = e.target.closest(".file");
  if (file) return openFile(file.dataset.path);
  const dir = e.target.closest(".dir");
  if (!dir) return;
  expanded.has(dir.dataset.dir) ? expanded.delete(dir.dataset.dir) : expanded.add(dir.dataset.dir);
  saveExpanded();
  renderTree();
});

async function loadTree() {
  const r = await fetch("/api/tree");
  if (!r.ok) return false;
  const data = await r.json();
  files = data.files; treeTruncated = data.truncated;
  fileSet = new Set(files.map((f) => f.path));
  const sig = files.map((f) => f.path + ":" + f.mtime).join("|");
  const changed = sig !== treeSig;
  treeSig = sig;
  return changed;
}

async function refreshTree() {
  try {
    const changed = await loadTree();
    if (current && !fileSet.has(current)) {
      current = null;
      $("doc").innerHTML = `<p class="notice">This file no longer exists.</p>`;
      renderTree();
      return;
    }
    const cur = files.find((f) => f.path === current);
    if (cur && cur.mtime !== currentMtime) await openFile(current, true);
    else if (changed) renderTree();
  } catch { /* server stopped or restarting; try again on the next tick */ }
}

// ---- viewer ----
const LANG_ALIASES = {
  h: "c", hpp: "cpp", hh: "cpp", cc: "cpp", cxx: "cpp", sbt: "scala", sc: "scala", mjs: "javascript", cjs: "javascript",
  jsx: "javascript", tsx: "typescript", mts: "typescript", yml: "yaml", toml: "ini", cfg: "ini", conf: "ini", properties: "ini",
  zsh: "bash", htm: "html", svg: "xml", kts: "kotlin", pyi: "python", txt: "plaintext", log: "plaintext", csv: "plaintext",
};

function languageFor(path) {
  const name = path.split("/").pop().toLowerCase();
  if (name === "dockerfile" || name.startsWith("dockerfile.") || name.endsWith(".dockerfile")) return "dockerfile";
  if (name === "makefile" || name === "gnumakefile") return "makefile";
  const ext = name.includes(".") ? name.split(".").pop() : "";
  const lang = LANG_ALIASES[ext] || ext;
  return lang && hljs.getLanguage(lang) ? lang : "plaintext";
}

const isMarkdown = (path) => /\.(md|markdown|mdx)$/i.test(path);

function highlightBlocks(el) {
  el.querySelectorAll("pre code").forEach((c) => {
    if (c.textContent.length > MAX_HIGHLIGHT_CHARS) return;
    try { hljs.highlightElement(c); } catch {}
  });
}

function resolveRelative(baseDir, href) {
  const joined = href.startsWith("/") ? href.slice(1) : (baseDir ? baseDir + "/" : "") + href;
  const out = [];
  for (const p of joined.split("/")) {
    if (p === "" || p === ".") continue;
    if (p === "..") out.pop(); else out.push(p);
  }
  return out.join("/");
}

// A code span like `docs/plan.md`, `./docs/plan.md` or `docs/plan.md:12` names a shown file.
function fileRef(text) {
  const t = text.trim().replace(/:\d+(-\d+)?(:\d+)?$/, "").replace(/^\.\//, "");
  return fileSet.has(t) ? t : null;
}

function makeFileLink(el, path) {
  el.classList.add("filelink");
  el.title = "Open " + path;
  el.addEventListener("click", (e) => { e.preventDefault(); openFile(path); });
}

function linkify(el, baseDir = "") {
  el.querySelectorAll("a[href]").forEach((a) => {
    const href = a.getAttribute("href");
    if (/^https?:/i.test(href)) { a.target = "_blank"; a.rel = "noopener noreferrer"; return; }
    if (href.startsWith("#") || /^[a-z][a-z0-9+.-]*:/i.test(href)) return;
    let target;
    try { target = resolveRelative(baseDir, decodeURIComponent(href.split(/[?#]/)[0])); } catch { return; }
    if (fileSet.has(target)) makeFileLink(a, target);
  });
  el.querySelectorAll("code").forEach((c) => {
    if (c.closest("pre") || c.closest("a")) return;
    const path = fileRef(c.textContent);
    if (!path) return;
    const a = document.createElement("a");
    makeFileLink(a, path);
    c.replaceWith(a);
    a.appendChild(c);
  });
}

function showNotice(text) {
  $("doc").className = "md";
  $("doc").innerHTML = `<p class="notice">${escapeHtml(text)}</p>`;
}

async function openFile(path, keepScroll = false) {
  let f;
  try {
    const r = await fetch("/api/file?path=" + encodeURIComponent(path));
    if (!r.ok) return false;
    f = await r.json();
  } catch { return false; }
  const scroll = mainEl.scrollTop;
  current = path; currentMtime = f.mtime;
  storage.set(wkey("file"), path);
  history.replaceState(null, "", "#" + encodeURI(path));
  seen[path] = f.mtime; saveSeen();
  if (!keepScroll) expandTo(path);
  $("path").textContent = path;
  document.title = `${path.split("/").pop()} · ${title}`;

  const doc = $("doc");
  if (f.binary) {
    showNotice("Binary file: not shown.");
  } else if (isMarkdown(path)) {
    doc.className = "md";
    doc.innerHTML = renderMarkdown(f.content);
    highlightBlocks(doc);
    linkify(doc, path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "");
  } else {
    doc.className = "md source";
    const pre = document.createElement("pre"), code = document.createElement("code");
    code.className = "language-" + languageFor(path);
    code.textContent = f.content;
    pre.appendChild(code);
    doc.replaceChildren(pre);
    highlightBlocks(doc);
  }
  if (f.truncated) doc.insertAdjacentHTML("afterbegin", `<p class="notice">Large file: showing the first 1 MB only.</p>`);
  mainEl.scrollTop = keepScroll ? scroll : 0;
  renderTree();
  return true;
}

function hashPath() {
  try { return decodeURI(location.hash.slice(1)); } catch { return ""; }
}

function defaultFile() {
  const linked = hashPath();  // deep link: /#docs/plan.md
  if (linked && fileSet.has(linked)) return linked;
  const saved = storage.get(wkey("file"));
  if (saved && fileSet.has(saved)) return saved;
  if (fileSet.has("README.md")) return "README.md";
  return (files.find((f) => isMarkdown(f.path)) || files[0])?.path || null;
}

// ---- start-up ----
async function init() {
  const cfg = await (await fetch("/api/config")).json();
  workspaceId = cfg.workspace_id; title = cfg.title;
  expanded = new Set(storage.json(wkey("expanded"), []));
  await loadTree();
  const savedSeen = storage.json(wkey("seen"), null);
  if (savedSeen && typeof savedSeen === "object") seen = savedSeen;
  else { for (const f of files) seen[f.path] = f.mtime; saveSeen(); }  // first visit: nothing is "new" yet

  const start = defaultFile();
  if (start) await openFile(start);
  else { renderTree(); showNotice("No files to show in this folder yet."); }

  if (typeof initChat === "function") await initChat();
  setInterval(() => { if (!document.hidden) refreshTree(); }, 2000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshTree(); });
}

window.addEventListener("hashchange", () => {
  const linked = hashPath();
  if (linked && linked !== current && fileSet.has(linked)) openFile(linked);
});
document.addEventListener("DOMContentLoaded", () => init().catch((e) => showNotice("Could not load the workspace: " + e)));
