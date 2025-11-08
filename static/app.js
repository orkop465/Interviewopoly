// static/app.js
const GROUP_COLORS = {
  BROWN: "#8B4513",
  LIGHT_BLUE: "#ADD8E6",
  PINK: "#FF69B4",
  ORANGE: "#FFA500",
  RED: "#D32F2F",
  YELLOW: "#F7D154",
  GREEN: "#2E7D32",
  DARK_BLUE: "#0D47A1",
  RR: "#000000",
  UTIL: null
};
const BOARD_BLUE = "#CFEFE9";

const el = (sel) => document.querySelector(sel);

let BOARD = [];
let STATE = null;

function idx_to_rc(i){
  i = ((i % 40) + 40) % 40;
  if (i <= 9) return [10, 10 - i];     // bottom
  if (i <= 19) return [10 - (i - 10), 0]; // left
  if (i <= 29) return [0, i - 20];     // top
  return [i - 30, 10];                 // right
}
function isRR(t){ return t.ttype === "COMPANY" && t.payload?.group === "RR"; }
function isUTIL(t){ return t.ttype === "COMPANY" && t.payload?.group === "UTIL"; }
function isProp(t){ return t.ttype === "COMPANY" && !isRR(t) && !isUTIL(t); }

function tileFillStripe(t){
  if (t.ttype === "CHANCE" || t.ttype === "COMMUNITY") return [BOARD_BLUE, null, true];
  if (isProp(t)) return ["#FFFFFF", GROUP_COLORS[t.payload.group], false];
  if (isRR(t)) return ["#FFFFFF", "#000000", false];
  if (isUTIL(t)) return ["#FFFFFF", null, false];
  return ["#FFFFFF", null, false];
}
function emojiFor(t){
  if (t.ttype === "CHANCE") return "❓";
  if (t.ttype === "COMMUNITY") return "🎁";
  if (t.ttype === "TAX") return "💸";
  if (t.ttype === "START") return "▶";
  if (t.ttype === "JAIL") return "⛓";
  if (t.ttype === "FREE_PARKING") return "🅿";
  if (t.ttype === "GOTO_JAIL") return "🚓";
  if (isRR(t)) return "🚂";
  if (isUTIL(t)) return "⚡";
  if (isProp(t)) return "🏠";
  return "";
}

function buildBoard(){
  const board = el("#board");
  const keep = new Set([".center-logo", "#pawn", "#dice-overlay", "#loading"]);
  [...board.children].forEach(ch => {
    if (![...keep].some(s => ch.matches(s))) ch.remove();
  });

  BOARD.forEach((t, i) => {
    const [r, c] = idx_to_rc(i);
    const [fill, stripe, ghost] = tileFillStripe(t);
    const rot =
      r === 10 ? "rot-0" :
      c === 0 ? "rot-90" :
      r === 0 ? "rot-180" : "rot-270";

    const cell = document.createElement("div");
    cell.className = "cell";
    cell.id = "cell-" + i;
    cell.style.gridRow = (r+1);
    cell.style.gridColumn = (c+1);

    const inner = document.createElement("div");
    inner.className = "tile-inner " + rot;
    inner.style.setProperty("--tile-bg", fill);
    if (stripe) inner.style.setProperty("--stripe", stripe);

    const stripeDiv = document.createElement("div");
    stripeDiv.className = "stripe" + (ghost ? " ghost" : "");
    inner.appendChild(stripeDiv);

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = t.name;
    inner.appendChild(title);

    const emw = document.createElement("div");
    emw.className = "emoji-wrap";
    const em = document.createElement("div");
    em.className = "emoji";
    em.textContent = emojiFor(t);
    emw.appendChild(em);
    inner.appendChild(emw);

    // Property question-type badge, raised above pawn
    if (isProp(t)) {
      const badge = document.createElement("div");
      badge.className = "qbadge";
      const qk = (t.payload?.qkind || "").toUpperCase();
      badge.textContent = qk === "LC" ? "LC" : qk === "SD" ? "SD" : qk === "BH" ? "BH" : "";
      inner.appendChild(badge);
    }

    cell.appendChild(inner);
    board.appendChild(cell);
  });
}

function centerOf(elm){
  const r = elm.getBoundingClientRect();
  return [r.left + r.width/2 + window.scrollX, r.top + r.height/2 + window.scrollY];
}
function placePawnAtIndex(idx, instant=false){
  const pawn = el("#pawn");
  const cell = el("#cell-"+idx);
  const board = el("#board");
  if (!pawn || !cell || !board) return;
  const [cx, cy] = centerOf(cell);
  const br = board.getBoundingClientRect();
  const bx = br.left + window.scrollX;
  const by = br.top + window.scrollY;
  if (instant) pawn.style.transition = "none";
  pawn.style.transform = `translate(${cx - bx}px, ${cy - by}px)`;
  if (instant){ void pawn.offsetWidth; pawn.style.transition = "transform 260ms ease"; }
}

function waitTransition(elm, timeoutMs = 300){
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      elm.removeEventListener("transitionend", finish);
      resolve();
    };
    elm.addEventListener("transitionend", finish, { once: true });
    setTimeout(finish, timeoutMs + 80);
  });
}

async function refresh(){
  const res = await fetch("/state");
  const data = await res.json();
  STATE = data;
  BOARD = data.board;
  buildBoard();
  updateHud();
  placePawnAtIndex(STATE.pos, true);
  renderOutcome(STATE.last_outcome);
}

function updateHud(){
  el("#m-cash").textContent = "$" + STATE.cash;
  el("#m-offers").textContent = STATE.offers;
  el("#m-turns").textContent = STATE.turns;
  el("#m-owned").textContent = STATE.owned.length;
}

function renderOutcome(outc){
  const box = el("#outcome");
  if (!outc){ box.classList.add("hidden"); return; }
  box.className = "outcome";
  if (outc.kind) box.classList.add(outc.kind);
  box.innerHTML = `<strong>${outc.title || ""}</strong>` + (outc.feedback ? `<div style="margin-top:6px">${outc.feedback}</div>` : "");
  box.classList.remove("hidden");
}

function setLoading(on){
  const overlay = el("#loading");
  overlay.classList.toggle("hidden", !on);
  const btn = el("#btn-roll");
  btn.disabled = on;
  btn.classList.toggle("disabled", on);
}

function spinDiceFor(ms, finalFace){
  return new Promise((resolve) => {
    const overlay = el("#dice-overlay");
    const die = el("#die");
    overlay.classList.remove("hidden");
    let id = setInterval(() => {
      const f = 1 + Math.floor(Math.random()*6);
      die.className = "dice face-" + f;
    }, 90);
    setTimeout(() => {
      clearInterval(id);
      die.className = "dice face-" + finalFace;
      resolve();
    }, ms);
  });
}

async function walkPath(path, stepMs){
  const pawn = el("#pawn");
  if (!Array.isArray(path) || path.length === 0) return;
  for (let i = 0; i < path.length; i++){
    placePawnAtIndex(path[i], false);
    await waitTransition(pawn, stepMs);
  }
}

async function doRoll(){
  const btn = el("#btn-roll");
  btn.disabled = true;

  const res = await fetch("/roll", {method:"POST"});
  const data = await res.json();

  if (data.skipped){
    await refresh();
    btn.disabled = false;
    return;
  }

  // Start prefetch while animations play
  setLoading(true); // show "preparing question..." indicator
  fetch("/prefetch", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({pos: data.pos})
  }).catch(()=>{});

  // Visual sequence: dice spin -> face hold -> pawn walk
  await spinDiceFor(700, data.roll);
  await new Promise(r => setTimeout(r, 500));
  await walkPath(data.path, 260);
  el("#dice-overlay").classList.add("hidden");

  // Resolve landing (uses prefetch if ready)
  const res2 = await fetch("/resolve", {method:"POST"});
  const rdata = await res2.json();

  setLoading(false);

  if (rdata.pending){
    openPending(rdata.pending);
  } else {
    await refresh();
  }

  btn.disabled = false;
}

function openPending(p){
  const dlg = el("#pending-modal");
  const title = el("#p-title");
  const body = el("#p-body");
  const ta = el("#p-answer");
  ta.value = "";

  if (p.type === "SYS_DESIGN"){
    const diff = p.difficulty ? ` — <em>${p.difficulty}</em>` : "";
    title.innerHTML = "System Design Mini" + diff;
    body.innerHTML = `<p>${p.question.prompt || ""}</p>
      <details><summary>What I’m looking for</summary><ul>
        ${(p.question.rubric||[]).map(x=>`<li>${x}</li>`).join("")}
      </ul></details>`;
  } else if (p.type === "BEHAVIORAL"){
    const diff = p.difficulty ? ` — <em>${p.difficulty}</em>` : "";
    title.innerHTML = "Behavioral (STAR)" + diff;
    body.innerHTML = `<p>${p.question.prompt || ""}</p><p style="opacity:.8">${p.question.tip||""}</p>`;
  } else {
    // LC_* types
    title.textContent = "LeetCode Challenge";
    body.innerHTML = `<p>${p.question.question || ""}</p>
      ${(p.question.hints && p.question.hints.length)
        ? `<details><summary>Hints</summary><ul>${p.question.hints.map(h=>`<li>${h}</li>`).join("")}</ul></details>`
        : ""}`;
  }
  dlg.showModal();

  el("#p-submit").textContent = "Submit";
  el("#p-submit").disabled = false;

  el("#p-submit").onclick = async (e) => {
    e.preventDefault();
    const text = (el("#p-answer").value || "");
    const res = await fetch("/submit_answer", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text})
    });
    const data = await res.json();
    dlg.close();
    await refresh();
    renderOutcome(data.last_outcome);
  };

  const form = el("#pending-form");
  form.querySelector('button[value="cancel"]').textContent = "Cancel";
  form.onsubmit = (e) => { /* default close is fine */ };
}

document.addEventListener("DOMContentLoaded", async () => {
  el("#btn-new").onclick = async () => { await fetch("/new", {method:"POST"}); await refresh(); };
  el("#btn-roll").onclick = doRoll;
  await refresh();
});
