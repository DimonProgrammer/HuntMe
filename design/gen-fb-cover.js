#!/usr/bin/env node
// Apex Talent — Facebook Cover 1640×624
// node landing/gen-fb-cover.js

const fs   = require('fs');
const path = require('path');

// ── Colours ───────────────────────────────────────────────────────────────────
const h8 = (r, g, b, a) =>
  '#' + [r, g, b, Math.round(a * 255)]
    .map(n => n.toString(16).padStart(2, '0').toUpperCase()).join('');

const INK     = '#1A0F2E';
const MAGENTA = '#E33BC5';
const LIME    = '#CCFF00';
const ORANGE  = '#FF8C42';
const WHITE   = '#FFFFFF';

// ── ID ────────────────────────────────────────────────────────────────────────
let _n = 0;
const id = (p = 'n') => `${p}${++_n}`;

// ── Primitive builders ────────────────────────────────────────────────────────
const solid  = hex      => ({ type: 'color',    color: hex });
const grad   = (deg, stops) => ({ type: 'gradient', gradientType: 'linear', rotation: deg, colors: stops });
const radial = (stops)  => ({ type: 'gradient', gradientType: 'radial',  colors: stops });

const rect = (name, x, y, w, h, opts = {}) => ({
  id: id('r'), name, type: 'rectangle', x, y, width: w, height: h,
  ...(opts.r        ? { cornerRadius: opts.r }  : {}),
  ...(opts.fills    ? { fills: opts.fills }     : {}),
  ...(opts.stroke   ? { strokes: [opts.stroke] }: {}),
  ...(opts.effects  ? { effects: opts.effects } : {}),
});

const ellipse = (name, x, y, w, h, opts = {}) => ({
  id: id('e'), name, type: 'ellipse', x, y, width: w, height: h,
  ...(opts.innerRadius !== undefined ? { innerRadius: opts.innerRadius } : {}),
  ...(opts.fills   ? { fills: opts.fills }      : {}),
  ...(opts.stroke  ? { strokes: [opts.stroke] } : {}),
  ...(opts.opacity !== undefined ? { opacity: opts.opacity } : {}),
});

const text = (name, x, y, w, h, content, s = {}) => ({
  id: id('t'), name, type: 'text', x, y, width: w, height: h,
  textGrowth: 'fixed-width',
  content,
  fontFamily:  s.ff  ?? 'Plus Jakarta Sans',
  fontSize:    s.fs  ?? 14,
  fontWeight:  s.fw  ?? 400,
  lineHeight:  s.lh  ?? 1.3,
  ...(s.ls !== undefined ? { letterSpacing: s.ls }    : {}),
  ...(s.ta !== undefined ? { textAlign: s.ta }        : {}),
  fills: [s.fill ?? solid(s.color ?? WHITE)],
});

const shadow = (dy, blur, spread, alpha) => ({
  type: 'shadow', shadowType: 'outer',
  offset: { x: 0, y: dy }, blur, spread,
  color: h8(26, 15, 46, alpha),
});

// ══════════════════════════════════════════════════════════════════════════════
//  FACEBOOK COVER  1640 × 624 px
// ══════════════════════════════════════════════════════════════════════════════
const W = 1640, H = 624;

// ── Canvas dimensions as constants ───────────────────────────────────────────
const PAD   = 80;   // left/right safe padding
const MID_X = 920;  // divider between left and right zones

// ── LAYER STACK (bottom → top) ────────────────────────────────────────────────
const layers = [];

// ─ 1. Background ────────────────────────────────────────────────────────────
layers.push(rect('bg', 0, 0, W, H, { fills: [solid(INK)] }));

// ─ 2. Right-side lime glow (radial gradient circle) ─────────────────────────
layers.push(ellipse('glow-lime', 900, -100, 900, 900, {
  fills: [radial([
    { color: h8(204, 255,   0, 0.08), position: 0   },
    { color: h8(204, 255,   0, 0.00), position: 0.7 },
  ])],
}));

// ─ 3. Right-side magenta glow ────────────────────────────────────────────────
layers.push(ellipse('glow-magenta', 1200, 300, 700, 700, {
  fills: [radial([
    { color: h8(227,  59, 197, 0.06), position: 0   },
    { color: h8(227,  59, 197, 0.00), position: 0.6 },
  ])],
}));

// ─ 4. Top accent bar ─────────────────────────────────────────────────────────
layers.push(rect('bar-top', 0, 0, W, 4, {
  fills: [grad(90, [
    { color: MAGENTA + 'FF', position: 0   },
    { color: LIME    + 'FF', position: 1   },
  ])],
}));

// ─ 5. Bottom accent bar ──────────────────────────────────────────────────────
layers.push(rect('bar-bottom', 0, H - 4, W, 4, {
  fills: [grad(90, [
    { color: LIME    + 'FF', position: 0 },
    { color: MAGENTA + 'FF', position: 1 },
  ])],
}));

// ─ 6. Decorative circles (ring shapes via innerRadius) ────────────────────────
// Large ring, top-right, clipped
layers.push(ellipse('ring-xl', 1140, -180, 560, 560, {
  innerRadius: 0.88,
  fills: [solid(h8(204, 255, 0, 0.08))],
}));
// Medium ring, bottom-right
layers.push(ellipse('ring-md', 1360, 360, 280, 280, {
  innerRadius: 0.82,
  fills: [solid(h8(204, 255, 0, 0.12))],
}));
// Small lime dot, left middle
layers.push(ellipse('dot-lime-1', MID_X - 40, 260, 10, 10, {
  fills: [solid(h8(204, 255, 0, 0.5))],
}));
layers.push(ellipse('dot-lime-2', MID_X + 20, 380, 6, 6, {
  fills: [solid(h8(204, 255, 0, 0.35))],
}));
layers.push(ellipse('dot-magenta', MID_X - 20, 180, 8, 8, {
  fills: [solid(h8(227, 59, 197, 0.5))],
}));
// Tiny scattered dots on right
layers.push(ellipse('dot-r1', 1560, 80,  5, 5, { fills: [solid(h8(204,255,0,0.4))] }));
layers.push(ellipse('dot-r2', 1480, 520, 4, 4, { fills: [solid(h8(227,59,197,0.4))] }));
layers.push(ellipse('dot-r3', 1040, 560, 6, 6, { fills: [solid(h8(204,255,0,0.3))] }));

// ─ 7. Vertical divider line ───────────────────────────────────────────────────
layers.push(rect('divider', MID_X, 60, 1, H - 120, {
  fills: [solid(h8(255, 255, 255, 0.06))],
}));

// ─ 8. LOGO — "APEX TALENT" top-left ──────────────────────────────────────────
layers.push(text('logo', PAD, 32, 260, 26, 'APEX TALENT', {
  ff:'Outfit', fs:20, fw:900, ls:2.4,
  fill: solid(WHITE),
}));
// Logo dot accent
layers.push(ellipse('logo-dot', PAD - 12, 40, 6, 6, {
  fills: [solid(LIME)],
}));

// ─ 9. URL — top-right ─────────────────────────────────────────────────────────
layers.push(text('url', W - PAD - 160, 36, 160, 16, 'apextalent.pro', {
  fs:13, fw:500,
  fill: solid(h8(255, 255, 255, 0.45)),
  ta: 'right',
}));

// ─ 10. LIVE badge ─────────────────────────────────────────────────────────────
const BADGE_Y = 96;
layers.push(rect('badge-bg', PAD, BADGE_Y, 248, 28, {
  r: 100,
  fills: [solid(h8(255, 255, 255, 0.07))],
}));
// Red live dot
layers.push(ellipse('live-dot', PAD + 12, BADGE_Y + 9, 10, 10, {
  fills: [solid('#FF3B30')],
}));
layers.push(text('badge-text', PAD + 28, BADGE_Y + 7, 210, 14, 'LIVE · OPERATOR RECRUITMENT', {
  ff:'Outfit', fs:10, fw:700, ls:1.2,
  fill: solid(h8(255, 255, 255, 0.8)),
}));

// ─ 11. HEADLINE (3 lines) ─────────────────────────────────────────────────────
const HL_X  = PAD;
const HL_W  = MID_X - PAD - 40;
const HL_FS = 80;
const HL_LH = 1.02;
const HL_GAP = 6; // extra gap between lines

// "Stream."  — white
const HL1_Y = 144;
layers.push(text('hl-1', HL_X, HL1_Y, HL_W, HL_FS, 'Stream.', {
  ff:'Outfit', fs:HL_FS, fw:900, lh:HL_LH,
  fill: solid(WHITE),
}));

// "Earn More."  — gradient magenta → orange
const HL2_Y = HL1_Y + Math.round(HL_FS * HL_LH) + HL_GAP;
layers.push(text('hl-2', HL_X, HL2_Y, HL_W, HL_FS, 'Earn More.', {
  ff:'Outfit', fs:HL_FS, fw:900, lh:HL_LH,
  fill: grad(125, [
    { color: MAGENTA + 'FF', position: 0   },
    { color: ORANGE  + 'FF', position: 1   },
  ]),
}));

// "Live."  — white
const HL3_Y = HL2_Y + Math.round(HL_FS * HL_LH) + HL_GAP;
layers.push(text('hl-3', HL_X, HL3_Y, HL_W, HL_FS, 'Live.', {
  ff:'Outfit', fs:HL_FS, fw:900, lh:HL_LH,
  fill: solid(WHITE),
}));

// ─ 12. TAGLINE ────────────────────────────────────────────────────────────────
const TAG_Y = HL3_Y + Math.round(HL_FS * HL_LH) + 20;
layers.push(text('tagline', HL_X, TAG_Y, HL_W, 36, 'International opportunities\nfor live streaming operators', {
  fs:16, fw:400, lh:1.5,
  fill: solid(h8(255, 255, 255, 0.6)),
}));

// ─ 13. Country chips ──────────────────────────────────────────────────────────
const CHIP_Y = TAG_Y + 52;
const chips = [
  { flag: '🇵🇭', label: 'Philippines', w: 148 },
  { flag: '🇳🇬', label: 'Nigeria',     w: 128 },
  { flag: '🇮🇩', label: 'Indonesia',   w: 140 },
];
let chipX = HL_X;
chips.forEach(({ flag, label, w }) => {
  layers.push(rect(`chip-${label}-bg`, chipX, CHIP_Y, w, 32, {
    r: 100,
    fills: [solid(h8(255, 255, 255, 0.08))],
  }));
  layers.push(text(`chip-${label}-t`, chipX + 10, CHIP_Y + 8, w - 20, 16,
    `${flag} ${label}`, {
      fs:13, fw:600,
      fill: solid(h8(255, 255, 255, 0.85)),
    }
  ));
  chipX += w + 10;
});

// ─ 14. CTA Button ────────────────────────────────────────────────────────────
const CTA_Y = H - 80;
layers.push(rect('cta-bg', HL_X, CTA_Y, 192, 48, {
  r: 100,
  fills: [solid(LIME)],
}));
layers.push(text('cta-text', HL_X + 24, CTA_Y + 13, 148, 22, 'Apply Free →', {
  ff:'Outfit', fs:16, fw:800,
  fill: solid(INK),
}));

// ─ 15. RIGHT SIDE — Hero stat ─────────────────────────────────────────────────
const STAT_X  = MID_X + 60;
const STAT_W  = W - STAT_X - PAD;

// Large "$2,400" in LIME
layers.push(text('stat-num', STAT_X, 100, STAT_W, 200, '$2,400', {
  ff:'Outfit', fs:160, fw:900, lh:1.0,
  fill: solid(LIME),
}));
// "/mo" subscript
layers.push(text('stat-sub', STAT_X, 308, 120, 40, '/mo', {
  ff:'Outfit', fs:32, fw:700, lh:1.0,
  fill: solid(h8(204, 255, 0, 0.6)),
}));
// Label
layers.push(text('stat-label', STAT_X, 358, STAT_W, 22, 'avg. monthly earning', {
  ff:'Outfit', fs:16, fw:600, ls:0.4,
  fill: solid(h8(255, 255, 255, 0.5)),
}));
// Thin lime underline below label
layers.push(rect('stat-line', STAT_X, 386, 120, 2, {
  fills: [solid(h8(204, 255, 0, 0.35))],
}));

// Secondary stat block
const STAT2_Y = 430;
layers.push(text('stat2-num', STAT_X, STAT2_Y, STAT_W, 56, '1,200+', {
  ff:'Outfit', fs:48, fw:900, lh:1.0,
  fill: solid(WHITE),
}));
layers.push(text('stat2-label', STAT_X, STAT2_Y + 52, STAT_W, 18, 'active operators worldwide', {
  ff:'Outfit', fs:13, fw:600, ls:0.3,
  fill: solid(h8(255, 255, 255, 0.45)),
}));

// Tertiary stat
layers.push(text('stat3-num', STAT_X + 240, STAT2_Y, 200, 56, '48h', {
  ff:'Outfit', fs:48, fw:900, lh:1.0,
  fill: solid(h8(227, 59, 197, 0.9)),
}));
layers.push(text('stat3-label', STAT_X + 240, STAT2_Y + 52, 200, 18, 'time to first payout', {
  ff:'Outfit', fs:13, fw:600, ls:0.3,
  fill: solid(h8(255, 255, 255, 0.45)),
}));

// ─ 16. Platform logos text ────────────────────────────────────────────────────
layers.push(text('platforms', STAT_X, H - 52, STAT_W, 16,
  'Chaturbate · Stripchat · LiveJasmin · BongaCams', {
    fs:12, fw:500,
    fill: solid(h8(255, 255, 255, 0.25)),
  }
));

// ══════════════════════════════════════════════════════════════════════════════
//  ASSEMBLE DOCUMENT
// ══════════════════════════════════════════════════════════════════════════════
const doc = {
  version: '1',
  children: [{
    id:       'fb-cover',
    name:     'Facebook Cover — Apex Talent (1640×624)',
    type:     'frame',
    x: 0, y: 0,
    width:  W,
    height: H,
    fills:  [solid(INK)],
    clip:   true,
    children: layers,
  }],
};

const outPath = path.join(__dirname, 'apex-talent-fb-cover.pen');
fs.writeFileSync(outPath, JSON.stringify(doc, null, 2), 'utf8');

console.log(`\n✅  apex-talent-fb-cover.pen — ${W}×${H}px`);
console.log(`📦  ${layers.length} layers`);
console.log(`📍  ${outPath}\n`);

// Layout summary
const groups = [
  ['Background + glow + bars',    layers.slice(0, 5).length],
  ['Decorative rings + dots',     layers.slice(5, 15).length],
  ['Logo + URL',                  2],
  ['LIVE badge',                  3],
  ['Headline (3 lines)',          3],
  ['Tagline',                     1],
  ['Country chips (3)',           6],
  ['CTA button',                  2],
  ['Right: stats + platforms',    8],
];
groups.forEach(([g, n]) => console.log(`  • ${g.padEnd(32)} ${n} layers`));
