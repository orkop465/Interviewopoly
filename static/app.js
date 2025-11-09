// static/app.js
const GROUP_COLORS = {
  BROWN:"#8B4513", LIGHT_BLUE:"#ADD8E6", PINK:"#FF69B4", ORANGE:"#FFA500",
  RED:"#D32F2F", YELLOW:"#F7D154", GREEN:"#2E7D32", DARK_BLUE:"#0D47A1",
  RR:"#6B7280", UTIL:null // RR bar readable
};
const BOARD_BLUE = "#CFEFE9";
const el = (sel) => document.querySelector(sel);

let BOARD = [];
let STATE = null;
let ROT_DEG = 0;
let INIT_DONE = false;

/* track last dismissed outcome so it doesn't bounce back after refresh */
let OUTCOME_DISMISSED_SIG = null;

/* fast lookup for ownership and houses */
let OWNED_SET = new Set();
let HOUSES_MAP = Object.create(null);

/* ---------- Board helpers ---------- */
function idx_to_rc(i){
  i = ((i % 40) + 40) % 40;
  if (i <= 9) return [10, 10 - i];
  if (i <= 19) return [10 - (i - 10), 0];
  if (i <= 29) return [0, i - 20];
  return [i - 30, 10];
}
function sideForIndex(i){ i=((i%40)+40)%40; if(i<=9)return 0; if(i<=19)return 1; if(i<=29)return 2; return 3; }
const CORNERS = new Set([0,10,20,30]);
function isCorner(i){ return CORNERS.has(((i%40)+40)%40); }
function isRR(t){ return t.ttype==="COMPANY" && t.payload?.group==="RR"; }
function isUTIL(t){ return t.ttype==="COMPANY" && t.payload?.group==="UTIL"; }
function isProp(t){ return t.ttype==="COMPANY" && !isRR(t) && !isUTIL(t); }
function tileFillStripe(t){
  if (t.ttype==="CHANCE"||t.ttype==="COMMUNITY") return [BOARD_BLUE,null,true];
  if (isProp(t)) return ["#FFFFFF", GROUP_COLORS[t.payload.group], false];
  if (isRR(t)) return ["#FFFFFF", GROUP_COLORS["RR"], false];
  if (isUTIL(t)) return ["#FFFFFF",null,false];
  return ["#FFFFFF",null,false];
}
function emojiFor(t){
  if (t.ttype==="CHANCE") return "❓";
  if (t.ttype==="COMMUNITY") return "🎁";
  if (t.ttype==="TAX") return "💸";
  if (t.ttype==="START") return "▶";
  if (t.ttype==="JAIL") return "⛓";
  if (t.ttype==="FREE_PARKING") return "🅿";
  if (t.ttype==="GOTO_JAIL") return "🚓";
  if (isRR(t)) return "🚂";
  if (isUTIL(t)) return "⚡";
  if (isProp(t)) return "🏠";
  return "";
}

/* ---------- Pawn overlay ---------- */
function ensurePawnOverlay(){
  const wrap = el("#board-wrap"); if (!wrap) return; wrap.style.position="relative";
  let overlay = el("#pawn-overlay");
  if (!overlay){
    overlay = document.createElement("div");
    overlay.id="pawn-overlay";
    Object.assign(overlay.style,{position:"absolute", inset:"0", pointerEvents:"none"});
    wrap.appendChild(overlay);
  }
  let pawn = el("#pawn");
  if (!pawn){
    pawn = document.createElement("div");
    pawn.id="pawn"; pawn.className="pawn";
  }
  if (pawn.parentElement !== overlay) overlay.appendChild(pawn);
}

/* ---------- Loader dialog ---------- */
let LOADING_CSS_INJECTED = false;
function ensureHudOverlay(){
  let dlg = document.querySelector("#loading-dialog");
  if (!dlg){
    dlg = document.createElement("dialog");
    dlg.id = "loading-dialog";
    dlg.setAttribute("aria-live","polite");
    dlg.setAttribute("aria-modal","true");
    Object.assign(dlg.style,{border:"none",padding:"0",background:"transparent",inset:"0",width:"auto",height:"auto"});

    const card = document.createElement("div");
    card.id="loading-card";
    Object.assign(card.style,{
      position:"fixed", left:"50%", top:"50%", transform:"translate(-50%,-58%)",
      display:"flex", flexDirection:"column", alignItems:"center", gap:"14px",
      background:"#FFFFFF", borderRadius:"16px", padding:"22px 24px",
      boxShadow:"0 18px 60px rgba(0,0,0,.25), inset 0 0 0 1px rgba(0,0,0,.06)"
    });

    const spin = document.createElement("div");
    spin.id="big-spinner";
    Object.assign(spin.style,{
      width:"44px", height:"44px", borderRadius:"50%",
      border:"6px solid rgba(0,0,0,.12)", borderTopColor:"#111",
      animation:"spin 850ms linear infinite"
    });

    const title = document.createElement("div");
    title.id="loading-title";
    Object.assign(title.style,{fontWeight:"800", fontSize:"18px", color:"#111", letterSpacing:"0.2px"});

    const sub = document.createElement("div");
    sub.id="loading-sub";
    Object.assign(sub.style,{fontSize:"13px", color:"rgba(0,0,0,.68)"});

    card.appendChild(spin); card.appendChild(title); card.appendChild(sub);
    dlg.appendChild(card);
    document.body.appendChild(dlg);

    if (!LOADING_CSS_INJECTED){
      const style = document.createElement("style");
      style.textContent = `
        @keyframes spin { to { transform: rotate(360deg); } }
        #loading-dialog::backdrop { background: rgba(0,0,0,.38); backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px); }
        #p-body ul { margin: 6px 0 0 18px; }
        #p-body li { margin: 2px 0; }
        #p-body details { margin-top: 6px; }
        .examples-block { margin-top: 8px; }
        .examples-block pre { margin: 4px 0; padding: 8px 10px; background: #f6f7f9; border-radius: 8px; overflow:auto; }
        .subtitle { opacity:.8; font-size: 13px; margin-top: 2px; }
        .titleline em { font-style: italic; opacity: .85; }
      `;
      document.head.appendChild(style);
      LOADING_CSS_INJECTED = true;
    }
  }
}

function showOverlay(titleText, subText){
  ensureHudOverlay();
  const dlg = el("#loading-dialog");
  el("#loading-title").textContent = titleText || "Working…";
  el("#loading-sub").textContent = subText || "This will only take a moment.";
  if (dlg && !dlg.open){ try { dlg.showModal(); } catch {} }
  const btn = el("#btn-roll"); if (btn){ btn.disabled = true; btn.classList.add("disabled"); }
}
function hideOverlay(){
  const dlg = el("#loading-dialog"); if (dlg && dlg.open){ try { dlg.close(); } catch {} }
  const btn = el("#btn-roll"); if (btn){ btn.disabled = false; btn.classList.remove("disabled"); }
}

/* ---------- Build board ---------- */
function clearBoardKeep(board){
  const keep = new Set([".center-logo", "#dice-overlay", "#loading"]);
  [...board.children].forEach(ch => { if (![...keep].some(s => ch.matches(s))) ch.remove(); });
}
function addOwnedAndDevIndicators(inner, tile){
  const name = tile.name;
  const isOwned = OWNED_SET.has(name);

  if (!isOwned && !isProp(tile)) return; // only mark RR/UTIL when owned; for color props we may still show houses if any

  // Owned chip for any owned company tile
  if (tile.ttype === "COMPANY" && isOwned){
    const chip = document.createElement("div");
    chip.className = "own-chip";
    chip.title = "Owned";
    inner.appendChild(chip);
  }

  // Development marks for color properties
  if (isProp(tile)){
    const count = HOUSES_MAP[name] || 0;
    if (count > 0){
      const wrap = document.createElement("div");
      wrap.className = "dev-marks";
      if (count >= 5){
        const hotel = document.createElement("div");
        hotel.className = "hotel";
        hotel.title = "Hotel";
        hotel.textContent = "H";
        wrap.appendChild(hotel);
      } else {
        for (let i=0; i<count; i++){
          const pip = document.createElement("div");
          pip.className = "house";
          pip.title = "House";
          wrap.appendChild(pip);
        }
      }
      inner.appendChild(wrap);
    }
  }
}
function buildBoard(){
  const board = el("#board");
  clearBoardKeep(board);

  BOARD.forEach((t,i) => {
    const [r,c] = idx_to_rc(i);
    const [fill,stripe,ghost] = tileFillStripe(t);
    const rot = r===10?"rot-0": c===0?"rot-90": r===0?"rot-180":"rot-270";

    const cell = document.createElement("div");
    cell.className="cell"; cell.id="cell-"+i; cell.style.gridRow=(r+1); cell.style.gridColumn=(c+1);

    const inner = document.createElement("div");
    inner.className = "tile-inner " + rot;
    inner.style.setProperty("--tile-bg", fill);
    if (stripe) inner.style.setProperty("--stripe", stripe);

    const stripeDiv = document.createElement("div"); stripeDiv.className="stripe"+(ghost?" ghost":"");
    inner.appendChild(stripeDiv);

    const title = document.createElement("div"); title.className="title"; title.textContent = t.name; inner.appendChild(title);

    const emw = document.createElement("div"); emw.className="emoji-wrap";
    const em = document.createElement("div"); em.className="emoji"; em.textContent = emojiFor(t);
    emw.appendChild(em); inner.appendChild(emw);

    if (isProp(t)){
      const badge = document.createElement("div"); badge.className="qbadge";
      const qk = (t.payload?.qkind || "").toUpperCase();
      badge.textContent = qk==="LC"?"LC": qk==="SD"?"SD": qk==="BH"?"BH":"";
      inner.appendChild(badge);
    }

    // NEW: ownership and dev markers
    addOwnedAndDevIndicators(inner, t);

    cell.appendChild(inner); board.appendChild(cell);
  });
}

/* ---------- Pawn placement ---------- */
function centerOf(elm){ const r = elm.getBoundingClientRect(); return [r.left + r.width/2 + window.scrollX, r.top + r.height/2 + window.scrollY]; }
function placePawnAtIndex(idx, instant=false){
  ensurePawnOverlay();
  const pawn = el("#pawn"), cell = el("#cell-"+idx), overlay = el("#pawn-overlay");
  if (!pawn || !cell || !overlay) return;
  const [cx,cy] = centerOf(cell); const or = overlay.getBoundingClientRect(); const ox = or.left + window.scrollX; const oy = or.top + window.scrollY;
  if (instant) pawn.style.transition = "none";
  pawn.style.transform = `translate(${cx-ox}px, ${cy-oy}px)`;
  if (instant){ void pawn.offsetWidth; pawn.style.transition = "transform 260ms ease"; }
}
function waitTransition(elm, timeoutMs=300){
  return new Promise((resolve) => {
    let done=false; const finish=()=>{ if(done)return; done=true; elm.removeEventListener("transitionend", finish); resolve(); };
    elm.addEventListener("transitionend", finish, {once:true}); setTimeout(finish, timeoutMs+120);
  });
}

/* ---------- Rotation helpers ---------- */
function updateDiceCounterRotation(){ const overlay = el("#dice-overlay"); if (!overlay) return; overlay.style.transformOrigin="50% 50%"; overlay.style.transform=`rotate(${-ROT_DEG}deg)`; }
function snapStageRotationForSide(side){ ROT_DEG=(-90*side); const stage=el(".stage"); stage.style.transformOrigin="50% 50%"; stage.style.transform=`rotate(${ROT_DEG}deg)`; normalizeRot(); updateDiceCounterRotation(); }
async function rotateStageCCW90Center(){ const stage=el(".stage"); stage.style.transformOrigin="50% 50%"; const from=ROT_DEG, to=ROT_DEG-90; const anim=stage.animate([{transform:`rotate(${from}deg)`},{transform:`rotate(${to}deg)`}],{duration:600,easing:"cubic-bezier(.22,.61,.36,1)",fill:"forwards"}); await anim.finished.catch(()=>{}); ROT_DEG=to; normalizeRot(); updateDiceCounterRotation(); }
function normalizeRot(){ if (ROT_DEG <= -360 || ROT_DEG >= 360){ const stage=el(".stage"); const k=Math.round(ROT_DEG/360); const norm=ROT_DEG - k*360; stage.style.transform=`rotate(${norm}deg)`; ROT_DEG=norm; } }
function displaySide(){ let s=Math.round((-ROT_DEG)/90)%4; if (s<0) s+=4; return s; }
async function rotateToMatchSide(targetSide){ let cur=displaySide(); while(cur!==targetSide){ await rotateStageCCW90Center(); cur=displaySide(); } }
async function rotateForPathUsingDisplaySide(startIndex, path){
  if (!Array.isArray(path)||path.length===0) return;
  const seq=[startIndex, ...path.map(x=>((x%40)+40)%40)];
  for (let i=1;i<seq.length;i++){ const target=seq[i]; if (isCorner(target)) continue; const tSide=sideForIndex(target); if (tSide!==displaySide()) await rotateToMatchSide(tSide); }
}

/* ---------- Outcome modal (centered) ---------- */
function ensureOutcomeBackdrop(){
  let bd = el("#outcome-backdrop");
  if (!bd){
    bd = document.createElement("div");
    bd.id = "outcome-backdrop";
    bd.className = "hidden";
    const wrap = el("#board-wrap");
    wrap.appendChild(bd);
  }
  return bd;
}
function outcomeSig(o){
  if (!o) return null;
  return [o.kind||"", o.title||"", o.feedback||""].join("|");
}
function setRollEnabled(enabled){
  const btn = el("#btn-roll");
  if (!btn) return;
  btn.disabled = !enabled;
  btn.classList.toggle("disabled", !enabled);
}
function renderOutcome(outc){
  const box = el("#outcome");
  const backdrop = ensureOutcomeBackdrop();

  if (!outc){
    box.classList.add("hidden");
    backdrop.classList.add("hidden");
    setRollEnabled(true);
    return;
  }

  const sig = outcomeSig(outc);
  if (OUTCOME_DISMISSED_SIG && OUTCOME_DISMISSED_SIG === sig){
    box.classList.add("hidden");
    backdrop.classList.add("hidden");
    setRollEnabled(true);
    return;
  }

  box.className = "outcome";
  if (outc.kind) box.classList.add(outc.kind);
  const title = outc.title || "";
  const feedback = outc.feedback || "";
  box.innerHTML = `
    <strong>${title}</strong>
    ${feedback ? `<div class="subtitle">${feedback}</div>` : ""}
    <div class="actions"><button type="button" id="outcome-close">Close</button></div>
  `;

  box.classList.remove("hidden");
  backdrop.classList.remove("hidden");
  setRollEnabled(false);

  const closeBtn = el("#outcome-close");
  if (closeBtn){
    closeBtn.onclick = () => {
      OUTCOME_DISMISSED_SIG = sig;
      box.classList.add("hidden");
      backdrop.classList.add("hidden");
      setRollEnabled(true);
    };
  }
}

/* ---------- HUD ---------- */
function updateHud(){
  el("#m-offers").textContent = STATE.offers;
  el("#m-turns").textContent = STATE.turns;
  el("#m-owned").textContent = STATE.owned.length;
}

/* ---------- Dice ---------- */
function initDice(){
  const dice=[el("#die1"),el("#die2")].filter(Boolean);
  dice.forEach(d=>{
    d.innerHTML="";
    const anchors=[{left:"14px",top:"14px"},{right:"14px",top:"14px"},{left:"14px",top:"31px"},{left:"31px",top:"31px"},{right:"14px",top:"31px"},{left:"14px",bottom:"14px"},{right:"14px",bottom:"14px"}];
    for(let i=0;i<7;i++){
      const p=document.createElement("div");
      p.className="pip"; p.dataset.pip=String(i+1);
      Object.assign(p.style,{position:"absolute",width:"10px",height:"10px",borderRadius:"50%",background:"#111",opacity:"0",...anchors[i]});
      d.appendChild(p);
    }
  });
}
function diceSetFace(elem, face){
  const showFor={1:[4],2:[1,7],3:[1,4,7],4:[1,2,6,7],5:[1,2,4,6,7],6:[1,2,3,5,6,7]}[face]||[4];
  const pips=elem.querySelectorAll(".pip[data-pip]"); pips.forEach(p=>{ const id=+p.dataset.pip; p.style.opacity=showFor.includes(id)?"1":"0"; });
}
function spinTwoDiceFor(ms, face1, face2){
  return new Promise((resolve)=>{
    const overlay=el("#dice-overlay"), d1=el("#die1"), d2=el("#die2");
    overlay.classList.remove("hidden");
    const tick=()=>1+Math.floor(Math.random()*6);
    const id=setInterval(()=>{ diceSetFace(d1,tick()); diceSetFace(d2,tick()); },90);
    setTimeout(()=>{ clearInterval(id); diceSetFace(d1,face1); diceSetFace(d2,face2); resolve(); },ms);
  });
}

/* ---------- Question tile expectation ---------- */
function willTileProduceQuestion(tile){
  if (!tile) return false;
  if (tile.ttype !== "COMPANY") return false;
  const group = tile.payload?.group;
  if (group === "UTIL") return false;
  if (group === "RR") return true; // RR -> LC_MEDIUM
  const qk = (tile.payload?.qkind || "").toUpperCase();
  return qk === "LC" || qk === "SD" || qk === "BH";
}

/* ---------- Core flow ---------- */
async function refresh(){
  const res = await fetch("/state"); const data = await res.json();
  STATE = data; BOARD = data.board;

  // fast lookup caches
  OWNED_SET = new Set((STATE.owned||[]).map(o=>o.name));
  HOUSES_MAP = Object.assign({}, STATE.houses||{});

  ensurePawnOverlay(); ensureHudOverlay(); buildBoard(); updateHud();
  if (!INIT_DONE){ const side=sideForIndex(STATE.pos); snapStageRotationForSide(side); INIT_DONE=true; }
  placePawnAtIndex(STATE.pos, true);

  renderOutcome(STATE.last_outcome);
}
function setPawnVisible(show){ const pawn = el("#pawn"); if (!pawn) return; pawn.style.opacity = show ? "1":"0"; }
function waitPawn(stepMs=260){ return waitTransition(el("#pawn"), stepMs); }
async function walkPath(path, stepMs){ if (!Array.isArray(path)||path.length===0) return; for(let i=0;i<path.length;i++){ placePawnAtIndex(path[i], false); await waitPawn(stepMs); } }
function findIndexByType(ttype){ for (let i=0;i<BOARD.length;i++){ if (BOARD[i]?.ttype===ttype) return i; } return -1; }

async function doRoll(){
  // Block rolling if outcome is open
  const box = el("#outcome");
  if (box && !box.classList.contains("hidden")) return;

  const btn = el("#btn-roll"); btn.disabled = true; btn.classList.add("disabled");

  const res = await fetch("/roll",{method:"POST"}); const data = await res.json();
  if (data.skipped){ await refresh(); btn.disabled=false; btn.classList.remove("disabled"); return; }

  const landedGotoJail = (BOARD[data.pos]?.ttype==="GOTO_JAIL");
  const jailIdx = findIndexByType("JAIL");

  await spinTwoDiceFor(750, data.d1, data.d2);
  await new Promise(r=>setTimeout(r,450));
  await walkPath(data.path, 260);
  el("#dice-overlay").classList.add("hidden");

  setPawnVisible(false);
  await rotateForPathUsingDisplaySide(data.pos_prev, data.path);
  placePawnAtIndex(data.pos, true);
  setPawnVisible(true);

  const landingTile = BOARD[data.pos];
  const expectQuestion = willTileProduceQuestion(landingTile);

  if (expectQuestion){
    showOverlay("Preparing question","This will only take a moment.");
    fetch("/prefetch", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({pos: data.pos})
    }).catch(()=>{});
  }

  const res2 = await fetch("/resolve",{method:"POST"}); const rdata = await res2.json();

  if (landedGotoJail && jailIdx>=0){
    await rotateStageCCW90Center(); await rotateStageCCW90Center();
    placePawnAtIndex(jailIdx, true);
  }

  if (expectQuestion) hideOverlay();

  if (rdata.pending) openPending(rdata.pending);
  else await refresh();

  btn.disabled = false; btn.classList.remove("disabled");
}

/* ---------- Modal rendering (question dialog) ---------- */
function diffFromType(p){
  if (!p || !p.type) return null;
  const t = p.type.toUpperCase();
  if (t==="SYS_DESIGN" || t==="BEHAVIORAL") return (p.difficulty || "").toUpperCase() || null;
  if (t.startsWith("LC_")){
    if (t.endsWith("EASY")) return "EASY";
    if (t.endsWith("MED") || t.endsWith("MEDIUM")) return "MEDIUM";
    if (t.endsWith("HARD")) return "HARD";
  }
  return null;
}
function titleLine(label, diff){
  const d = diff ? ` — <em>${diff}</em>` : "";
  return `<span class="titleline"><strong>${label}</strong>${d}</span>`;
}

function openPending(p){
  const dlg = el("#pending-modal");
  const title = el("#p-title");
  const body = el("#p-body");
  const ta = el("#p-answer");
  const submitBtn = el("#p-submit");

  // Reset state
  ta.value = "";
  submitBtn.disabled = true;

  // Build content
  const diff = diffFromType(p);

  if (p.type === "SYS_DESIGN"){
    title.innerHTML = titleLine("System Design", diff);
    const rub = (p.question.rubric||[]).map(x=>`<li>${x}</li>`).join("");
    body.innerHTML = `
      <div>${p.question.title ? `<div><strong>${p.question.title}</strong></div>`:""}</div>
      <div class="subtitle">${p.question.prompt||""}</div>
      <details><summary>Rubric</summary><ul>${rub}</ul></details>
    `;
  } else if (p.type === "BEHAVIORAL"){
    title.innerHTML = titleLine("Behavioral (STAR)", diff);
    body.innerHTML = `
      <div>${p.question.title ? `<div><strong>${p.question.title}</strong></div>`:""}</div>
      <div class="subtitle">${p.question.prompt||""}</div>
      <div class="subtitle">${p.question.tip||""}</div>
    `;
  } else {
    // LeetCode
    title.innerHTML = titleLine("LeetCode", diff);
    const exs = (p.question.examples||[]);
    let exHtml = "";
    if (exs.length){
      exHtml = `<div class="examples-block"><details open><summary>Examples</summary>${
        exs.map(e=>`<pre>${e}</pre>`).join("")
      }</details></div>`;
    }
    const hints = (p.question.hints||[]);
    const hintHtml = hints.length ? `<details><summary>Hints</summary><ul>${hints.map(h=>`<li>${h}</li>`).join("")}</ul></details>` : "";
    body.innerHTML = `
      <div>${p.question.title ? `<div><strong>${p.question.title}</strong></div>`:""}</div>
      <div class="subtitle">${p.question.question||""}</div>
      ${exHtml}
      ${hintHtml}
    `;
  }

  // enforce non-empty answer before enabling submit
  function validateAnswer(){
    const ok = (ta.value || "").trim().length > 0;
    submitBtn.disabled = !ok;
  }
  ta.addEventListener("input", validateAnswer, { once:false });
  validateAnswer();

  // show as modal and prevent ESC close
  try { dlg.showModal(); } catch {}
  dlg.addEventListener("cancel", (e) => { e.preventDefault(); });

  // submit handler
  submitBtn.onclick = async (e) => {
    e.preventDefault();
    const text = (ta.value || "").trim();
    if (!text) return;

    showOverlay("Grading answer","Scoring your response.");
    const res = await fetch("/submit_answer", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text})
    });
    const data = await res.json();

    dlg.close();
    await refresh();
    renderOutcome(data.last_outcome);
    hideOverlay();
  };
}

/* ---------- Boot ---------- */
document.addEventListener("DOMContentLoaded", async () => {
  // ensure outcome backdrop exists
  (function ensureOutcomeBackdropAtBoot(){
    let bd = el("#outcome-backdrop");
    if (!bd){
      bd = document.createElement("div");
      bd.id = "outcome-backdrop";
      bd.className = "hidden";
      const wrap = el("#board-wrap");
      wrap.appendChild(bd);
    }
  })();

  ensurePawnOverlay(); ensureHudOverlay(); initDice();
  el("#btn-new").onclick = async () => { ROT_DEG=0; INIT_DONE=false; OUTCOME_DISMISSED_SIG=null; await fetch("/new",{method:"POST"}); await refresh(); };
  el("#btn-roll").onclick = doRoll;
  await refresh();
  window.addEventListener("resize", () => { if (STATE) placePawnAtIndex(STATE.pos, true); });
});
