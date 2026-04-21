// OfficeCanvas.jsx — agents as seated workers in an office, wandering to chat

const { useEffect, useRef } = React;

function OfficeCanvas({ agents, selectedId, onSelect, settings }) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const workersRef = useRef(new Map()); // id -> {x,y,home:{x,y},state,target,chatUntil,chatWith,path,pathT,floatPhase}
  const agentsRef = useRef(agents);
  const selectedRef = useRef(selectedId);
  const onSelectRef = useRef(onSelect);
  const settingsRef = useRef(settings);
  const rafRef = useRef(0);
  const sizeRef = useRef({ w: 0, h: 0 });

  agentsRef.current = agents;
  selectedRef.current = selectedId;
  onSelectRef.current = onSelect;
  settingsRef.current = settings;

  // Assign desks in a grid layout based on count
  function layoutDesks(agents, w, h) {
    const cols = Math.max(3, Math.ceil(Math.sqrt(agents.length * 1.4)));
    const rows = Math.ceil(agents.length / cols);
    const padX = 80, padY = 90;
    const gridW = w - padX * 2;
    const gridH = h - padY * 2 - 40;
    const cellW = gridW / cols;
    const cellH = gridH / Math.max(rows, 2);
    return agents.map((a, i) => {
      const r = Math.floor(i / cols), c = i % cols;
      return { id: a.id, x: padX + cellW * c + cellW / 2, y: padY + cellH * r + cellH / 2 };
    });
  }

  useEffect(() => {
    const { w, h } = sizeRef.current;
    if (!w) return;
    const desks = layoutDesks(agents, w, h);
    agents.forEach((a, i) => {
      const desk = desks[i];
      const prev = workersRef.current.get(a.id);
      if (!prev) {
        workersRef.current.set(a.id, {
          x: desk.x, y: desk.y,
          home: { x: desk.x, y: desk.y },
          state: 'seated',
          chatUntil: 0, chatWith: null,
          floatPhase: Math.random() * Math.PI * 2,
          nextEventAt: performance.now() + 2000 + Math.random() * 3000,
        });
      } else {
        prev.home = { x: desk.x, y: desk.y };
      }
    });
    for (const id of workersRef.current.keys()) {
      if (!agents.find(a => a.id === id)) workersRef.current.delete(id);
    }
  }, [agents]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const w = wrap.clientWidth || 600;
      const h = wrap.clientHeight || 500;
      sizeRef.current = { w, h };
      canvas.width = w * dpr; canvas.height = h * dpr;
      canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // relayout desks
      const desks = layoutDesks(agentsRef.current, w, h);
      agentsRef.current.forEach((a, i) => {
        const desk = desks[i];
        const wk = workersRef.current.get(a.id);
        if (wk) {
          wk.home = { x: desk.x, y: desk.y };
          if (wk.state === 'seated') { wk.x = desk.x; wk.y = desk.y; }
        }
      });
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(wrap);

    const STATUS_COLOR = { idle: '#5a6072', thinking: '#7a8cff', working: '#1fd08a', waiting: '#f5b84c', error: '#ff5d6b' };

    function nearestPeer(id) {
      const others = agentsRef.current.filter(a => a.id !== id && a.status !== 'idle');
      if (!others.length) return null;
      return others[Math.floor(Math.random() * others.length)].id;
    }

    function stepWorker(wk, a, now, dt) {
      const settings = settingsRef.current;
      if (!settings.movement) {
        wk.state = 'seated';
        wk.x += (wk.home.x - wk.x) * 0.15;
        wk.y += (wk.home.y - wk.y) * 0.15;
        return;
      }

      if (wk.state === 'seated') {
        // bob slightly at desk
        wk.floatPhase += dt * 2.4;
        wk.x = wk.home.x;
        wk.y = wk.home.y + Math.sin(wk.floatPhase) * 0.6;
        if (now > wk.nextEventAt && a.status !== 'idle') {
          // decide to go chat
          if (Math.random() < settings.chatiness) {
            const peerId = nearestPeer(a.id);
            if (peerId != null) {
              const peer = workersRef.current.get(peerId);
              if (peer) {
                wk.state = 'walking';
                wk.chatWith = peerId;
                wk.target = { x: peer.home.x, y: peer.home.y - 34 };
              }
            }
          }
          wk.nextEventAt = now + 2500 + Math.random() * 4000;
        }
      } else if (wk.state === 'walking') {
        const t = wk.target;
        if (!t) { wk.state = 'seated'; return; }
        const dx = t.x - wk.x, dy = t.y - wk.y;
        const d = Math.hypot(dx, dy);
        const speed = 90 * settings.speed; // px/sec
        if (d < 3) {
          wk.state = 'chatting';
          wk.chatUntil = now + 1800 + Math.random() * 2200;
        } else {
          wk.x += (dx / d) * speed * dt;
          wk.y += (dy / d) * speed * dt;
        }
      } else if (wk.state === 'chatting') {
        // gentle sway
        wk.floatPhase += dt * 3.5;
        wk.x += Math.sin(wk.floatPhase) * 0.2;
        if (now > wk.chatUntil) {
          wk.state = 'returning';
          wk.target = { x: wk.home.x, y: wk.home.y };
        }
      } else if (wk.state === 'returning') {
        const t = wk.target;
        const dx = t.x - wk.x, dy = t.y - wk.y;
        const d = Math.hypot(dx, dy);
        const speed = 90 * settings.speed;
        if (d < 3) {
          wk.state = 'seated';
          wk.chatWith = null;
          wk.x = wk.home.x; wk.y = wk.home.y;
          wk.nextEventAt = now + 3000 + Math.random() * 4000;
        } else {
          wk.x += (dx / d) * speed * dt;
          wk.y += (dy / d) * speed * dt;
        }
      }
    }

    function drawFloor(w, h, time) {
      // warm desaturated office floor
      ctx.fillStyle = '#141820';
      ctx.fillRect(0, 0, w, h);
      // subtle floor planks / grid
      ctx.strokeStyle = 'rgba(255,255,255,0.035)';
      ctx.lineWidth = 1;
      for (let x = 40; x < w; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }
      for (let y = 40; y < h; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }
      // vignette
      const g = ctx.createRadialGradient(w/2, h/2, Math.min(w,h)*0.2, w/2, h/2, Math.max(w,h)*0.7);
      g.addColorStop(0, 'rgba(0,0,0,0)');
      g.addColorStop(1, 'rgba(0,0,0,0.45)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    }

    function drawDesk(cx, cy, color, selected) {
      // desk = rounded rect; chair = small circle behind
      const w = 64, h = 30;
      // chair
      ctx.fillStyle = '#2a3040';
      ctx.beginPath(); ctx.arc(cx, cy + 20, 8, 0, Math.PI*2); ctx.fill();
      // desk top
      ctx.fillStyle = '#232936';
      roundRect(ctx, cx - w/2, cy - h/2, w, h, 4);
      ctx.fill();
      // monitor
      ctx.fillStyle = '#0d1118';
      roundRect(ctx, cx - 16, cy - h/2 - 10, 32, 16, 2);
      ctx.fill();
      // screen glow (status color)
      ctx.fillStyle = color + '55';
      ctx.fillRect(cx - 13, cy - h/2 - 7, 26, 10);
      // selected ring
      if (selected) {
        ctx.strokeStyle = 'rgba(31,208,138,0.55)';
        ctx.lineWidth = 2;
        roundRect(ctx, cx - w/2 - 4, cy - h/2 - 14, w + 8, h + 22, 8);
        ctx.stroke();
      }
    }

    function drawWorker(wk, a, time) {
      const color = STATUS_COLOR[a.status];
      // shadow
      ctx.fillStyle = 'rgba(0,0,0,0.3)';
      ctx.beginPath(); ctx.ellipse(wk.x, wk.y + 18, 10, 3, 0, 0, Math.PI*2); ctx.fill();
      // body (tinted by status)
      const bodyGrad = ctx.createLinearGradient(wk.x, wk.y - 10, wk.x, wk.y + 16);
      bodyGrad.addColorStop(0, color);
      bodyGrad.addColorStop(1, shade(color, -30));
      ctx.fillStyle = bodyGrad;
      roundRect(ctx, wk.x - 7, wk.y - 2, 14, 18, 4);
      ctx.fill();
      // head
      ctx.fillStyle = '#e4c8a0';
      ctx.beginPath(); ctx.arc(wk.x, wk.y - 8, 7, 0, Math.PI*2); ctx.fill();
      // hair cap tinted by id
      const hue = (a.id * 97) % 360;
      ctx.fillStyle = `oklch(55% 0.12 ${hue})`;
      ctx.beginPath(); ctx.arc(wk.x, wk.y - 10, 7, Math.PI, 2*Math.PI); ctx.fill();
      // status indicator ring around head when active
      if (a.status === 'working' || a.status === 'thinking' || a.status === 'waiting') {
        const phase = (time * 0.8) % 1;
        ctx.strokeStyle = color + '66';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(wk.x, wk.y - 8, 10 + phase * 10, 0, Math.PI*2); ctx.stroke();
      }
      // selection halo
      if (a.id === selectedRef.current) {
        ctx.strokeStyle = 'rgba(31,208,138,0.5)';
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(wk.x, wk.y + 4, 18, 0, Math.PI*2); ctx.stroke();
      }
      // name label below
      ctx.fillStyle = 'rgba(228,231,239,0.85)';
      ctx.font = '500 10px Inter Tight, sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      ctx.fillText(a.name, wk.x, wk.y + 22);
      // speech bubble when chatting
      if (wk.state === 'chatting') {
        drawBubble(wk.x + 10, wk.y - 22, a.tool || a.status);
      }
      // thinking dots when thinking & seated
      if (a.status === 'thinking' && wk.state === 'seated') {
        const t = time * 3;
        for (let i = 0; i < 3; i++) {
          const o = 0.4 + 0.6 * Math.max(0, Math.sin(t - i * 0.6));
          ctx.fillStyle = `rgba(122,140,255,${o})`;
          ctx.beginPath(); ctx.arc(wk.x + 10 + i * 5, wk.y - 18, 1.5, 0, Math.PI*2); ctx.fill();
        }
      }
    }

    function drawBubble(x, y, text) {
      ctx.font = '500 10px Inter Tight, sans-serif';
      const pad = 6;
      const tw = Math.min(ctx.measureText(text).width, 120);
      const bw = tw + pad * 2, bh = 18;
      ctx.fillStyle = 'rgba(22,26,36,0.95)';
      ctx.strokeStyle = 'rgba(255,255,255,0.12)';
      roundRect(ctx, x, y - bh, bw, bh, 6);
      ctx.fill(); ctx.stroke();
      // tail
      ctx.fillStyle = 'rgba(22,26,36,0.95)';
      ctx.beginPath();
      ctx.moveTo(x + 8, y);
      ctx.lineTo(x + 4, y + 4);
      ctx.lineTo(x + 14, y);
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = 'rgba(228,231,239,0.9)';
      ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
      // clip text
      const display = text.length > 22 ? text.slice(0, 21) + '…' : text;
      ctx.fillText(display, x + pad, y - bh / 2);
    }

    function drawChatLink(a, b, time) {
      // dashed mint line between chatting pair
      ctx.strokeStyle = 'rgba(31,208,138,0.5)';
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.lineDashOffset = -time * 10;
      ctx.beginPath(); ctx.moveTo(a.x, a.y - 4); ctx.lineTo(b.x, b.y - 4); ctx.stroke();
      ctx.setLineDash([]);
    }

    function drawWalls(w, h) {
      // office perimeter
      ctx.strokeStyle = 'rgba(255,255,255,0.08)';
      ctx.lineWidth = 2;
      roundRect(ctx, 20, 20, w - 40, h - 40, 14);
      ctx.stroke();
      // label
      ctx.fillStyle = 'rgba(136,140,160,0.5)';
      ctx.font = '10px JetBrains Mono, monospace';
      ctx.textAlign = 'left'; ctx.textBaseline = 'top';
      ctx.fillText('AGENTMESH · FLOOR 01', 34, 28);
    }

    let t0 = performance.now();
    const tick = (t) => {
      const dt = Math.min((t - t0) / 1000, 0.05);
      t0 = t;
      const { w, h } = sizeRef.current;
      const agents = agentsRef.current;
      const now = t;
      const time = t / 1000;

      drawFloor(w, h, time);
      drawWalls(w, h);

      // Update + step workers
      agents.forEach(a => {
        const wk = workersRef.current.get(a.id);
        if (wk) stepWorker(wk, a, now, dt);
      });

      // Draw desks
      agents.forEach(a => {
        const wk = workersRef.current.get(a.id);
        if (!wk) return;
        drawDesk(wk.home.x, wk.home.y, STATUS_COLOR[a.status], a.id === selectedRef.current);
      });

      // Draw chat links
      agents.forEach(a => {
        const wk = workersRef.current.get(a.id);
        if (!wk || wk.state !== 'chatting' || wk.chatWith == null) return;
        const other = workersRef.current.get(wk.chatWith);
        if (other) drawChatLink(wk, other, time);
      });

      // Draw workers (sort by y for proper overlap)
      const sorted = [...agents].sort((a,b) => {
        const wa = workersRef.current.get(a.id), wb = workersRef.current.get(b.id);
        return (wa?.y || 0) - (wb?.y || 0);
      });
      sorted.forEach(a => {
        const wk = workersRef.current.get(a.id);
        if (wk) drawWorker(wk, a, time);
      });

      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    const onClick = (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left, y = e.clientY - rect.top;
      let hit = null;
      for (const [id, wk] of workersRef.current) {
        if (Math.hypot(x - wk.x, y - wk.y - 4) < 20) { hit = id; break; }
      }
      onSelectRef.current(hit);
    };
    canvas.addEventListener('click', onClick);

    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
      canvas.removeEventListener('click', onClick);
    };
  }, []);

  return (
    <div ref={wrapRef} style={{ position: 'absolute', inset: 0, background: '#0e1218' }}>
      <canvas ref={canvasRef} style={{ display: 'block', cursor: 'pointer' }} />
    </div>
  );
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
function shade(hex, delta) {
  // simple darker/lighter on hex
  const c = hex.replace('#','');
  const num = parseInt(c, 16);
  let r = (num >> 16) + delta;
  let g = ((num >> 8) & 0xff) + delta;
  let b = (num & 0xff) + delta;
  r = Math.max(0, Math.min(255, r));
  g = Math.max(0, Math.min(255, g));
  b = Math.max(0, Math.min(255, b));
  return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
}

Object.assign(window, { OfficeCanvas });
