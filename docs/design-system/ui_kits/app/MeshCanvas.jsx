// MeshCanvas.jsx — force-directed agent mesh

const { useEffect, useRef } = React;

function MeshCanvas({ agents, selectedId, onSelect }) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const nodesRef = useRef(new Map());
  const agentsRef = useRef(agents);
  const selectedRef = useRef(selectedId);
  const onSelectRef = useRef(onSelect);
  const rafRef = useRef(0);
  const sizeRef = useRef({ w: 0, h: 0 });

  // keep latest props in refs
  agentsRef.current = agents;
  selectedRef.current = selectedId;
  onSelectRef.current = onSelect;

  // maintain node positions whenever agents change
  useEffect(() => {
    const { w, h } = sizeRef.current;
    agents.forEach((a, i) => {
      if (!nodesRef.current.has(a.id)) {
        const angle = (i / Math.max(agents.length, 1)) * Math.PI * 2;
        const r = Math.min(w || 600, h || 500) * 0.25;
        nodesRef.current.set(a.id, {
          x: (w || 600) / 2 + Math.cos(angle) * r,
          y: (h || 500) / 2 + Math.sin(angle) * r,
          vx: 0, vy: 0,
        });
      }
    });
    for (const id of nodesRef.current.keys()) {
      if (!agents.find(a => a.id === id)) nodesRef.current.delete(id);
    }
  }, [agents]);

  // mount-only: setup canvas, resize observer, rAF loop, click handler
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
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(wrap);

    let t0 = performance.now();
    const tick = (t) => {
      const dt = Math.min((t - t0) / 1000, 0.05);
      t0 = t;
      const { w, h } = sizeRef.current;
      const agents = agentsRef.current;
      const selectedId = selectedRef.current;

      // physics
      const nodes = [...nodesRef.current.entries()];
      for (const [, n] of nodes) {
        n.vx += (w / 2 - n.x) * 0.6 * dt;
        n.vy += (h / 2 - n.y) * 0.6 * dt;
      }
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i][1], b = nodes[j][1];
          const dx = b.x - a.x, dy = b.y - a.y;
          const d2 = Math.max(dx*dx + dy*dy, 400);
          const f = 9000 / d2;
          const len = Math.sqrt(d2);
          const nx = dx / len, ny = dy / len;
          a.vx -= nx * f * dt; a.vy -= ny * f * dt;
          b.vx += nx * f * dt; b.vy += ny * f * dt;
        }
      }
      for (const [, n] of nodes) {
        n.vx *= 0.88; n.vy *= 0.88;
        n.x += n.vx; n.y += n.vy;
        n.x = Math.max(60, Math.min(w - 60, n.x));
        n.y = Math.max(60, Math.min(h - 60, n.y));
      }

      // draw
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = 'rgba(255,255,255,0.035)';
      for (let x = 0; x < w; x += 24) {
        for (let y = 0; y < h; y += 24) {
          ctx.fillRect(x, y, 1.2, 1.2);
        }
      }
      const time = t / 1000;
      ctx.lineWidth = 1;
      agents.forEach(a => {
        if (a.parentId == null) return;
        const p = nodesRef.current.get(a.parentId);
        const c = nodesRef.current.get(a.id);
        if (!p || !c) return;
        ctx.strokeStyle = 'rgba(31,208,138,0.35)';
        ctx.setLineDash([4, 4]);
        ctx.lineDashOffset = -time * 12;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y); ctx.lineTo(c.x, c.y); ctx.stroke();
      });
      ctx.setLineDash([]);

      agents.forEach(a => {
        const n = nodesRef.current.get(a.id); if (!n) return;
        const r = 22;
        const ring = { idle: '#3a3f4e', thinking: '#7a8cff', working: '#1fd08a', waiting: '#f5b84c', error: '#ff5d6b' }[a.status];
        if (a.status === 'working' || a.status === 'thinking' || a.status === 'waiting') {
          const phase = (time * 0.8) % 1;
          ctx.strokeStyle = ring + '66';
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.arc(n.x, n.y, r + phase * 18, 0, Math.PI * 2); ctx.stroke();
          ctx.globalAlpha = 1 - phase;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
        if (a.id === selectedId) {
          ctx.strokeStyle = 'rgba(31,208,138,0.4)';
          ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(n.x, n.y, r + 4, 0, Math.PI * 2); ctx.stroke();
        }
        const grad = ctx.createLinearGradient(n.x - r, n.y - r, n.x + r, n.y + r);
        const h1 = (a.id * 97) % 360, h2 = (h1 + 40) % 360;
        grad.addColorStop(0, `oklch(70% 0.15 ${h1})`);
        grad.addColorStop(1, `oklch(45% 0.14 ${h2})`);
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2); ctx.fill();
        ctx.lineWidth = 2; ctx.strokeStyle = ring;
        ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2); ctx.stroke();
        ctx.fillStyle = 'rgba(0,0,0,0.75)';
        ctx.font = '600 14px JetBrains Mono, monospace';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(String(a.id).padStart(2, '0'), n.x, n.y);
        ctx.fillStyle = 'rgba(228,231,239,0.8)';
        ctx.font = '500 11px Inter Tight, sans-serif';
        ctx.fillText(a.name, n.x, n.y + r + 14);
        ctx.fillStyle = 'rgba(136,140,160,0.8)';
        ctx.font = '10px JetBrains Mono, monospace';
        const statusLabel = a.status === 'working' ? (a.tool || 'working') : a.status;
        ctx.fillText(statusLabel, n.x, n.y + r + 28);
      });

      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    const onClick = (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left, y = e.clientY - rect.top;
      let hit = null;
      for (const [id, n] of nodesRef.current) {
        if ((x - n.x) ** 2 + (y - n.y) ** 2 < 26 ** 2) { hit = id; break; }
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
    <div ref={wrapRef} style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 40%, #0f1a16 0%, #0a0d14 70%)' }}>
      <canvas ref={canvasRef} style={{ display: 'block', cursor: 'pointer' }} />
    </div>
  );
}

Object.assign(window, { MeshCanvas });
