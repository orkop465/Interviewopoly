import json
import streamlit.components.v1 as components

TTYPE_COLORS = {
    "START": "#2e7d32",
    "LC_EASY": "#64b5f6",
    "LC_MED": "#1e88e5",
    "LC_HARD": "#0d47a1",
    "SYS_DESIGN": "#ffb74d",
    "BEHAVIORAL": "#ba68c8",
    "CHANCE": "#90a4ae",
    "COMMUNITY": "#80cbc4",
    "COMPANY": "#ef5350",
    "JAIL": "#ff7043",
    "FREE_PARKING": "#26a69a",
    "GOTO_JAIL": "#8e24aa",
}

def render_visual_board(
    board,
    pos,
    prev_pos,
    path,
    owned_names=None,
    show_dice=False,
    dice_face=1,
    dice_spin=False,
    animate=True,
    teleport=False,
):
    """
    - pos: current pawn index
    - prev_pos: previous index
    - path: list of indices to animate through (if animate=True)
    - show_dice: render dice overlay
    - dice_face: final rolled face (1-6)
    - dice_spin: if True, JS cycles faces until rerun
    - animate: if True, animate pawn along path starting from prev_pos
    - teleport: if True, show a global flash (Go To Jail arrival)
    """
    owned_names = set(owned_names or [])

    names = [t.name for t in board]
    colors = [TTYPE_COLORS.get(t.ttype, "#3a4150") for t in board]

    # badges
    badges = []
    for t in board:
        b = ""
        if t.ttype == "COMPANY":
            b = "💼"
            if t.name in owned_names:
                b = "✅"
        elif t.ttype.startswith("LC_"):
            b = "🧠"
        elif t.ttype == "SYS_DESIGN":
            b = "🏗️"
        elif t.ttype == "BEHAVIORAL":
            b = "🗣️"
        elif t.ttype == "CHANCE":
            b = "🎲"
        elif t.ttype == "COMMUNITY":
            b = "🤝"
        elif t.ttype == "START":
            b = "🏁"
        elif t.ttype == "JAIL":
            b = "🚔"
        elif t.ttype == "FREE_PARKING":
            b = "🅿️"
        elif t.ttype == "GOTO_JAIL":
            b = "⚠️"
        badges.append(b)

    # perimeter mapping for 6x6 grid, 20 tiles
    areas = {
        0: "a0", 1: "a1", 2: "a2", 3: "a3", 4: "a4", 5: "a5",
        6: "a6", 7: "a7", 8: "a8", 9: "a9", 10: "a10", 11: "a11",
        12: "a12", 13: "a13", 14: "a14", 15: "a15", 16: "a16",
        17: "a17", 18: "a18", 19: "a19",
    }

    cells_html = ""
    for i in range(len(board)):
        cells_html += (
            f'<div class="cell" id="cell-{i}" title="{names[i]}">'
            f'<div class="type-bar" style="background:{colors[i]}"></div>'
            f'<div class="label"><span class="badge">{badges[i]}</span>'
            f'<span>{names[i]}</span></div>'
            f'</div>'
        )

    areas_css = "".join(
        f"#cell-{i} {{ grid-area: {areas[i]}; }}\n" for i in range(len(board))
    )

    teleport_html = "<div class='teleport-flash'></div>" if teleport else ""

    overlay_html = ""
    if show_dice:
        pips = "".join("<div class='pip'></div>" for _ in range(6))
        overlay_html = f"""
        <div class="dice-overlay">
          <div class="dice face-{int(dice_face or 1)}" id="die">
            {pips}
          </div>
        </div>
        """

    path_json = json.dumps(path or [])
    pos_json = json.dumps(int(pos))
    prev_json = json.dumps(int(prev_pos))
    animate_flag = "true" if animate and path else "false"
    spin_flag = "true" if dice_spin else "false"
    final_face_js = int(dice_face or 1)

    html = f"""
    <style>
      .board-wrap {{
        width: 600px;
        margin: 6px auto 10px;
      }}
      .board {{
        position: relative;
        width: 600px;
        height: 600px;
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        grid-template-rows: repeat(6, 1fr);
        grid-template-areas:
          "a0  a1  a2  a3  a4  a5"
          "a19 .   .   .   .   a6"
          "a18 .   .   .   .   a7"
          "a17 .   .   .   .   a8"
          "a16 .   .   .   .   a9"
          "a15 a14 a13 a12 a11 a10";
        gap: 6px;
        padding: 10px;
        background: #0e1217;
        border-radius: 18px;
        box-shadow: 0 16px 40px rgba(0,0,0,0.45);
      }}
      .center-logo {{
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%) rotate(-28deg);
        font: 900 40px/1 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        letter-spacing: 4px;
        color: #e6edf3;
        opacity: 0.18;
        user-select: none;
        pointer-events: none;
        text-transform: uppercase;
        text-shadow: 0 2px 10px rgba(0,0,0,0.35);
      }}
      .cell {{
        position: relative;
        background: #171e28;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
      }}
      .type-bar {{
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 8px;
      }}
      .label {{
        position: absolute;
        left: 8px; bottom: 6px; right: 6px;
        font: 600 10px/1.2 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        color: #e6edf3;
        text-shadow: 0 1px 2px rgba(0,0,0,0.35);
        display: flex;
        gap: 4px;
        align-items: center;
        pointer-events: none;
      }}
      .badge {{ font-size: 12px; }}

      .highlight {{
        box-shadow:
          0 0 0 2px rgba(255,255,255,0.18) inset,
          0 0 12px rgba(255,255,255,0.26);
        animation: pulse 800ms ease 1;
      }}
      @keyframes pulse {{
        0%   {{ box-shadow: 0 0 0 0 rgba(255,255,255,0); }}
        40%  {{ box-shadow: 0 0 0 2px rgba(255,255,255,0.22),
                         0 0 14px rgba(255,255,255,0.26); }}
        100% {{ box-shadow: 0 0 0 1px rgba(255,255,255,0.16),
                         0 0 10px rgba(255,255,255,0.2); }}
      }}

      .pawn {{
        position: absolute;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #ffffff, #d6dbe2);
        border: 3px solid #050608;
        box-shadow:
          0 8px 22px rgba(0,0,0,0.55),
          inset 0 0 4px rgba(0,0,0,0.4);
        transform: translate(-50%, -50%);
        transition: transform 260ms ease;
        z-index: 30;
      }}
      .spark {{
        position: absolute;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #fff;
        opacity: 0;
        pointer-events: none;
      }}

      {areas_css}

      .dice-overlay {{
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        background: rgba(0,0,0,0.30);
        z-index: 60;
        backdrop-filter: blur(2px);
      }}
      .dice {{
        width: 72px;
        height: 72px;
        background: #ffffff;
        border-radius: 14px;
        box-shadow:
          0 14px 26px rgba(0,0,0,0.45),
          inset 0 0 0 3px #151515;
        position: relative;
      }}
      .pip {{
        position: absolute;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #111;
      }}

      /* Face layouts (we always render 6 pips, arrangement implies number) */
      .dice.face-1 .pip:nth-child(1) {{ left:31px; top:31px; }}

      .dice.face-2 .pip:nth-child(1) {{ left:18px; top:18px; }}
      .dice.face-2 .pip:nth-child(2) {{ left:44px; top:44px; }}

      .dice.face-3 .pip:nth-child(1) {{ left:18px; top:18px; }}
      .dice.face-3 .pip:nth-child(2) {{ left:31px; top:31px; }}
      .dice.face-3 .pip:nth-child(3) {{ left:44px; top:44px; }}

      .dice.face-4 .pip:nth-child(1) {{ left:18px; top:18px; }}
      .dice.face-4 .pip:nth-child(2) {{ left:44px; top:18px; }}
      .dice.face-4 .pip:nth-child(3) {{ left:18px; top:44px; }}
      .dice.face-4 .pip:nth-child(4) {{ left:44px; top:44px; }}

      .dice.face-5 .pip:nth-child(1) {{ left:18px; top:18px; }}
      .dice.face-5 .pip:nth-child(2) {{ left:44px; top:18px; }}
      .dice.face-5 .pip:nth-child(3) {{ left:31px; top:31px; }}
      .dice.face-5 .pip:nth-child(4) {{ left:18px; top:44px; }}
      .dice.face-5 .pip:nth-child(5) {{ left:44px; top:44px; }}

      .dice.face-6 .pip:nth-child(1) {{ left:18px; top:16px; }}
      .dice.face-6 .pip:nth-child(2) {{ left:44px; top:16px; }}
      .dice.face-6 .pip:nth-child(3) {{ left:18px; top:30px; }}
      .dice.face-6 .pip:nth-child(4) {{ left:44px; top:30px; }}
      .dice.face-6 .pip:nth-child(5) {{ left:18px; top:46px; }}
      .dice.face-6 .pip:nth-child(6) {{ left:44px; top:46px; }}

      .teleport-flash {{
        position: absolute;
        inset: 0;
        border-radius: 18px;
        box-shadow:
          0 0 0 3px rgba(255,255,255,0.9),
          0 0 26px rgba(255,255,255,0.9);
        animation: tflash 420ms ease-out 1;
        pointer-events: none;
      }}
      @keyframes tflash {{
        0%   {{ opacity: 0;   transform: scale(0.94); }}
        40%  {{ opacity: 1;   transform: scale(1.02); }}
        100% {{ opacity: 0;   transform: scale(1.00); }}
      }}
    </style>

    <div class="board-wrap">
      <div id="board" class="board">
        {cells_html}
        <div class="center-logo">INTERVIEWOPOLY</div>
        <div id="pawn" class="pawn"></div>
        {teleport_html}
        {overlay_html}
      </div>
    </div>

    <script>
      const pos = {pos_json};
      const prev = {prev_json};
      const path = {path_json};
      const DO_ANIMATE = {animate_flag};
      const SPIN = {spin_flag};
      const FINAL_FACE = {final_face_js};

      function centerOf(el) {{
        const r = el.getBoundingClientRect();
        const cx = r.left + r.width / 2 + window.scrollX;
        const cy = r.top + r.height / 2 + window.scrollY;
        return [cx, cy];
      }}

      function placePawnAtElement(el, instant=false) {{
        const pawn = document.getElementById('pawn');
        if (!pawn || !el) return;
        const [cx, cy] = centerOf(el);
        const boardRect = document.getElementById('board').getBoundingClientRect();
        const bx = boardRect.left + window.scrollX;
        const by = boardRect.top + window.scrollY;
        if (instant) {{
          pawn.style.transition = 'none';
        }}
        pawn.style.transform = 'translate(' + (cx - bx) + 'px,' + (cy - by) + 'px)';
        if (instant) {{
          void pawn.offsetWidth;
          pawn.style.transition = 'transform 260ms ease';
        }}
      }}

      function placePawnAtIndex(index, instant=false) {{
        const el = document.getElementById('cell-' + index);
        if (!el) return;
        placePawnAtElement(el, instant);
      }}

      function highlightCell(i) {{
        document.querySelectorAll('.cell').forEach(c => c.classList.remove('highlight'));
        const el = document.getElementById('cell-' + i);
        if (el) el.classList.add('highlight');
      }}

      function sparks(el) {{
        for (let k = 0; k < 5; k++) {{
          const s = document.createElement('div');
          s.className = 'spark';
          el.appendChild(s);
          const x = Math.random() * 100;
          const y = Math.random() * 100;
          s.style.left = x + '%';
          s.style.top = y + '%';
          s.animate(
            [
              {{ opacity: 0, transform: 'scale(0.4)' }},
              {{ opacity: 1, transform: 'scale(1.3)' }},
              {{ opacity: 0, transform: 'scale(0.4)' }}
            ],
            {{ duration: 350 + Math.random() * 300 }}
          );
          setTimeout(() => s.remove(), 600);
        }}
      }}

      const hasPath = Array.isArray(path) && path.length > 0;

      if (DO_ANIMATE && hasPath) {{
        // Start on previous tile, then walk path exactly once.
        placePawnAtIndex(prev, true);
        let idx = 0;
        function step() {{
          const targetIndex = path[idx];
          const cell = document.getElementById('cell-' + targetIndex);
          if (!cell) return;
          placePawnAtElement(cell, false);
          highlightCell(targetIndex);
          if (idx === path.length - 1) {{
            sparks(cell);
          }}
          idx++;
          if (idx < path.length) {{
            setTimeout(step, 260);
          }}
        }}
        requestAnimationFrame(step);
      }} else {{
        // No animation: just show at pos.
        placePawnAtIndex(pos, true);
      }}

      // Dice behavior
      const die = document.getElementById('die');
      if (die) {{
        if (SPIN) {{
          setInterval(() => {{
            const f = 1 + Math.floor(Math.random() * 6);
            die.className = 'dice face-' + f;
          }}, 90);
        }} else {{
          die.className = 'dice face-' + FINAL_FACE;
        }}
      }}
    </script>
    """

    components.html(html, height=640, scrolling=False)
