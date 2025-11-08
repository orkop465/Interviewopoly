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

function idx_to_rc(i){
  i = ((i % 40) + 40) % 40;
  if (i <= 9) return [10, 10 - i];         // bottom
  if (i <= 19) return [10 - (i - 10), 0];  // left
  if (i <= 29) return [0, i - 20];         // top
  return [i - 30, 10];                     // right
}
function sideForIndex(i){
  i = ((i % 40) + 40) % 40;
  if (i <= 9) return 0;
  if (i <= 19) return 1;
  if (i <= 29) return 2;
  return 3;
}
function isCorner(i){ return i === 0 || i === 10 || i === 20 || i === 30; }

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

// Snap instantly to keep the current side at the bottom
function snapStageRotationForSide(side){
  ROT_DEG = (-90 * side); // no modulo here; keep absolute to avoid normalization quirks
  const stage = el(".stage");
  stage.style.transformOrigin = "50% 50%";
  stage.style.transform = `rotate(${ROT_DEG}deg)`;
  normalizeRot();          // normalize after applying
  updateDiceCounterRotation();
}

// Animate exactly -90deg (counter-clockwise) from the current angle.
// Do NOT modulo inside the animation to avoid the browser taking the long path.
async function rotateStageCCW90Center(){
  const stage = el(".stage");
  stage.style.transformOrigin = "50% 50%";
  const from = ROT_DEG;
  const to = ROT_DEG - 90;           // strictly CCW by 90
  const anim = stage.animate(
    [{ transform: `rotate(${from}deg)` }, { transform: `rotate(${to}deg)` }],
    { duration: 600, easing: "cubic-bezier(.22,.61,.36,1)", fill: "forwards" }
  );
  await anim.finished.catch(()=>{});
  ROT_DEG = to;
  normalizeRot();                    // fold full turns back to canonical range without animation
  updateDiceCounterRotation();
}

// Fold multiples of 360 so we stay near 0, -90, -180, -270 after any animation
function normalizeRot(){
  if (ROT_DEG <= -360 || ROT_DEG >= 360){
    const stage = el(".stage");
    // compute normalized angle equivalent to ROT_DEG
    const k = Math.round(ROT_DEG / 360);
    const norm = ROT_DEG - k * 360;
    // jump instantly to normalized equivalent to avoid future long-path animations
    stage.style.transform = `rotate(${norm}deg)`;
    ROT_DEG = norm;
  }
}

// Rotate only if you actually passed a corner; never when landing on a corner
async function rotateIfCrossedCorner(oldIndex, newIndex){
  if (isCorner(newIndex)) return;
  const oldSide = sideForIndex(oldIndex);
  const newSide = sideForIndex(newIndex);
  const advancedOneSide = (oldSide + 1) % 4 === newSide;
  if (advancedOneSide){
    await rotateStageCCW90Center();
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
  const overlay = el("#loading");
  overlay.classList.toggle("hidden", !on);
  const btn = el("#btn-roll");
  btn.disabled = on;
  btn.classList.toggle("disabled", on);
}

function setPawnVisible(show){
  const pawn = el("#pawn");
  if (!pawn) return;
  pawn.style.opacity = show ? "1" : "0";
}

/* ---- Dice (already fixed to 7 anchor pips) ---- */

function initDice(){
  const dice = [el("#die1"), el("#die2")].filter(Boolean);
  dice.forEach(d => {
    d.innerHTML = "";
    const anchors = [
      {left:"14px", top:"14px"},      // 1 TL
      {right:"14px", top:"14px"},     // 2 TR
      {left:"14px", top:"31px"},      // 3 ML
      {left:"31px", top:"31px"},      // 4 MM
      {right:"14px", top:"31px"},     // 5 MR
      {left:"14px", bottom:"14px"},   // 6 BL
      {right:"14px", bottom:"14px"}   // 7 BR
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
  buildBoard();
  updateHud();

  const side = sideForIndex(STATE.pos);
  snapStageRotationForSide(side);   // updates counter-rotation too

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

  // Hide pawn while the board rotates so it doesn't "float"
  setPawnVisible(false);
  await rotateIfCrossedCorner(data.pos_prev, data.pos);

  // After rotation, snap pawn precisely to the landing tile and show it again
  placePawnAtIndex(data.pos, true);
  setPawnVisible(true);

  // Then resolve landing
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
  initDice();

  el("#btn-new").onclick = async () => { await fetch("/new", {method:"POST"}); await refresh(); };
  el("#btn-roll").onclick = doRoll;
  await refresh();

  updateDiceCounterRotation();

  window.addEventListener("resize", () => {
    if (STATE) placePawnAtIndex(STATE.pos, true);
  });
});
