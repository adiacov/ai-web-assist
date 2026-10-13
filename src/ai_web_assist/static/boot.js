// Runs before first paint: apply the saved theme, font size and panel sizes (no flash).
try {
  const r = document.documentElement, get = (k) => localStorage.getItem("awa." + k);
  const t = get("theme");
  if (t === "light" || t === "dark") {
    r.setAttribute("data-theme", t);
    document.getElementById("hlLight").media = t === "light" ? "all" : "not all";
    document.getElementById("hlDark").media = t === "dark" ? "all" : "not all";
  }
  if (get("fontSize")) r.style.setProperty("--fs", get("fontSize"));
  if (Number(get("chatWidth"))) r.style.setProperty("--chat-w", get("chatWidth") + "px");
  if (Number(get("inputHeight"))) r.style.setProperty("--input-h", get("inputHeight") + "px");
} catch {}
