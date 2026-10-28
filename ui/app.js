// Music Tool UI: plain JS, no libraries. All text stays short and plain.
const $ = (id) => document.getElementById(id);

function player(url, label) {
  const wrap = document.createElement("div");
  const p = document.createElement("p");
  p.textContent = label;
  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "none";
  audio.src = url;
  wrap.append(p, audio);
  return wrap;
}

function showError(el, data) {
  el.textContent = "Sorry, that did not work: " + (data.error || "unknown error");
}

// ---------- Make music ----------
$("make-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const status = $("make-status");
  const result = $("make-result");
  status.textContent = "Making music… please wait.";
  result.hidden = true;
  const body = {
    name: $("make-name").value.trim(),
    style: $("make-style").value,
    tempo: Number($("make-tempo").value),
    key: $("make-key").value.trim(),
    bars: Number($("make-bars").value),
    seed: Number($("make-seed").value),
  };
  let data;
  try {
    const res = await fetch("/api/make", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    data = await res.json();
    if (!res.ok) throw data;
  } catch (err) {
    showError(status, err && err.error ? err : { error: "could not reach the server" });
    return;
  }
  status.textContent = "Done! Press play below.";
  result.hidden = false;
  $("make-result-title").textContent = data.track + " — " + data.style;
  const mixBox = $("make-mix");
  const stemBox = $("make-stems");
  mixBox.innerHTML = "";
  stemBox.innerHTML = "";
  if (data.mix) mixBox.append(player(data.mix.url, "Mix — all parts together"));
  data.stems.forEach((s) => stemBox.append(player(s.url, "Part: " + s.stem)));
  // QC badge
  const badge = $("make-qc-badge");
  badge.textContent = "Checking…";
  badge.className = "badge";
  try {
    const res = await fetch("/api/qc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track: data.track }),
    });
    const qc = await res.json();
    badge.textContent = qc.pass ? "QC passed ✓" : "QC failed ✗";
    badge.className = "badge " + (qc.pass ? "pass" : "fail");
  } catch {
    badge.textContent = "QC check did not run";
  }
});

// ---------- Preset tracks ----------
const STYLE_MATCH = {
  lofi: "lo-fi", synthwave: "synthwave", folk: "folk",
  dark: "dark", epic: "epic",
};

async function loadPresets() {
  const list = $("preset-list");
  list.innerHTML = "<p>Loading…</p>";
  const filter = $("preset-filter").value;
  let data;
  try {
    data = await (await fetch("/api/tracks")).json();
  } catch {
    list.innerHTML = "<p>Sorry, the track list did not load.</p>";
    return;
  }
  let tracks = data.presets || [];
  if (filter) {
    const needle = STYLE_MATCH[filter];
    tracks = tracks.filter((t) => t.style.toLowerCase().includes(needle));
  }
  list.innerHTML = "";
  for (const t of tracks) {
    const card = document.createElement("div");
    card.className = "card";
    const h = document.createElement("h3");
    h.textContent = t.name;
    const info = document.createElement("p");
    info.textContent = `${t.style} · ${t.tempo_bpm} beats per minute · ${t.key} · ${t.mood}`;
    card.append(h, info);
    let detail;
    try {
      detail = await (await fetch("/api/track?name=" + encodeURIComponent(t.name))).json();
    } catch { detail = null; }
    if (detail && detail.mix) {
      card.append(player(detail.mix.url, "Mix — all parts together"));
      if (detail.stems && detail.stems.length) {
        const det = document.createElement("details");
        const sum = document.createElement("summary");
        sum.textContent = "Parts (" + detail.stems.length + ") — tap to open";
        det.append(sum);
        detail.stems.forEach((s) => {
          const d = document.createElement("div");
          d.className = "stem";
          d.append(player(s.url, "Part: " + s.stem));
          det.append(d);
        });
        card.append(det);
      }
    } else {
      const note = document.createElement("p");
      note.textContent = "Not made yet on this machine. Run: python3 music_tool.py render " + t.name;
      card.append(note);
    }
    list.append(card);
  }
}
$("preset-filter").addEventListener("change", loadPresets);

// ---------- Old game music ----------
let oldPage = 0;
let oldTotal = 0;
const OLD_PER_PAGE = 20;

async function loadOld() {
  const list = $("old-list");
  list.innerHTML = "<p>Loading…</p>";
  const q = $("old-search").value.trim();
  const offset = oldPage * OLD_PER_PAGE;
  let data;
  try {
    const url = `/api/tracks?q=${encodeURIComponent(q)}&limit=${OLD_PER_PAGE}&offset=${offset}`;
    data = await (await fetch(url)).json();
  } catch {
    list.innerHTML = "<p>Sorry, the old songs did not load.</p>";
    return;
  }
  oldTotal = data.total_old || 0;
  const pages = Math.max(1, Math.ceil(oldTotal / OLD_PER_PAGE));
  const info = `Page ${oldPage + 1} of ${pages} — ${oldTotal} songs`;
  $("old-page-info").textContent = info;
  $("old-page-info2").textContent = info;
  list.innerHTML = "";
  (data.old || []).forEach((m) => {
    const row = document.createElement("div");
    row.className = "row";
    const h = document.createElement("h3");
    h.textContent = m.name;
    row.append(h, player(m.url, "Song"));
    list.append(row);
  });
  if (!(data.old || []).length) list.innerHTML = "<p>No songs match that search.</p>";
}

function oldGo(delta) {
  const pages = Math.max(1, Math.ceil(oldTotal / OLD_PER_PAGE));
  oldPage = Math.min(Math.max(0, oldPage + delta), pages - 1);
  loadOld();
  document.getElementById("old").scrollIntoView();
}
$("old-prev").addEventListener("click", () => oldGo(-1));
$("old-next").addEventListener("click", () => oldGo(1));
$("old-prev2").addEventListener("click", () => oldGo(-1));
$("old-next2").addEventListener("click", () => oldGo(1));
let searchTimer = null;
$("old-search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { oldPage = 0; loadOld(); }, 300);
});

// ---------- Copy buttons ----------
document.querySelectorAll(".copy").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const text = btn.getAttribute("data-copy") || "";
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied!";
      setTimeout(() => { btn.textContent = "Copy commands"; }, 2000);
    } catch {
      btn.textContent = "Copy did not work — select the text by hand";
    }
  });
});

loadPresets();
loadOld();
