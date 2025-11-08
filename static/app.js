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

// side 0 (bottom) => 0deg
// side 1 (left)   => -90deg
// side 2 (top)    => -180deg
// side 3 (right)  => -270deg
let ROT_DEG = 0;
let INIT_DONE = false; // only snap once on first load

function idx_to_rc(i){
  i = ((i % 40) + 40) % 40;
  if (i <= 9) return [10, 10 - i];
  if (i <= 19) return [10 - (i - 10), 0];
  if (i <= 29) return [0, i - 20];
  return [i - 30, 10];
}
function sideForIndex(i){
  i = ((i % 40) + 40) % 40;
  if (i <= 9) return 0;
  if (i <= 19) return 1;
  if (i <= 29) return 2;
  return 3;
}
const CORNERS = new Set([0,10,20,30]);
function isCorner(i){ return CORNERS.has(((i % 40)+40)%40); }

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

/* -------------------- Overlays -------------------- */

function ensurePawnOverlay(){
  const wrap = el("#board-wrap");
  if (!wrap) return;
  wrap.style.position = "relative";

  let overlay = el("#pawn-overlay");
  if (!overlay){
    overlay = document.createElement("div");
    overlay.id = "pawn-overlay";
    overlay.style.position = "absolute";
    overlay.style.inset = "0";
    overlay.style.pointerEvents = "none";
    wrap.appendChild(overlay);
  }

  let pawn = el("#pawn");
  if (!pawn){
    pawn = document.createElement("div");
    pawn.id = "pawn";
    pawn.className = "pawn";
  }
  if (pawn.parentElement !== overlay){
    overlay.appendChild(pawn);
  }
}

// Non-rotating HUD overlay (top-right loading chip)
let SPINNER_CSS_INJECTED = false;
function ensureHudOverlay(){
  const wrap = el("#board-wrap");
  if (!wrap) return;

  let hud = el("#hud-overlay");
  if (!hud){
    hud = document.createElement("div");
    hud.id = "hud-overlay";
    Object.assign(hud.style, {
      position:"absolute", inset:"0", pointerEvents:"none", zIndex:"65"
    });
    wrap.appendChild(hud);
  }

  let chip = el("#hud-loading");
  if (!chip){
    chip = document.createElement("div");
    chip.id = "hud-loading";
    Object.assign(chip.style, {
      position:"absolute", top:"8px", right:"8px",
      display:"none",
      background:"#fff",
      borderRadius:"10px",
      padding:"6px 10px",
      boxShadow:"0 10px 30px rgba(0,0,0,.25), inset 0 0 0 1px rgba(0,0,0,.05)",
      fontWeight:"800",
      color:"#111",
      gap:"8px",
      alignItems:"center",
      pointerEvents:"none"
    });
    const dot = document.createElement("div");
    Object.assign(dot.style, {
      width:"14px", height:"14px", borderRadius:"50%",
      border:"3px solid #1115", borderTopColor:"#111",
      marginRight:"6px",
      animation:"spin 1s linear infinite"
    });
    const txt = document.createElement("span");
    txt.textContent = "Preparing question…";
    txt.style.verticalAlign = "middle";

    chip.appendChild(dot);
    chip.appendChild(txt);
    hud.appendChild(chip);

    if (!SPINNER_CSS_INJECTED){
      const style = document.createElement("style");
      style.textContent = "@keyframes spin{to{transform:rotate(360deg)}}";
      document.head.appendChild(style);
      SPINNER_CSS_INJECTED = true;
    }
  }
}

/* -------------------- Board build -------------------- */

function buildBoard(){
  const board = el("#board");
  const keep = new Set([".center-logo", "#dice-overlay", "#loading"]);
  [...board.children].forEach(ch => {
    if (![...keep].some(s => ch.matches(s))) ch.remove();
  });

  BOARD.forEach((t, i) => {
    const [r, c] = idx_to_rc(i);
    const [fill, stripe, ghost] = tileFillStripe(t);
    const rot = r === 10 ? "rot-0" : c === 0 ? "rot-90" : r === 0 ? "rot-180" : "rot-270";

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

// Pawn lives in the non-rotating overlay
function placePawnAtIndex(idx, instant=false){
  ensurePawnOverlay();
  const pawn = el("#pawn");
  const cell = el("#cell-"+idx);
  const overlay = el("#pawn-overlay");
  if (!pawn || !cell || !overlay) return;

  const [cx, cy] = centerOf(cell);
  const or = overlay.getBoundingClientRect();
  const ox = or.left + window.scrollX;
  const oy = or.top + window.scrollY;

  if (instant) pawn.style.transition = "none";
  pawn.style.transform = `translate(${cx - ox}px, ${cy - oy}px)`;
  if (instant){ void pawn.offsetWidth; pawn.style.transition = "transform 260ms ease"; }
}

function waitTransition(elm, timeoutMs = 300){
  return new Promise((resolve) => {
    let done = false;
    const finish = () => { if (done) return; done = true; elm.removeEventListener("transitionend", finish); resolve(); };
    elm.addEventListener("transitionend", finish, { once: true });
    setTimeout(finish, timeoutMs + 120);
  });
}

/* ---------- Dice counter-rotation (keep dice upright) ---------- */
function updateDiceCounterRotation(){
  const overlay = el("#dice-overlay");
  if (!overlay) return;
  overlay.style.transformOrigin = "50% 50%";
  overlay.style.transform = `rotate(${-ROT_DEG}deg)`;
}

/* ---------- Rotation helpers (pivot around center, always CCW) ---------- */

function snapStageRotationForSide(side){
  ROT_DEG = (-90 * side);
  const stage = el(".stage");
  stage.style.transformOrigin = "50% 50%";
  stage.style.transform = `rotate(${ROT_DEG}deg)`;
  normalizeRot();
  updateDiceCounterRotation();
}

async function rotateStageCCW90Center(){
  const stage = el(".stage");
  stage.style.transformOrigin = "50% 50%";
  const from = ROT_DEG;
  const to = ROT_DEG - 90; // strictly CCW by 90
  const anim = stage.animate(
    [{ transform: `rotate(${from}deg)` }, { transform: `rotate(${to}deg)` }],
    { duration: 600, easing: "cubic-bezier(.22,.61,.36,1)", fill: "forwards" }
  );
  await anim.finished.catch(()=>{});
  ROT_DEG = to;
  normalizeRot();
  updateDiceCounterRotation();
}

function normalizeRot(){
  if (ROT_DEG <= -360 || ROT_DEG >= 360){
    const stage = el(".stage");
    const k = Math.round(ROT_DEG / 360);
    const norm = ROT_DEG - k * 360;
    stage.style.transform = `rotate(${norm}deg)`;
    ROT_DEG = norm;
  }
}

/* ----- Rotation driven by displayed side, ignoring corner landings ----- */
function displaySide(){
  let s = Math.round((-ROT_DEG) / 90) % 4;
  if (s < 0) s += 4;
  return s;
}

async function rotateToMatchSide(targetSide){
  let cur = displaySide();
  while (cur !== targetSide){
    await rotateStageCCW90Center();
    cur = displaySide();
  }
}

async function rotateForPathUsingDisplaySide(startIndex, path){
  if (!Array.isArray(path) || path.length === 0) return;
  const seq = [startIndex, ...path.map(x => ((x % 40)+40)%40)];

  for (let i = 1; i < seq.length; i++){
    const target = seq[i];
    if (isCorner(target)) continue;            // never rotate on corner landings
    const tSide = sideForIndex(target);
    if (tSide !== displaySide()){
      await rotateToMatchSide(tSide);
    }
  }
}

/* -------------------- HUD / Outcome -------------------- */

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

/* -------------------- Loading / Dice -------------------- */

function setLoading(on){
  ensureHudOverlay();
  const hudChip = el("#hud-loading");
  if (hudChip) hudChip.style.display = on ? "flex" : "none";

  const rotating = el("#loading");   // keep the rotating one hidden permanently
  if (rotating) rotating.classList.add("hidden");

  const btn = el("#btn-roll");
  btn.disabled = on;
  btn.classList.toggle("disabled", on);
}

function setPawnVisible(show){
  const pawn = el("#pawn");
  if (!pawn) return;
  pawn.style.opacity = show ? "1" : "0";
}

/* ---- Dice (7 anchor pips) ---- */

function initDice(){
  const dice = [el("#die1"), el("#die2")].filter(Boolean);
  dice.forEach(d => {
    d.innerHTML = "";
    const anchors = [
      {left:"14px", top:"14px"},
      {right:"14px", top:"14px"},
      {left:"14px", top:"31px"},
      {left:"31px", top:"31px"},
      {right:"14px", top:"31px"},
      {left:"14px", bottom:"14px"},
      {right:"14px", bottom:"14px"}
    ];
    for (let i = 0; i < 7; i++){
      const p = document.createElement("div");
      p.className = "pip";
      p.dataset.pip = String(i+1);
      Object.assign(p.style, {
        position:"absolute",
        width:"10px", height:"10px", borderRadius:"50%", background:"#111",
        opacity:"0", ...anchors[i]
      });
      d.appendChild(p);
    }
  });
}

function diceSetFace(elem, face){
  const showFor = {
    1: [4],
    2: [1,7],
    3: [1,4,7],
    4: [1,2,6,7],
    5: [1,2,4,6,7],
    6: [1,2,3,5,6,7]
  }[face] || [4];
  const pips = elem.querySelectorAll(".pip[data-pip]");
  pips.forEach(p => {
    const id = +p.dataset.pip;
    p.style.opacity = showFor.includes(id) ? "1" : "0";
  });
}

function spinTwoDiceFor(ms, face1, face2){
  return new Promise((resolve) => {
    const overlay = el("#dice-overlay");
    const d1 = el("#die1");
    const d2 = el("#die2");

    updateDiceCounterRotation();
    overlay.classList.remove("hidden");

    const tick = () => 1 + Math.floor(Math.random()*6);
    const id = setInterval(() => {
      diceSetFace(d1, tick());
      diceSetFace(d2, tick());
    }, 90);

    setTimeout(() => {
      clearInterval(id);
      diceSetFace(d1, face1);
      diceSetFace(d2, face2);
      resolve();
    }, ms);
  });
}

/* -------------------- Core flow -------------------- */

async function refresh(){
  const res = await fetch("/state");
  const data = await res.json();
  STATE = data;
  BOARD = data.board;

  ensurePawnOverlay();
  ensureHudOverlay();
  buildBoard();
  updateHud();

  if (!INIT_DONE){
    const side = sideForIndex(STATE.pos);
    snapStageRotationForSide(side);
    INIT_DONE = true;
  } else {
    updateDiceCounterRotation();
  }

  setPawnVisible(true);
  placePawnAtIndex(STATE.pos, true);
  renderOutcome(STATE.last_outcome);
}

function waitPawn(stepMs=260){
  return waitTransition(el("#pawn"), stepMs);
}

async function walkPath(path, stepMs){
  if (!Array.isArray(path) || path.length === 0) return;
  for (let i = 0; i < path.length; i++){
    placePawnAtIndex(path[i], false);
    await waitPawn(stepMs);
  }
}

function findIndexByType(ttype){
  for (let i = 0; i < BOARD.length; i++){
    if (BOARD[i]?.ttype === ttype) return i;
  }
  return -1;
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

  const landedGotoJail = (BOARD[data.pos]?.ttype === "GOTO_JAIL");
  const jailIdx = findIndexByType("JAIL");

  // Prefetch during animations (no UI block)
  setLoading(true);
  fetch("/prefetch", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({pos: data.pos})
  }).catch(()=>{});

  // Dice spin -> brief hold -> pawn walk
  await spinTwoDiceFor(750, data.d1, data.d2);
  await new Promise(r => setTimeout(r, 450));
  await walkPath(data.path, 260);
  el("#dice-overlay").classList.add("hidden");

  // Hide pawn while rotating so it doesn't "float"
  setPawnVisible(false);

  // Rotate based on path traversed (ignores corner landings)
  await rotateForPathUsingDisplaySide(data.pos_prev, data.path);

  // After rotation, snap pawn to the landing tile
  placePawnAtIndex(data.pos, true);

  // Resolve landing on server (this may teleport to Jail)
  const res2 = await fetch("/resolve", {method:"POST"});
  const rdata = await res2.json();

  // If we landed on GOTO_JAIL, visually rotate two more times CCW to the opposite corner,
  // then snap pawn onto the Jail tile before refreshing HUD/state.
  if (landedGotoJail && jailIdx >= 0){
    // Two CCW quarter-turns
    await rotateStageCCW90Center();
    await rotateStageCCW90Center();
    placePawnAtIndex(jailIdx, true);
  }

  setPawnVisible(true);
  setLoading(false);

  if (rdata.pending){
    openPending(rdata.pending);
  } else {
    await refresh();
  }

  btn.disabled = false;
}

/* -------------------- Pending modal -------------------- */

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
  form.onsubmit = (e) => { /* default close */ };
}

/* -------------------- Boot -------------------- */

document.addEventListener("DOMContentLoaded", async () => {
  ensurePawnOverlay();
  ensureHudOverlay();
  initDice();

  el("#btn-new").onclick = async () => {
    ROT_DEG = 0;
    INIT_DONE = false;
    await fetch("/new", {method:"POST"});
    await refresh();
  };
  el("#btn-roll").onclick = doRoll;

  await refresh();

  updateDiceCounterRotation();

  window.addEventListener("resize", () => {
    if (STATE) placePawnAtIndex(STATE.pos, true);
  });
});
