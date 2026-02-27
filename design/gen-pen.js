#!/usr/bin/env node
// Apex Talent — .pen design system generator
// Usage: node landing/gen-pen.js

const fs = require('fs');
const path = require('path');

// ── ID counter ────────────────────────────────────────────────────────────────
let _id = 0;
const uid = (prefix = 'n') => `${prefix}${++_id}`;

// ── Colour helpers ─────────────────────────────────────────────────────────────
// rgba → 8-digit hex
const toHex8 = (r, g, b, a) => {
  const h = (n) => n.toString(16).padStart(2, '0').toUpperCase();
  return `#${h(r)}${h(g)}${h(b)}${h(Math.round(a * 255))}`;
};
const INK = '#1A0F2E';

// ── Primitive builders ─────────────────────────────────────────────────────────
const rect = (id, name, x, y, w, h, opts = {}) => ({
  id, name, type: 'rectangle', x, y, width: w, height: h,
  ...(opts.r   !== undefined ? { cornerRadius: opts.r }          : {}),
  ...(opts.fill !== undefined ? { fills: [opts.fill] }           : {}),
  ...(opts.fills !== undefined ? { fills: opts.fills }           : {}),
  ...(opts.stroke !== undefined ? { strokes: [opts.stroke] }     : {}),
  ...(opts.effects !== undefined ? { effects: opts.effects }     : {}),
});

const txt = (id, name, x, y, w, h, content, style = {}) => ({
  id, name, type: 'text', x, y, width: w, height: h,
  textGrowth: 'fixed-width',
  content,
  fontFamily:    style.ff  ?? 'Plus Jakarta Sans',
  fontSize:      style.fs  ?? 13,
  fontWeight:    style.fw  ?? 400,
  lineHeight:    style.lh  ?? 1.5,
  ...(style.ls  !== undefined ? { letterSpacing: style.ls } : {}),
  ...(style.ta  !== undefined ? { textAlign: style.ta }     : {}),
  fills: [style.color ?? INK],
});

const overline = (x, y, content) =>
  txt(uid('t'), content, x, y, 600, 14, content, {
    ff: 'Outfit', fs: 10, fw: 700, ls: 1.4, color: toHex8(26,15,46,0.35),
  });

const solidFill  = (hex)  => ({ type: 'color', color: hex });
const alphaFill  = (r,g,b,a) => solidFill(toHex8(r,g,b,a));
const linGrad = (deg, stops) => ({
  type: 'gradient', gradientType: 'linear', rotation: deg, colors: stops,
});
const shadow = (dy, blur, spread, alpha) => ({
  type: 'shadow', shadowType: 'outer',
  offset: { x: 0, y: dy }, blur, spread,
  color: toHex8(26, 15, 46, alpha),
});
const stroke = (hex, w = 1) => ({ color: hex, width: w });

// ── Swatch group ───────────────────────────────────────────────────────────────
// Returns flat array of objects for one colour swatch (rect + 2 text labels)
function swatch(name, fill, x, y) {
  const W = 80, H = 60, R = 12;
  const hexLabel = typeof fill === 'string' ? fill : '(gradient)';
  return [
    rect(uid('r'), name, x, y, W, H, {
      fills: [typeof fill === 'string' ? solidFill(fill) : fill],
      stroke: stroke(toHex8(26,15,46,0.08)),
      r: R,
    }),
    txt(uid('t'), `${name}-n`, x, y + H + 6, 140, 13, name, {
      ff: 'Outfit', fs: 11, fw: 700, color: INK,
    }),
    txt(uid('t'), `${name}-v`, x, y + H + 21, 140, 12, hexLabel, {
      fs: 11, fw: 400, color: toHex8(26,15,46,0.45),
    }),
  ];
}

// ── Frame wrapper ──────────────────────────────────────────────────────────────
const frame = (id, name, x, y, w, h, bgFill, children) => ({
  id, name, type: 'frame', x, y, width: w, height: h,
  fills: [solidFill(bgFill)], clip: true, children,
});

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 01 — COLOR PALETTE
// ══════════════════════════════════════════════════════════════════════════════
function frame01Colors() {
  const els = [];
  const STEP = 100; // swatch width 80 + gap 20

  els.push(overline(48, 32, '01 — COLORS / PRIMITIVE PALETTE'));

  // Row A: Brand (y = 70)
  els.push(txt(uid('t'), 'g-brand', 48, 66, 200, 12, 'BRAND', {
    ff:'Outfit', fs:9, fw:700, ls:1.2, color: toHex8(26,15,46,0.35),
  }));
  [['color.ink','#1A0F2E'],['color.magenta','#E33BC5'],['color.lime','#CCFF00'],['color.orange','#FF8C42']]
    .forEach(([n,c],i) => els.push(...swatch(n, c, 48 + i*STEP, 82)));

  // Row A: Backgrounds (x = 500)
  els.push(txt(uid('t'), 'g-bg', 500, 66, 200, 12, 'BACKGROUNDS', {
    ff:'Outfit', fs:9, fw:700, ls:1.2, color: toHex8(26,15,46,0.35),
  }));
  [['color.white','#FFFFFF'],['color.cream.base','#FFF5F0'],['color.cream.mid','#FFFAED'],
   ['color.cream.warm','#FFF3B0'],['color.surface','#FAFAFA']]
    .forEach(([n,c],i) => els.push(...swatch(n, c, 500 + i*STEP, 82)));

  // Row B: Purple alpha (y = 210)
  els.push(txt(uid('t'), 'g-alpha', 48, 206, 300, 12, 'PURPLE / ALPHA', {
    ff:'Outfit', fs:9, fw:700, ls:1.2, color: toHex8(26,15,46,0.35),
  }));
  [
    ['purple.soft',      toHex8(26,15,46,0.05)],
    ['purple.muted',     toHex8(26,15,46,0.08)],
    ['purple.dim',       toHex8(26,15,46,0.15)],
    ['purple.mid',       toHex8(26,15,46,0.35)],
    ['purple.sub',       toHex8(26,15,46,0.55)],
    ['purple.secondary', toHex8(26,15,46,0.65)],
  ].forEach(([n,c],i) => els.push(...swatch(n, c, 48 + i*STEP, 222)));

  // Row B: Interactive (x = 700)
  els.push(txt(uid('t'), 'g-int', 700, 206, 300, 12, 'INTERACTIVE / BORDER', {
    ff:'Outfit', fs:9, fw:700, ls:1.2, color: toHex8(26,15,46,0.35),
  }));
  [['interactive.primary','#E33BC5'],['interactive.accent','#CCFF00'],
   ['border.focus','#E33BC5'],['border.accent','#CCFF00'],['bg.dark','#1A0F2E']]
    .forEach(([n,c],i) => els.push(...swatch(n, c, 700 + i*STEP, 222)));

  // Gradients row (y = 360)
  els.push(txt(uid('t'), 'g-grad', 48, 356, 200, 12, 'GRADIENTS', {
    ff:'Outfit', fs:9, fw:700, ls:1.2, color: toHex8(26,15,46,0.35),
  }));
  // gradient.text
  els.push(
    rect(uid('r'), 'gradient.text', 48, 372, 160, 72, {
      r: 16,
      fills: [linGrad(135, [{color:'#E33BC5FF',position:0},{color:'#FF8C42FF',position:1}])],
    }),
    txt(uid('t'), 'gt-label', 48, 450, 200, 12, 'gradient.text — 135° Magenta → Orange', {
      fs:10, color: toHex8(26,15,46,0.45),
    }),
  );
  // gradient.hero.bg
  els.push(
    rect(uid('r'), 'gradient.hero.bg', 232, 372, 160, 72, {
      r: 16,
      fills: [linGrad(150, [{color:'#FFF5F0FF',position:0},{color:'#FFFAEDFF',position:0.5},{color:'#FFF3B0FF',position:1}])],
      stroke: stroke(toHex8(26,15,46,0.1)),
    }),
    txt(uid('t'), 'ghb-label', 232, 450, 220, 12, 'gradient.hero.bg — 150° Cream', {
      fs:10, color: toHex8(26,15,46,0.45),
    }),
  );
  // gradient.success.icon
  els.push(
    rect(uid('r'), 'gradient.success.icon', 416, 372, 72, 72, {
      r: 36,
      fills: [linGrad(135, [{color:'#CCFF00FF',position:0},{color:'#E33BC5FF',position:1}])],
    }),
    txt(uid('t'), 'gsi-label', 416, 450, 220, 12, 'gradient.success — Lime → Magenta', {
      fs:10, color: toHex8(26,15,46,0.45),
    }),
  );
  // gradient.step.line
  els.push(
    rect(uid('r'), 'gradient.step.line', 616, 400, 200, 8, {
      r: 4,
      fills: [linGrad(90, [{color:toHex8(227,59,197,0.3),position:0},{color:toHex8(204,255,0,0.3),position:1}])],
    }),
    txt(uid('t'), 'gsl-label', 616, 450, 240, 12, 'gradient.step.line — Step connector', {
      fs:10, color: toHex8(26,15,46,0.45),
    }),
  );

  return frame('f01', '01 — Color Palette', 0, 0, 1440, 492, '#FFF5F0', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 02 — TYPOGRAPHY
// ══════════════════════════════════════════════════════════════════════════════
function frame02Typography() {
  const els = [];
  els.push(overline(48, 32, '02 — TYPOGRAPHY SCALE'));

  const SCALE = [
    { token:'type.display',     meta:'Outfit 900 · 67px / 1.05',     text:'Earn More Streaming',          ff:'Outfit', fs:67, fw:900, lh:1.05, h:80 },
    { token:'type.h1',          meta:'Outfit 800 · 48px / 1.1',      text:'Join the Global Network',      ff:'Outfit', fs:48, fw:800, lh:1.10, h:56 },
    { token:'type.h2',          meta:'Outfit 800 · 35px / 1.15',     text:'How It Works',                 ff:'Outfit', fs:35, fw:800, lh:1.15, h:44 },
    { token:'type.h3',          meta:'Outfit 700 · 22px / 1.2',      text:'Fast Onboarding Process',      ff:'Outfit', fs:22, fw:700, lh:1.20, h:32 },
    { token:'type.label',       meta:'Outfit 700 · 12px · 0.12em',   text:'HOW TO GET STARTED',           ff:'Outfit', fs:12, fw:700, lh:1.40, ls:1.44, h:18, color: toHex8(26,15,46,0.45) },
    { token:'type.body.lg',     meta:'Plus Jakarta Sans 400 · 17px', text:'We connect operators from Philippines, Nigeria, and Indonesia with top platforms.', fs:17, fw:400, lh:1.65, h:30 },
    { token:'type.body',        meta:'Plus Jakarta Sans 400 · 15px', text:'Fill out the form, pass our quick technical check, and get matched within 48 hours.', fs:15, fw:400, lh:1.60, h:28 },
    { token:'type.body.sm',     meta:'Plus Jakarta Sans 400 · 13px', text:'Platform fees and earning estimates vary by region and experience level.',           fs:13, fw:400, lh:1.50, h:24, color: toHex8(26,15,46,0.55) },
    { token:'type.serif.accent',meta:'Fraunces 400 italic',           text:'"The fastest path from zero to your first streaming paycheck."', ff:'Fraunces', fs:24, fw:400, lh:1.30, h:36 },
  ];

  let curY = 68;
  SCALE.forEach(({ token, meta, text, ff, fs, fw, lh, ls, h, color }) => {
    // meta label (right side)
    els.push(txt(uid('t'), `${token}-meta`, 740, curY + (h - 13) / 2, 660, 13, `${token}  ·  ${meta}`, {
      fs:11, color: toHex8(26,15,46,0.35),
    }));
    // sample text
    const t = txt(uid('t'), token, 48, curY, 680, h, text, {
      ff: ff ?? 'Plus Jakarta Sans', fs, fw, lh, color: color ?? INK,
    });
    if (ls !== undefined) t.letterSpacing = ls;
    els.push(t);
    // thin divider
    els.push(rect(uid('r'), 'div', 48, curY + h + 12, 1344, 1, {
      fills: [alphaFill(26,15,46,0.06)],
    }));
    curY += h + 32;
  });

  return frame('f02', '02 — Typography Scale', 0, 532, 1440, curY + 24, '#FFFFFF', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 03 — BUTTONS
// ══════════════════════════════════════════════════════════════════════════════
function frame03Buttons() {
  const els = [];
  els.push(overline(48, 32, '03 — BUTTONS'));

  const BTNS = [
    { name:'btn-dark',       label:'Primary',          bg:'#1A0F2E', text:'Apply Now',       tc:'#FFFFFF', x:48,  w:180, h:52, fs:16 },
    { name:'btn-magenta',    label:'Emotional CTA',    bg:'#E33BC5', text:'Start Earning →', tc:'#FFFFFF', x:252, w:200, h:52, fs:16 },
    { name:'btn-lime',       label:'Secondary',        bg:'#FFFFFF', text:'Learn More',      tc:'#1A0F2E', x:476, w:180, h:52, fs:16, border:'#1A0F2E' },
    { name:'btn-dark-sm',    label:'Primary SM',       bg:'#1A0F2E', text:'Apply Now',       tc:'#FFFFFF', x:700, w:140, h:40, fs:13 },
    { name:'btn-magenta-sm', label:'Emotional CTA SM', bg:'#E33BC5', text:'Join Free',       tc:'#FFFFFF', x:860, w:120, h:40, fs:13 },
  ];

  BTNS.forEach(({ name, label, bg, text, tc, x, w, h, fs, border }) => {
    els.push(rect(uid('r'), `${name}-bg`, x, 68, w, h, {
      r: 100,
      fills: [solidFill(bg)],
      ...(border ? { stroke: stroke(border, 2) } : {}),
    }));
    els.push(txt(uid('t'), `${name}-lbl`, x, 68 + h + 10, w + 60, 13, `${name} · ${label}`, {
      fs:11, color: toHex8(26,15,46,0.45),
    }));
    els.push(txt(uid('t'), `${name}-txt`, x, 68 + (h - fs * 1.3) / 2, w, fs * 1.3, text, {
      ff:'Outfit', fs, fw:800, ta:'center', color: tc,
    }));
  });

  return frame('f03', '03 — Buttons', 0, 0, 1440, 160, '#FFF5F0', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 04 — CHIPS & BADGES
// ══════════════════════════════════════════════════════════════════════════════
function frame04Chips() {
  const els = [];
  els.push(overline(48, 32, '04 — CHIPS & BADGES'));

  const CHIPS = [
    { name:'chip-default', text:'🇵🇭 Philippines',       bg: toHex8(26,15,46,0.05), tc: INK },
    { name:'chip-lime',    text:'⚡ Active Now',          bg: toHex8(204,255,0,0.2), tc: INK },
    { name:'chip-magenta', text:'✦ New',                 bg: toHex8(227,59,197,0.12), tc:'#E33BC5' },
    { name:'chip-purple',  text:'hello@apextalent.pro',  bg:'#6366F1', tc:'#FFFFFF' },
    { name:'chip-dark',    text:'🌍 Global',             bg: INK,      tc: toHex8(255,255,255,0.8) },
  ];

  let cx = 48;
  CHIPS.forEach(({ name, text, bg, tc }) => {
    const W = text.length * 7.8 + 28;
    els.push(rect(uid('r'), `${name}-bg`, cx, 68, W, 32, { r:100, fills:[solidFill(bg)] }));
    els.push(txt(uid('t'), `${name}-t`, cx + 14, 76, W - 28, 16, text, {
      fs:13, fw:600, color: tc,
    }));
    els.push(txt(uid('t'), `${name}-l`, cx, 110, W + 20, 13, name, {
      fs:11, color: toHex8(26,15,46,0.45),
    }));
    cx += W + 20;
  });

  return frame('f04', '04 — Chips & Badges', 0, 0, 1440, 152, '#FFFFFF', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 05 — CARDS
// ══════════════════════════════════════════════════════════════════════════════
function frame05Cards() {
  const els = [];
  els.push(overline(48, 32, '05 — CARDS'));

  const shadow_card      = shadow(20, 40, -10, 0.08);
  const shadow_card_hover = shadow(32, 64, -16, 0.15);

  // Default card
  els.push(rect(uid('r'), 'card-default', 48, 68, 280, 200, {
    r:20, fills:[solidFill('#FFFFFF')], effects:[shadow_card],
  }));
  els.push(txt(uid('t'), 'cd-l', 48, 278, 280, 13, 'card · shadow.card', { fs:11, color: toHex8(26,15,46,0.45) }));

  // Lime accent card
  els.push(rect(uid('r'), 'card-lime', 352, 68, 280, 200, {
    r:20, fills:[solidFill('#FFFFFF')],
    stroke: stroke('#CCFF00', 2.5), effects:[shadow_card],
  }));
  els.push(txt(uid('t'), 'cl-l', 352, 278, 320, 13, 'card-lime · border.accent + shadow.card', { fs:11, color: toHex8(26,15,46,0.45) }));

  // Card hover state
  els.push(rect(uid('r'), 'card-hover', 656, 50, 280, 220, {
    r:20, fills:[solidFill('#FFFFFF')], effects:[shadow_card_hover],
  }));
  els.push(txt(uid('t'), 'ch-l', 656, 280, 280, 13, 'card :hover · shadow.card-hover', { fs:11, color: toHex8(26,15,46,0.45) }));
  // Hover label badge
  els.push(rect(uid('r'), 'hover-badge', 656, 50, 80, 24, { r:100, fills:[solidFill(toHex8(26,15,46,0.08))] }));
  els.push(txt(uid('t'), 'hover-badge-t', 668, 55, 60, 14, ':hover', { ff:'Outfit', fs:10, fw:700, color: toHex8(26,15,46,0.55) }));

  // Dark card
  els.push(rect(uid('r'), 'card-dark', 960, 68, 280, 200, { r:20, fills:[solidFill(INK)] }));
  els.push(txt(uid('t'), 'cdark-l', 960, 278, 280, 13, 'card-dark · color.bg.dark', { fs:11, color: toHex8(26,15,46,0.45) }));

  return frame('f05', '05 — Cards', 0, 0, 1440, 320, '#FFF5F0', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 06 — FORM INPUTS
// ══════════════════════════════════════════════════════════════════════════════
function frame06Inputs() {
  const els = [];
  els.push(overline(48, 32, '06 — FORM INPUTS'));

  const INPUTS = [
    { name:'default', label:'Full Name',     val:'Maria Santos',       placeholder:true,  focused:false, x:48  },
    { name:'focused', label:'Email Address', val:'maria@example.com',  placeholder:false, focused:true,  x:380 },
    { name:'filled',  label:'Country',       val:'Philippines 🇵🇭',    placeholder:false, focused:false, x:712 },
  ];

  INPUTS.forEach(({ name, label, val, placeholder, focused, x }) => {
    // label
    els.push(txt(uid('t'), `inp-${name}-lbl`, x, 68, 280, 16, label, {
      ff:'Outfit', fs:13, fw:600, color: INK,
    }));
    // bg
    els.push(rect(uid('r'), `inp-${name}-bg`, x, 90, 280, 48, {
      r: 12,
      fills: [solidFill(focused ? '#FFFFFF' : '#FAFAFA')],
      stroke: stroke(focused ? '#E33BC5' : toHex8(26,15,46,0.1), 2),
    }));
    // value
    els.push(txt(uid('t'), `inp-${name}-val`, x + 16, 104, 248, 20, val, {
      fs:15, color: placeholder ? toHex8(26,15,46,0.35) : INK,
    }));
    // state label
    const stateText = focused ? 'Focused (border-color: magenta)' : placeholder ? 'Default state (placeholder)' : 'Filled state';
    els.push(txt(uid('t'), `inp-${name}-state`, x, 148, 280, 13, stateText, {
      fs:11, color: toHex8(26,15,46,0.45),
    }));
  });

  return frame('f06', '06 — Form Inputs', 0, 0, 1440, 188, '#FFFFFF', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 07 — BORDER RADIUS
// ══════════════════════════════════════════════════════════════════════════════
function frame07Radius() {
  const els = [];
  els.push(overline(48, 32, '07 — BORDER RADIUS'));

  const RADII = [
    { token:'radius.sm',   r:8,   px:'8px',   desc:'Buttons, small pills' },
    { token:'radius.md',   r:12,  px:'12px',  desc:'Inputs, small cards'  },
    { token:'radius.lg',   r:16,  px:'16px',  desc:'Modals, banners'      },
    { token:'radius.xl',   r:20,  px:'20px',  desc:'.card'                },
    { token:'radius.full', r:100, px:'100px', desc:'Chips, avatars'       },
  ];

  let cx = 48;
  RADII.forEach(({ token, r, px, desc }) => {
    els.push(rect(uid('r'), token, cx, 68, 80, 80, { r: Math.min(r, 40), fills:[solidFill(INK)] }));
    els.push(txt(uid('t'), `${token}-t`, cx, 158, 120, 13, token, { ff:'Outfit', fs:11, fw:700, color: toHex8(26,15,46,0.5) }));
    els.push(txt(uid('t'), `${token}-v`, cx, 173, 120, 12, px,    { fs:11, color: toHex8(26,15,46,0.4) }));
    els.push(txt(uid('t'), `${token}-d`, cx, 187, 140, 12, desc,  { fs:10, color: toHex8(26,15,46,0.35) }));
    cx += 128;
  });

  return frame('f07', '07 — Border Radius', 0, 0, 1440, 216, '#FFF5F0', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 08 — SPACING SCALE
// ══════════════════════════════════════════════════════════════════════════════
function frame08Spacing() {
  const els = [];
  els.push(overline(48, 32, '08 — SPACING SCALE (base 8px)'));

  const SPACINGS = [4,8,12,16,20,24,32,40,48,64,96];
  const MAX_H = 96;
  const BASE_Y = 52 + MAX_H; // bars grow upward from this line

  let cx = 48;
  SPACINGS.forEach((px, i) => {
    const token = [1,2,3,4,5,6,8,10,12,16,24][i];
    const barH = Math.min(px, MAX_H);
    const barW = Math.max(px * 0.7, 6);
    els.push(rect(uid('r'), `space-${token}`, cx, BASE_Y - barH, barW, barH, {
      r: 3,
      fills: [linGrad(180, [{color:'#E33BC5FF',position:0},{color:'#FF8C42FF',position:1}])],
    }));
    els.push(txt(uid('t'), `sp-t${token}`, cx, BASE_Y + 6,  50, 12, `space.${token}`, { ff:'Outfit', fs:9, fw:700, color: toHex8(26,15,46,0.4) }));
    els.push(txt(uid('t'), `sp-v${token}`, cx, BASE_Y + 19, 50, 12, `${px}px`,        { fs:10, color: toHex8(26,15,46,0.4) }));
    cx += barW + 16;
  });

  return frame('f08', '08 — Spacing Scale', 0, 0, 1440, BASE_Y + 48, '#FFFFFF', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 09 — SHADOWS
// ══════════════════════════════════════════════════════════════════════════════
function frame09Shadows() {
  const els = [];
  els.push(overline(48, 32, '09 — ELEVATION / SHADOWS'));

  const SHADOWS = [
    { name:'shadow.card',     eff: shadow(20,40,-10,0.08), desc:'Cards' },
    { name:'shadow.card-hover', eff: shadow(32,64,-16,0.15), desc:'Card :hover' },
    { name:'shadow.cookie',   eff: shadow(8,32,0,0.22),    desc:'Floating / banner' },
    { name:'shadow.nav',      eff: shadow(1,0,0,0.07),     desc:'Scrolled navbar' },
    { name:'shadow.nav-full', eff: shadow(1,24,0,0.07),    desc:'.nav-solid' },
  ];

  let cx = 48;
  SHADOWS.forEach(({ name, eff, desc }) => {
    els.push(rect(uid('r'), name, cx, 68, 160, 100, { r:16, fills:[solidFill('#FFFFFF')], effects:[eff] }));
    els.push(txt(uid('t'), `${name}-n`, cx, 178, 200, 13, name, { ff:'Outfit', fs:11, fw:700, color: toHex8(26,15,46,0.5) }));
    els.push(txt(uid('t'), `${name}-d`, cx, 193, 200, 12, desc, { fs:11, color: toHex8(26,15,46,0.4) }));
    cx += 220;
  });

  return frame('f09', '09 — Shadows', 0, 0, 1440, 232, '#FFF5F0', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  FRAME 10 — MOTION TOKENS
// ══════════════════════════════════════════════════════════════════════════════
function frame10Motion() {
  const els = [];
  els.push(overline(48, 32, '10 — MOTION TOKENS'));

  const DURATIONS = [
    ['duration.fast',    '150ms', 'Button hover, filter'],
    ['duration.base',    '200ms', 'Color transitions (border, nav links)'],
    ['duration.normal',  '300ms', 'Card hover, FAQ icon rotate'],
    ['duration.slow',    '450ms', 'FAQ accordion, scroll reveal, fade-up'],
    ['duration.entrance','750ms', 'Word reveal animation (hero)'],
  ];
  const EASINGS = [
    ['easing.spring',    'cubic-bezier(0.16, 1, 0.3, 1)', 'Entrance animations'],
    ['easing.standard',  'ease',                           'Scroll reveal, card hover'],
    ['easing.accordion', 'cubic-bezier(0.4, 0, 0.2, 1)',  'FAQ max-height'],
    ['easing.linear',    'linear',                         'Clock animations'],
  ];

  // Duration column
  els.push(txt(uid('t'), 'dur-h', 48, 62, 120, 12, 'DURATION', { ff:'Outfit', fs:9, fw:700, ls:1.2, color: toHex8(26,15,46,0.35) }));
  DURATIONS.forEach(([token, val, desc], i) => {
    const y = 80 + i * 32;
    els.push(txt(uid('t'), `dur-t${i}`, 48,  y, 200, 16, token, { fs:13, color: toHex8(26,15,46,0.6) }));
    els.push(txt(uid('t'), `dur-v${i}`, 260, y, 80,  16, val,   { ff:'Outfit', fs:13, fw:700, color:'#E33BC5' }));
    els.push(txt(uid('t'), `dur-d${i}`, 360, y, 320, 16, desc,  { fs:12, color: toHex8(26,15,46,0.4) }));
  });

  // Easing column
  els.push(txt(uid('t'), 'eas-h', 720, 62, 120, 12, 'EASING', { ff:'Outfit', fs:9, fw:700, ls:1.2, color: toHex8(26,15,46,0.35) }));
  EASINGS.forEach(([token, val, desc], i) => {
    const y = 80 + i * 32;
    els.push(txt(uid('t'), `eas-t${i}`, 720,  y, 200, 16, token, { fs:13, color: toHex8(26,15,46,0.6) }));
    els.push(txt(uid('t'), `eas-v${i}`, 940,  y, 360, 16, val,   { ff:'Outfit', fs:12, fw:600, color: INK }));
    els.push(txt(uid('t'), `eas-d${i}`, 1320, y, 200, 16, desc,  { fs:12, color: toHex8(26,15,46,0.4) }));
  });

  return frame('f10', '10 — Motion Tokens', 0, 0, 1440, 240, '#FFFFFF', els);
}

// ══════════════════════════════════════════════════════════════════════════════
//  VARIABLES (design tokens)
// ══════════════════════════════════════════════════════════════════════════════
const variables = {
  // ── Colors ─────────────────────────────────────
  color_ink:               { type:'color',  value:'#1A0F2E' },
  color_magenta:           { type:'color',  value:'#E33BC5' },
  color_lime:              { type:'color',  value:'#CCFF00' },
  color_orange:            { type:'color',  value:'#FF8C42' },
  color_white:             { type:'color',  value:'#FFFFFF' },
  color_cream_base:        { type:'color',  value:'#FFF5F0' },
  color_cream_mid:         { type:'color',  value:'#FFFAED' },
  color_cream_warm:        { type:'color',  value:'#FFF3B0' },
  color_surface:           { type:'color',  value:'#FAFAFA' },
  color_purple_soft:       { type:'color',  value: toHex8(26,15,46,0.05) },
  color_purple_muted:      { type:'color',  value: toHex8(26,15,46,0.08) },
  color_purple_dim:        { type:'color',  value: toHex8(26,15,46,0.15) },
  color_purple_mid:        { type:'color',  value: toHex8(26,15,46,0.35) },
  color_purple_sub:        { type:'color',  value: toHex8(26,15,46,0.55) },
  color_purple_secondary:  { type:'color',  value: toHex8(26,15,46,0.65) },
  color_text_primary:      { type:'color',  value:'#1A0F2E' },
  color_text_secondary:    { type:'color',  value: toHex8(26,15,46,0.65) },
  color_text_placeholder:  { type:'color',  value: toHex8(26,15,46,0.35) },
  color_text_muted:        { type:'color',  value: toHex8(26,15,46,0.55) },
  color_text_inverted:     { type:'color',  value: toHex8(255,255,255,0.65) },
  color_bg_dark:           { type:'color',  value:'#1A0F2E' },
  color_bg_card:           { type:'color',  value:'#FFFFFF' },
  color_bg_input:          { type:'color',  value:'#FAFAFA' },
  color_border_default:    { type:'color',  value: toHex8(26,15,46,0.08) },
  color_border_input:      { type:'color',  value: toHex8(26,15,46,0.10) },
  color_border_focus:      { type:'color',  value:'#E33BC5' },
  color_border_accent:     { type:'color',  value:'#CCFF00' },
  color_interactive_primary: { type:'color', value:'#E33BC5' },
  color_interactive_accent:  { type:'color', value:'#CCFF00' },
  // ── Typography ─────────────────────────────────
  font_heading:      { type:'string', value:'Outfit' },
  font_serif:        { type:'string', value:'Fraunces' },
  font_body:         { type:'string', value:'Plus Jakarta Sans' },
  font_size_display: { type:'number', value:67 },
  font_size_h1:      { type:'number', value:48 },
  font_size_h2:      { type:'number', value:35 },
  font_size_h3:      { type:'number', value:22 },
  font_size_label:   { type:'number', value:12 },
  font_size_body_lg: { type:'number', value:17 },
  font_size_body:    { type:'number', value:15 },
  font_size_body_sm: { type:'number', value:13 },
  // ── Spacing ────────────────────────────────────
  space_1:  { type:'number', value:4  },
  space_2:  { type:'number', value:8  },
  space_3:  { type:'number', value:12 },
  space_4:  { type:'number', value:16 },
  space_5:  { type:'number', value:20 },
  space_6:  { type:'number', value:24 },
  space_8:  { type:'number', value:32 },
  space_10: { type:'number', value:40 },
  space_12: { type:'number', value:48 },
  space_16: { type:'number', value:64 },
  space_24: { type:'number', value:96 },
  // ── Radius ─────────────────────────────────────
  radius_sm:   { type:'number', value:8   },
  radius_md:   { type:'number', value:12  },
  radius_lg:   { type:'number', value:16  },
  radius_xl:   { type:'number', value:20  },
  radius_full: { type:'number', value:100 },
  // ── Motion ─────────────────────────────────────
  duration_fast:     { type:'number', value:150 },
  duration_base:     { type:'number', value:200 },
  duration_normal:   { type:'number', value:300 },
  duration_slow:     { type:'number', value:450 },
  duration_entrance: { type:'number', value:750 },
};

// ══════════════════════════════════════════════════════════════════════════════
//  Stack frames vertically with a gap
// ══════════════════════════════════════════════════════════════════════════════
const GAP = 40;

// Frames that share a "row" (same y), plus stacked frames
const ROW1_FRAMES = [frame03Buttons(), frame04Chips(), frame05Cards(), frame06Inputs()];
const STACK_FRAMES = [frame07Radius(), frame08Spacing(), frame09Shadows(), frame10Motion()];

// Position Row-1 frames side-by-side? No — stack everything vertically for clarity
const f01 = frame01Colors();
const f02 = frame02Typography();

// Compute y positions
let yOffset = f01.height + GAP;
f02.y = yOffset;

yOffset += f02.height + GAP;

// Stack the smaller frames
const smallFrames = [...ROW1_FRAMES, ...STACK_FRAMES];
smallFrames.forEach((f) => {
  f.y = yOffset;
  yOffset += f.height + GAP;
});

// ══════════════════════════════════════════════════════════════════════════════
//  ASSEMBLE & WRITE
// ══════════════════════════════════════════════════════════════════════════════
const doc = {
  version: '1',
  variables,
  children: [f01, f02, ...smallFrames],
};

const outPath = path.join(__dirname, 'apex-talent.pen');
fs.writeFileSync(outPath, JSON.stringify(doc, null, 2), 'utf8');

const frameNames = doc.children.map(f => `  • ${f.name} (h: ${f.height}px)`).join('\n');
const varCount   = Object.keys(variables).length;
console.log(`\n✅  apex-talent.pen written to: ${outPath}`);
console.log(`\n📦  ${varCount} design tokens (variables)`);
console.log(`\n🖼   ${doc.children.length} frames:\n${frameNames}\n`);
