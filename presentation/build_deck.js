// presentation/build_deck.js
// Builds Lexi_AI_Judges_Deck.pptx (16 main slides + 2 appendix) with pptxgenjs.
// Run:  NODE_PATH=/path/to/node_modules node presentation/build_deck.js
// Needs: npm i pptxgenjs sharp react react-dom react-icons   (installed outside the repo)
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const fi = require("react-icons/fi");

const SKILL_SCRIPTS = process.env.PPTX_SKILL_SCRIPTS;
const { applyTheme } = require(path.join(SKILL_SCRIPTS, "apply_theme.js"));

const ASSETS = path.join(__dirname, "assets");
const SHOTS = path.join(ASSETS, "shots");
const CROPS = path.join(ASSETS, "crops");
const OUT = path.join(__dirname, "Lexi_AI_Judges_Deck.pptx");

// ───────────────────────────── theme ─────────────────────────────
const THEME = {
  name: "Lexi AI Night",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "050B1B", lt1: "FFFFFF", dk2: "101C3A", lt2: "A9B8D6",
    accent1: "38BDF8", accent2: "5B93FF", accent3: "A78BFA",
    accent4: "34D399", accent5: "FBBF24", accent6: "FB7185",
    hlink: "5B93FF", folHlink: "A78BFA",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Lexi AI — Business document intelligence";
pres.subject = "Project presentation for judges";
pres.author = "Vidushi Bhadauria, Parth Nawal, Aryama Sharma, Ashi Srivastava, Simran Karan Bora";
const C = pres.SchemeColor;
const WHITE = C.background1, MUTED = C.background2, CARD = C.text2, INK = C.text1;
const CYAN = C.accent1, BLUE = C.accent2, VIOLET = C.accent3, GREEN = C.accent4, AMBER = C.accent5, ROSE = C.accent6;

// ───────────────────────────── layouts ─────────────────────────────
pres.defineSlideMaster({
  title: "TITLE_SLIDE",
  background: { path: path.join(ASSETS, "bg_title.png") },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { path: path.join(ASSETS, "bg_content.png") },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.13, h: 0.85, fontSize: 34, bold: true, color: WHITE, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "Lexi AI  ·  Business document intelligence", options: { x: 0.6, y: 7.03, w: 6, h: 0.3, fontSize: 10, color: MUTED, margin: 0, valign: "middle" } } },
  ],
  slideNumber: { x: 12.0, y: 7.03, w: 0.73, h: 0.3, fontSize: 10, color: MUTED, align: "right", margin: 0 },
});

// ───────────────────────────── helpers ─────────────────────────────
const iconCache = {};
async function icon(key, hex) {
  const k = key + hex;
  if (!iconCache[k]) {
    const svg = renderToStaticMarkup(React.createElement(fi[key], { color: "#" + hex, size: "256" }));
    const buf = await sharp(Buffer.from(svg), { density: 300 }).resize(256, 256).png().toBuffer();
    iconCache[k] = "image/png;base64," + buf.toString("base64");
  }
  return iconCache[k];
}

function T(slide, text, x, y, w, h, o = {}) {
  slide.addText(text, Object.assign(
    { x, y, w, h, fontSize: 16, color: WHITE, margin: 0, valign: "top", isTextBox: true }, o));
}

function card(slide, x, y, w, h, name, fill = CARD) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.12, fill: { color: fill },
    line: { color: MUTED, width: 0.75, transparency: 78 }, objectName: name,
  });
}

function chip(slide, text, x, y, w, color, name, h = 0.36) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: h / 2, fill: { color }, line: { type: "none" }, objectName: name,
  });
  T(slide, text, x, y, w, h, { fontSize: 12, bold: true, color: INK, align: "center", valign: "middle", objectName: name + " text" });
}

async function iconCircle(slide, key, cx, cy, d, accent, name) {
  slide.addShape(pres.ShapeType.ellipse, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { color: accent }, line: { type: "none" }, objectName: name });
  slide.addImage({ data: await icon(key, HEX.dk1), x: cx - d * 0.3, y: cy - d * 0.3, w: d * 0.6, h: d * 0.6, objectName: name + " icon", altText: "" });
}

function numCircle(slide, n, cx, cy, d, accent, name) {
  slide.addShape(pres.ShapeType.ellipse, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { color: accent }, line: { type: "none" }, objectName: name });
  T(slide, String(n), cx - d / 2, cy - d / 2, d, d, { fontSize: Math.round(d * 36), bold: true, color: INK, align: "center", valign: "middle", objectName: name + " number" });
}

// a framed, cropped screenshot; returns the image's x/y/w/h
function shot(slide, file, x, y, w, name, alt) {
  const meta = shot.meta[file];
  const h = (w * meta.height) / meta.width;
  slide.addShape(pres.ShapeType.roundRect, {
    x: x - 0.07, y: y - 0.07, w: w + 0.14, h: h + 0.14, rectRadius: 0.1, fill: { color: "0A1224" },
    line: { color: MUTED, width: 0.75, transparency: 65 }, objectName: name + " frame",
  });
  slide.addImage({ path: path.join(CROPS, file), x, y, w, h, objectName: name, altText: alt });
  return { x, y, w, h };
}
shot.meta = {};

async function makeCrop(out, src, left, top, width, height) {
  const f = path.join(CROPS, out);
  await sharp(path.join(SHOTS, src)).extract({ left, top, width, height }).png().toFile(f);
  shot.meta[out] = { width, height };
}

// vertical stack of regions from one screenshot (used for the audit-log composite)
async function makeStack(out, src, regions, gap, bg = "#0A1224") {
  const width = regions[0].width;
  const parts = [];
  let y = 0;
  for (const r of regions) {
    parts.push({ input: await sharp(path.join(SHOTS, src)).extract(r).toBuffer(), left: 0, top: y });
    y += r.height + gap;
  }
  const height = y - gap;
  await sharp({ create: { width, height, channels: 3, background: bg } }).composite(parts).png().toFile(path.join(CROPS, out));
  shot.meta[out] = { width, height };
}

function pin(slide, n, cx, cy, name) {
  numCircle(slide, n, cx, cy, 0.4, AMBER, name);
}

function notes(slide, text) { slide.addNotes(text.trim()); }

// ───────────────────────────── build ─────────────────────────────
async function main() {
  fs.mkdirSync(CROPS, { recursive: true });
  // screenshot crops (pixel boxes in the full-resolution captures)
  await makeCrop("qa_answer.png", "s_qa.jpg", 40, 600, 1520, 1280);
  await makeCrop("qa_source.png", "s_qa.jpg", 40, 3735, 1520, 355);
  await makeCrop("compliance_cards.png", "s_compliance_run1.jpg", 40, 1005, 1520, 930);
  await makeCrop("briefing_top.png", "s_briefing_run1.jpg", 40, 965, 1520, 850);
  await makeCrop("entities_top.png", "s_entities.jpg", 45, 740, 1510, 835);
  await makeCrop("tagging_top.png", "s_tagging_financial.jpg", 40, 600, 1520, 900);
  await makeStack("audit_stack.png", "s_audit_wide.jpg",
    [{ left: 40, top: 465, width: 2110, height: 95 }, { left: 40, top: 735, width: 2110, height: 55 }, { left: 40, top: 1805, width: 2110, height: 530 }], 14);

  let s;

  // ═════════════ 1 · TITLE ═════════════
  pres.addSection({ title: "Opening" });
  s = pres.addSlide({ masterName: "TITLE_SLIDE", sectionTitle: "Opening" });
  {
    const logo = await sharp(Buffer.from(
      `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0EA5E9"/><stop offset="0.55" stop-color="#4F7CFF"/><stop offset="1" stop-color="#8B5CF6"/></linearGradient></defs><rect width="512" height="512" rx="120" fill="url(#g)"/><g fill="none" stroke="#fff" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"><path d="M300 110H190a30 30 0 0 0-30 30v232a30 30 0 0 0 30 30h132a30 30 0 0 0 30-30V162z"/><polyline points="300 110 300 162 352 162"/><circle cx="244" cy="290" r="40"/><line x1="274" y1="320" x2="312" y2="358"/></g></svg>`)).png().toBuffer();
    s.addImage({ data: "image/png;base64," + logo.toString("base64"), x: 0.8, y: 1.15, w: 1.15, h: 1.15, objectName: "Logo", altText: "Lexi AI logo" });
    T(s, [{ text: "Lexi ", options: { color: WHITE } }, { text: "AI", options: { color: CYAN } }], 0.8, 2.45, 7.2, 1.35, { fontSize: 88, bold: true, valign: "middle", objectName: "Title" });
    T(s, "Business document intelligence", 0.8, 3.85, 7.4, 0.6, { fontSize: 30, bold: true, objectName: "Subtitle" });
    T(s, "Cited answers, compliance checks and clause extraction — running on your own machine.", 0.8, 4.5, 6.9, 0.95, { fontSize: 20, color: MUTED, objectName: "Tagline" });
    chip(s, "Hybrid retrieval", 0.8, 5.65, 1.9, CYAN, "Chip hybrid");
    chip(s, "Local LLM", 2.85, 5.65, 1.5, VIOLET, "Chip local");
    chip(s, "Audit-ready", 4.5, 5.65, 1.6, GREEN, "Chip audit");
    shot(s, "qa_answer.png", 8.35, 1.2, 4.35, "Hero screenshot", "Lexi AI answering a question with citations");
    T(s, "Vidushi Bhadauria  ·  Parth Nawal  ·  Aryama Sharma  ·  Ashi Srivastava  ·  Simran Karan Bora", 0.8, 6.65, 11.9, 0.4, { fontSize: 16, color: MUTED, objectName: "Team names" });
  }
  notes(s, `
Open by naming the product and the one-line promise: Lexi AI reads your business documents and gives answers you can check — without sending those documents to a third-party cloud.
The screenshot on the right is the real app answering a real question about a 10-page vendor contract; we'll come back to it in the demo.
Introduce the team in one breath, then move to the problem. Target time for the whole talk: about 10 minutes, plus questions.`);

  // ═════════════ 2 · PROBLEM ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Opening" });
  T(s, "Decisions live in documents — reading them doesn't scale", 0, 0, 0, 0, { placeholder: "title" });
  {
    const cols = [
      { k: "FiClock", c: CYAN, t: "Slow", d: "Contracts, SOPs and reports pile up faster than anyone can read them." },
      { k: "FiAlertTriangle", c: AMBER, t: "Risky", d: "Pasting them into a general chatbot sends sensitive files to a third party." },
      { k: "FiHelpCircle", c: ROSE, t: "Unverifiable", d: "Answers arrive with no way to check them — and no record of who asked what." },
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.1, w = 3.93;
      card(s, x, 1.55, w, 3.55, `Problem card ${i + 1}`);
      await iconCircle(s, cols[i].k, x + 0.85, 2.55, 1.0, cols[i].c, `Problem icon ${i + 1}`);
      T(s, cols[i].t, x + 0.4, 3.3, w - 0.8, 0.5, { fontSize: 26, bold: true, objectName: `Problem title ${i + 1}` });
      T(s, cols[i].d, x + 0.4, 3.9, w - 0.8, 1.1, { fontSize: 16, color: MUTED, objectName: `Problem text ${i + 1}` });
    }
    card(s, 0.6, 5.45, 12.13, 1.2, "Need banner");
    T(s, [{ text: "What teams actually need: answers they can ", options: { color: WHITE } }, { text: "check", options: { color: CYAN, bold: true } },
      { text: ", from documents they ", options: { color: WHITE } }, { text: "control", options: { color: CYAN, bold: true } }, { text: ".", options: { color: WHITE } }],
      0.95, 5.45, 11.45, 1.2, { fontSize: 24, bold: true, valign: "middle", objectName: "Need statement" });
  }
  notes(s, `
Three pains, one sentence each. Reading is slow; a general chatbot means sending confidential documents to someone else's servers; and its answers can't be checked or audited.
The point of the slide is the last line: the need is not 'more AI', it is answers people can verify from documents they keep control of. Everything after this slide is how we tried to deliver that — and how we measured whether we did.`);

  // ═════════════ 3 · IDEA ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Opening" });
  T(s, "Our idea: bring the model to the documents", 0, 0, 0, 0, { placeholder: "title" });
  {
    const steps = [
      ["Retrieve first", "Find the right passages before any model speaks."],
      ["Answer only from them", "A local LLM is told to use nothing else."],
      ["Cite and verify", "Numbered sources, checked quotes, shown confidence."],
      ["Log everything", "A tamper-evident record of who did what."],
    ];
    const cs = [CYAN, BLUE, VIOLET, GREEN];
    for (let i = 0; i < 4; i++) {
      const y = 1.55 + i * 1.3;
      card(s, 0.6, y, 7.1, 1.15, `Principle ${i + 1}`);
      numCircle(s, i + 1, 1.25, y + 0.575, 0.62, cs[i], `Principle number ${i + 1}`);
      T(s, steps[i][0], 1.8, y + 0.14, 5.7, 0.45, { fontSize: 22, bold: true, objectName: `Principle title ${i + 1}` });
      T(s, steps[i][1], 1.8, y + 0.6, 5.7, 0.4, { fontSize: 16, color: MUTED, objectName: `Principle text ${i + 1}` });
    }
    card(s, 8.0, 1.55, 4.73, 5.05, "Objective card");
    await iconCircle(s, "FiTarget", 8.6, 2.2, 0.7, CYAN, "Objective icon");
    T(s, "Objective", 9.15, 1.9, 3.3, 0.6, { fontSize: 24, bold: true, valign: "middle", objectName: "Objective heading" });
    T(s, [{ text: "Build a ", options: { color: WHITE } }, { text: "private, auditable", options: { color: CYAN, bold: true } },
      { text: " platform that turns contracts, reports and SOPs into briefings, compliance verdicts, extracted clauses and answers that cite their source — then ", options: { color: WHITE } },
      { text: "measure honestly", options: { color: CYAN, bold: true } }, { text: " how well it works.", options: { color: WHITE } }],
      8.35, 2.85, 4.05, 3.6, { fontSize: 21, objectName: "Objective text" });
  }
  notes(s, `
The whole design in four verbs: retrieve, answer-only-from-that, cite-and-verify, log. If a judge remembers one slide's worth of architecture, it is this.
The objective has two halves on purpose: build the platform, and measure it honestly. The second half is why the evidence section later includes limitations, not just good news.`);

  // ═════════════ 4 · HOW IT WORKS ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Opening" });
  T(s, "How Lexi AI works", 0, 0, 0, 0, { placeholder: "title" });
  {
    const st = [
      ["FiUploadCloud", CYAN, "Ingest", "PDF, DOCX, XLSX, PPTX, CSV, audio — validated and scanned"],
      ["FiDatabase", BLUE, "Index", "MiniLM vectors in FAISS, plus a BM25 keyword index"],
      ["FiSearch", VIOLET, "Retrieve", "Top-5 passages with page and relevance score"],
      ["FiCpu", GREEN, "Reason", "Local Llama 3.2 3B answers from those passages only"],
      ["FiCheckCircle", AMBER, "Verify", "Citations, quote check, refusal threshold"],
      ["FiLayers", ROSE, "Deliver", "Q&A, briefings, compliance, entities, tags"],
    ];
    const w = 1.86, gap = 0.194;
    for (let i = 0; i < 6; i++) {
      const x = 0.6 + i * (w + gap);
      card(s, x, 1.55, w, 3.1, `Stage card ${i + 1}`);
      await iconCircle(s, st[i][0], x + w / 2, 2.25, 0.8, st[i][1], `Stage icon ${i + 1}`);
      T(s, st[i][2], x + 0.12, 2.9, w - 0.24, 0.4, { fontSize: 20, bold: true, align: "center", objectName: `Stage title ${i + 1}` });
      T(s, st[i][3], x + 0.14, 3.4, w - 0.28, 1.35, { fontSize: 14, color: MUTED, objectName: `Stage text ${i + 1}` });
    }
    card(s, 0.6, 4.95, 12.13, 1.65, "Governance band");
    await iconCircle(s, "FiShield", 1.4, 5.775, 0.8, VIOLET, "Governance icon");
    T(s, "Governance layer", 2.1, 5.3, 3.9, 0.5, { fontSize: 22, bold: true, objectName: "Governance heading" });
    T(s, "Wrapped around every stage above", 2.1, 5.85, 3.9, 0.4, { fontSize: 14, color: MUTED, objectName: "Governance subhead" });
    const g = ["Role-based access", "Hash-chained audit log", "Zero-retention mode", "API keys"];
    for (let i = 0; i < 4; i++) { chip(s, g[i], 6.3 + (i % 2) * 3.2, 5.27 + Math.floor(i / 2) * 0.62, 3.0, VIOLET, `Governance chip ${i + 1}`, 0.46); }
  }
  notes(s, `
Walk left to right in about thirty seconds. Documents are validated, scanned for prompt-injection attempts, and split into overlapping chunks that keep their true page numbers.
Two indexes run side by side: dense vectors (MiniLM in FAISS) for meaning, and BM25 for exact keywords. We blend both scores and hand the top five passages to a local Llama 3.2 3B model with an instruction to answer only from them.
The violet band is what makes it enterprise-shaped rather than a demo: roles, a hash-chained audit log, and an optional zero-retention mode.`);

  // ═════════════ 5 · DEMO: Q&A ═════════════
  pres.addSection({ title: "Demo" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
  T(s, "Ask in plain English, get an answer you can check", 0, 0, 0, 0, { placeholder: "title" });
  {
    const a = shot(s, "qa_answer.png", 0.67, 1.5, 6.1, "Q&A answer screenshot", "Q&A screen showing a cited answer about uptime guarantees");
    pin(s, 1, a.x + a.w + 0.07, a.y + a.h * 0.063, "Pin 1");
    pin(s, 2, a.x + a.w + 0.07, a.y + a.h * 0.357, "Pin 2");
    pin(s, 3, a.x + a.w + 0.07, a.y + a.h * 0.92, "Pin 3");
    const items = [
      [1, "Plain-English question", "No query language, no keywords to guess."],
      [2, "Grounded answer, inline citations", "Markers like [2] and [5] point to numbered sources."],
      [3, "Confidence shown, not hidden", "Retrieval confidence 54 % (Medium) and the cited sources."],
    ];
    for (let i = 0; i < 3; i++) {
      const y = 1.5 + i * 0.95;
      numCircle(s, items[i][0], 7.4, y + 0.22, 0.4, AMBER, `Legend ${i + 1}`);
      T(s, items[i][1], 7.75, y, 4.95, 0.4, { fontSize: 18, bold: true, objectName: `Legend title ${i + 1}` });
      T(s, items[i][2], 7.75, y + 0.4, 4.95, 0.5, { fontSize: 14, color: MUTED, objectName: `Legend text ${i + 1}` });
    }
    numCircle(s, 4, 7.4, 4.5, 0.4, AMBER, "Legend 4");
    T(s, "Verifiable sources", 7.75, 4.28, 4.95, 0.4, { fontSize: 18, bold: true, objectName: "Legend title 4" });
    const b = shot(s, "qa_source.png", 7.4, 4.8, 5.2, "Source card screenshot", "Source card showing document, page, relevance and cited flag");
    pin(s, 4, b.x + b.w + 0.07, b.y + b.h * 0.5, "Pin 4");
    card(s, 7.33, 6.12, 5.4, 0.7, "Verified banner");
    T(s, [{ text: "✓ Checked against the contract: ", options: { bold: true, color: GREEN } }, { text: "99.9 % uptime, 5 % credit per hour, capped at 25 % (§4.2)", options: { color: WHITE } }],
      7.5, 6.12, 5.1, 0.7, { fontSize: 14, valign: "middle", objectName: "Verified text" });
  }
  notes(s, `
This is the real application, not a mock-up. The question: 'What uptime does the Vendor guarantee, and what happens if it falls short?'
Point to the four callouts. One: plain English. Two: the answer carries inline citation markers. Three: it shows its own retrieval confidence — 54 percent, 'Medium' — instead of sounding certain. Four: every source lists document, page, relevance score and whether the model actually cited it.
We checked the answer against section 4.2 of the contract: 99.9 percent availability, a 5 percent service credit per full hour of downtime, capped at 25 percent. The answer matches.
If asked: the confidence number is the retrieval score, not a guarantee the answer is right — which is why the sources are shown.`);

  // ═════════════ 6 · COMPLIANCE + BRIEFING ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
  T(s, "From reading to deciding: compliance and briefings", 0, 0, 0, 0, { placeholder: "title" });
  {
    T(s, "Compliance checker — a quote, or it doesn't pass", 0.6, 1.4, 5.95, 0.4, { fontSize: 20, bold: true, objectName: "Compliance heading" });
    T(s, "Each PASS needs a verbatim quote, machine-checked against the page; unprovable claims drop to REVIEW.", 0.6, 1.82, 5.95, 0.62, { fontSize: 14, color: MUTED, objectName: "Compliance subhead" });
    shot(s, "compliance_cards.png", 0.67, 2.62, 5.5, "Compliance screenshot", "Compliance results: one PASS with a verified quote, one REVIEW");
    card(s, 0.6, 6.12, 5.95, 0.72, "Compliance honesty chip");
    T(s, "Across 8 live runs the 3B model passed 0–4 of 6 checks (avg ≈ 2); the rest went to a human.", 0.78, 6.12, 5.62, 0.72, { fontSize: 14, color: AMBER, bold: true, valign: "middle", objectName: "Compliance honesty text" });

    T(s, "Executive briefing — the one-page read", 6.78, 1.4, 5.95, 0.4, { fontSize: 20, bold: true, objectName: "Briefing heading" });
    T(s, "Bottom line, key decisions, risks, key numbers and next actions from one click.", 6.78, 1.82, 5.95, 0.62, { fontSize: 14, color: MUTED, objectName: "Briefing subhead" });
    shot(s, "briefing_top.png", 6.85, 2.62, 5.8, "Briefing screenshot", "Executive briefing showing bottom line and key decisions with citations");
    card(s, 6.78, 6.12, 5.95, 0.72, "Briefing honesty chip");
    T(s, "Cited its sources in 6 of 8 runs; otherwise the app says so: “verify before relying”.", 6.96, 6.12, 5.62, 0.72, { fontSize: 14, color: AMBER, bold: true, valign: "middle", objectName: "Briefing honesty text" });
  }
  notes(s, `
Left: the compliance checker runs a standard six-item checklist. The safety design is the point: a PASS must carry a verbatim quote, and the app checks that quote really exists in the document. If the model cannot back a claim, the item is downgraded to REVIEW for a human — it fails safe.
Be upfront about variability: across eight live runs of this check, a 3B local model passed between zero and four of the six items, about two on average, and none came back FAIL; the rest went to human review. Also note a verified quote proves a passage exists, not that it proves the point — a reviewer still decides.
Right: the executive briefing. In six of eight runs it carried source citations; in the other two the app itself printed a warning that the briefing had no citations and should be verified. We fact-checked the briefing shown here against the contract: three-year term, termination for convenience after 18 months, the entire-agreement clause and the signatories are all correct.`);

  // ═════════════ 7 · ENTITIES + TAGGING ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
  T(s, "Structure from prose: entities and a trained tagger", 0, 0, 0, 0, { placeholder: "title" });
  {
    T(s, "Entities & clauses", 0.6, 1.4, 5.95, 0.4, { fontSize: 20, bold: true, objectName: "Entities heading" });
    T(s, "Organisations, people, places, dates and money found by BERT NER plus clause rules.", 0.6, 1.82, 5.95, 0.62, { fontSize: 14, color: MUTED, objectName: "Entities subhead" });
    shot(s, "entities_top.png", 0.67, 2.62, 5.8, "Entities screenshot", "Entity extraction cards for organisations, people, locations and dates");
    card(s, 0.6, 6.12, 5.95, 0.72, "Entities stat chip");
    T(s, "Also found: 6 financial values, 31 obligations, 20 risk clauses.", 0.78, 6.12, 5.62, 0.72, { fontSize: 14, color: CYAN, bold: true, valign: "middle", objectName: "Entities stat text" });

    T(s, "Sentence tagger — our trained ANN, live", 6.78, 1.4, 5.95, 0.4, { fontSize: 20, bold: true, objectName: "Tagging heading" });
    T(s, "Labels all 80 sentences with 7 tags and a confidence; filter by tag, here Financial.", 6.78, 1.82, 5.95, 0.62, { fontSize: 14, color: MUTED, objectName: "Tagging subhead" });
    shot(s, "tagging_top.png", 6.85, 2.62, 5.45, "Tagging screenshot", "Sentences tagged Financial with confidence percentages");
    card(s, 6.78, 6.12, 5.95, 0.72, "Tagging stat chip");
    T(s, "Held-out test: ANN F1 = 0.84 (chance = 0.14).", 6.96, 6.12, 5.62, 0.72, { fontSize: 14, color: CYAN, bold: true, valign: "middle", objectName: "Tagging stat text" });
  }
  notes(s, `
Left: entity extraction pulls organisations, people, places, dates and money out of the same contract, using a BERT named-entity model plus our own clause rules. It also found 31 obligation sentences and 20 risk-clause sentences. It is not perfect — for example 'MS' and 'AAA' appear as organisations — which is why it feeds review rather than replacing it.
Right: the sentence tagger is a neural network we trained ourselves on 280 hand-labelled contract sentences, seven tags. Here it has tagged all 80 sentences in the demo contract and we filter to Financial. On a held-out test set it scored F1 0.84 against a 0.14 chance level; the next section shows the comparison with CNN and LSTM.`);

  // ═════════════ 8 · HOW WE TESTED ═════════════
  pres.addSection({ title: "Evidence" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
  T(s, "How we tested: three hypotheses, 85 questions", 0, 0, 0, 0, { placeholder: "title" });
  {
    const hyp = [
      ["H1", CYAN, "Hybrid search beats keyword-only search", "Blending BM25 with dense vectors finds the gold passage more often."],
      ["H2", VIOLET, "A similarity threshold enables honest refusals", "A relevance cut-off lets the system say “not found” instead of guessing."],
      ["H3", GREEN, "A small neural net can tag contract sentences", "A compact ANN, CNN or LSTM labels 7 sentence types far above chance."],
    ];
    for (let i = 0; i < 3; i++) {
      const y = 1.5 + i * 1.7;
      card(s, 0.6, y, 7.0, 1.5, `Hypothesis ${i + 1}`);
      s.addShape(pres.ShapeType.roundRect, { x: 0.82, y: y + 0.28, w: 0.78, h: 0.78, rectRadius: 0.14, fill: { color: hyp[i][1] }, line: { type: "none" }, objectName: `Hypothesis badge ${i + 1}` });
      T(s, hyp[i][0], 0.82, y + 0.28, 0.78, 0.78, { fontSize: 22, bold: true, color: INK, align: "center", valign: "middle", objectName: `Hypothesis id ${i + 1}` });
      T(s, hyp[i][2], 1.85, y + 0.18, 5.55, 0.45, { fontSize: 20, bold: true, objectName: `Hypothesis title ${i + 1}` });
      T(s, hyp[i][3], 1.85, y + 0.68, 5.55, 0.7, { fontSize: 14, color: MUTED, objectName: `Hypothesis text ${i + 1}` });
    }
    card(s, 7.9, 1.5, 4.83, 4.9, "Setup card");
    T(s, "Evaluation setup", 8.2, 1.7, 4.2, 0.45, { fontSize: 22, bold: true, color: CYAN, objectName: "Setup heading" });
    const stats = [["5", "sector datasets: consulting, finance, healthcare, HR/ops, legal"], ["85", "questions: 63 answerable + 22 unanswerable"], ["280", "hand-labelled contract sentences, 7 tags"], ["3", "metrics: Recall@k, MRR, refusal accuracy"]];
    for (let i = 0; i < 4; i++) {
      const y = 2.35 + i * 1.0;
      T(s, stats[i][0], 8.2, y, 1.1, 0.8, { fontSize: 36, bold: true, color: CYAN, valign: "middle", objectName: `Setup number ${i + 1}` });
      T(s, stats[i][1], 9.35, y, 3.25, 0.8, { fontSize: 14, color: WHITE, valign: "middle", objectName: `Setup label ${i + 1}` });
    }
    T(s, "Gold answer = right document + right page + passage text.", 0.6, 6.62, 12.13, 0.3, { fontSize: 12, color: MUTED, objectName: "Gold definition" });
  }
  notes(s, `
Three hypotheses, each testable. H1: hybrid retrieval beats keyword-only. H2: a similarity threshold lets the system refuse unanswerable questions rather than guess. H3: a small neural network can tag contract sentences well above chance.
The retrieval test uses five labelled sector datasets — 63 answerable and 22 unanswerable questions — where the gold answer is the right document, the right page and the right passage text. The tagger test uses 280 hand-written contract sentences, 40 per tag, split 218 train, 31 validation, 31 test.
All of this is reproducible with the evaluation script in the repository.`);

  // ═════════════ 9 · RESULTS: RETRIEVAL ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
  T(s, "Hybrid search finds the right passage more often", 0, 0, 0, 0, { placeholder: "title" });
  {
    card(s, 0.6, 1.5, 7.6, 5.0, "Retrieval chart card");
    s.addChart(pres.charts.BAR, [
      { name: "Keyword only (BM25)", labels: ["Recall@1", "Recall@3", "Recall@5"], values: [79.4, 92.1, 95.2] },
      { name: "Hybrid (BM25 + vectors)", labels: ["Recall@1", "Recall@3", "Recall@5"], values: [87.3, 96.8, 98.4] },
    ], {
      x: 0.75, y: 1.6, w: 7.3, h: 4.8, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
      chartColors: ["6F84B3", HEX.accent1],
      showTitle: true, title: "Does the right passage surface? (%)", titleColor: HEX.lt1, titleFontSize: 18, titleFontFace: "+mn-lt",
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: HEX.lt1, dataLabelFontSize: 14, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: '0.0"%"',
      catAxisLabelColor: HEX.lt1, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt",
      valAxisLabelColor: HEX.lt2, valAxisLabelFontSize: 12, valAxisLabelFontFace: "+mn-lt", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25,
      valGridLine: { color: "2A3A5E", size: 0.5 }, catGridLine: { style: "none" },
      showLegend: true, legendPos: "b", legendColor: HEX.lt1, legendFontSize: 14, legendFontFace: "+mn-lt",
    });
    const kp = [["98.4%", "Recall@5 with hybrid search", CYAN], ["+7.9 pts", "Recall@1 vs keyword-only", VIOLET], ["0.92", "Mean reciprocal rank (keyword-only: 0.86)", GREEN]];
    for (let i = 0; i < 3; i++) {
      const y = 1.5 + i * 1.7;
      card(s, 8.5, y, 4.23, 1.5, `Stat card ${i + 1}`);
      T(s, kp[i][0], 8.75, y + 0.12, 3.75, 0.8, { fontSize: 40, bold: true, color: kp[i][2], valign: "middle", objectName: `Stat number ${i + 1}` });
      T(s, kp[i][1], 8.75, y + 0.9, 3.75, 0.5, { fontSize: 14, color: MUTED, objectName: `Stat label ${i + 1}` });
    }
    T(s, "63 answerable questions · 5 sectors · hybrid better on Recall@1 in 3 sectors, never worse on any measure.", 0.6, 6.62, 12.13, 0.3, { fontSize: 12, color: MUTED, objectName: "Retrieval footnote" });
  }
  notes(s, `
H1 supported. Across 63 answerable questions in five sectors, hybrid retrieval beat keyword-only on every recall measure: Recall@1 went from 79.4 to 87.3 percent, Recall@3 from 92.1 to 96.8, Recall@5 from 95.2 to 98.4. Mean reciprocal rank rose from 0.862 to 0.919.
It was better on three of the five sectors and never worse on any — consulting, healthcare and legal improved; finance was unchanged and HR/ops was already at 100 percent for Recall@1.
Be honest about scale: 63 questions is a solid sanity check, not a benchmark; the next step is a larger, blind set.`);

  // ═════════════ 10 · RESULTS: REFUSAL + TAGGER ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
  T(s, "Honest refusals and a clear model winner", 0, 0, 0, 0, { placeholder: "title" });
  {
    card(s, 0.6, 1.5, 5.95, 4.3, "Refusal chart card");
    s.addChart(pres.charts.BAR, [{ name: "Refusal accuracy (%)", labels: ["Keyword-only", "Hybrid, default", "Hybrid, tuned"], values: [54.5, 75.5, 95.4] }], {
      x: 0.7, y: 1.55, w: 5.75, h: 4.2, barDir: "col", barGapWidthPct: 50,
      chartColors: ["6F84B3", HEX.accent3, HEX.accent1],
      showTitle: true, title: "Answers when it can, refuses when it can't (%)", titleColor: HEX.lt1, titleFontSize: 16, titleFontFace: "+mn-lt",
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: HEX.lt1, dataLabelFontSize: 14, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: '0.0"%"',
      catAxisLabelColor: HEX.lt1, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt",
      valAxisLabelColor: HEX.lt2, valAxisLabelFontSize: 12, valAxisLabelFontFace: "+mn-lt", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25,
      valGridLine: { color: "2A3A5E", size: 0.5 }, catGridLine: { style: "none" }, showLegend: false,
    });
    T(s, "Similarity scores — not keyword scores — make “not found” possible. Tuned on the same data, so optimistic.", 0.7, 5.95, 5.75, 0.9, { fontSize: 16, objectName: "Refusal takeaway" });

    card(s, 6.78, 1.5, 5.95, 4.3, "Tagger chart card");
    s.addChart(pres.charts.BAR, [
      { name: "Accuracy", labels: ["ANN", "CNN", "LSTM"], values: [83.9, 77.4, 48.4] },
      { name: "F1 score", labels: ["ANN", "CNN", "LSTM"], values: [84.1, 76.6, 48.7] },
    ], {
      x: 6.88, y: 1.55, w: 5.75, h: 4.2, barDir: "col", barGrouping: "clustered", barGapWidthPct: 50,
      chartColors: ["8EA0C8", HEX.accent1],
      showTitle: true, title: "Sentence tagger on the held-out test (%)", titleColor: HEX.lt1, titleFontSize: 16, titleFontFace: "+mn-lt",
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: HEX.lt1, dataLabelFontSize: 14, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: '0.0"%"',
      catAxisLabelColor: HEX.lt1, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt",
      valAxisLabelColor: HEX.lt2, valAxisLabelFontSize: 12, valAxisLabelFontFace: "+mn-lt", valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25,
      valGridLine: { color: "2A3A5E", size: 0.5 }, catGridLine: { style: "none" },
      showLegend: true, legendPos: "b", legendColor: HEX.lt1, legendFontSize: 14, legendFontFace: "+mn-lt",
    });
    T(s, "The ANN wins; chance is 14.3 %. An LSTM needs sequences — a sentence embedding isn't one.", 6.88, 5.95, 5.75, 0.9, { fontSize: 16, objectName: "Tagger takeaway" });
  }
  notes(s, `
H2 supported, with a caveat. Refusal accuracy means: answer the answerable questions and refuse the unanswerable ones. Keyword scores alone managed 54.5 percent — they can't tell a good match from a bad one. Hybrid scoring at the best threshold reached 95.4 percent, but at the default threshold of 0.30 only 75.5 percent. The 95.4 was tuned on the same data, so treat it as optimistic and the default as needing work.
H3 supported. On the 31-sentence held-out test the ANN scored 83.9 percent accuracy and 0.84 F1, the CNN about 77, and the LSTM only 48 — still well above the 14.3 percent chance level. The LSTM trails because we are feeding it a single sentence embedding reshaped into a fake sequence; there is no temporal structure for it to use. A simple feed-forward network is the right tool.
Mention the 31-sentence test set is small.`);

  // ═════════════ 11 · LIMITS ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
  T(s, "What we learned — and what we won't overclaim", 0, 0, 0, 0, { placeholder: "title" });
  {
    const L = [
      ["FiBarChart2", CYAN, "Small test sets", "85 questions and a 31-sentence tagger test: good evidence, not proof."],
      ["FiSliders", VIOLET, "Optimistic thresholds", "Refusal thresholds were tuned on the same data; a blind set is next."],
      ["FiCpu", AMBER, "A cautious 3B local model", "In 8 live compliance runs it passed 0–4 of 6; the rest went to human review."],
      ["FiCheckSquare", ROSE, "Verified ≠ proven", "A checked quote proves a passage exists, not that it proves the claim."],
      ["FiTool", GREEN, "A bug our tests missed", "A model-blind cache crashed search on real embeddings — found live, fixed, regression-tested."],
      ["FiServer", BLUE, "Single-tenant today", "One deployment per organisation; multi-tenancy and SSO are next."],
    ];
    for (let i = 0; i < 6; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.6 + col * 6.18, y = 1.5 + row * 1.8;
      card(s, x, y, 5.95, 1.62, `Limit card ${i + 1}`);
      await iconCircle(s, L[i][0], x + 0.7, y + 0.81, 0.78, L[i][1], `Limit icon ${i + 1}`);
      T(s, L[i][2], x + 1.4, y + 0.2, 4.35, 0.4, { fontSize: 19, bold: true, objectName: `Limit title ${i + 1}` });
      T(s, L[i][3], x + 1.4, y + 0.64, 4.35, 0.9, { fontSize: 14, color: MUTED, objectName: `Limit text ${i + 1}` });
    }
  }
  notes(s, `
This slide is deliberate: we would rather tell you the limits than have you find them.
Small test sets. Thresholds tuned on the data they were measured on. A 3B local model that is cautious — in eight live compliance runs it passed between zero and four of six checks and sent the rest to review. And a verified quote proves a passage exists, not that it supports the claim, so a human still decides.
The bug story shows the engineering discipline: when we ran real embeddings end to end, a disk cache keyed only on text — not on the model — returned wrong-dimension vectors and crashed search. Unit tests had mocked the embedder, so they never saw it. We found it live, fixed the cache key, and added regression tests.
Last, it is single-tenant today: one deployment per organisation. SSO and multi-tenancy are on the roadmap.`);

  // ═════════════ 12 · TRUST ═════════════
  pres.addSection({ title: "Beyond the model" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Beyond the model" });
  T(s, "Built to be trusted, not just to demo", 0, 0, 0, 0, { placeholder: "title" });
  {
    const a = shot(s, "audit_stack.png", 0.67, 1.5, 7.0, "Audit log screenshot", "Audit log: chain intact, 27 entries, with compliance run outcomes");
    card(s, 0.6, 4.25, 7.14, 2.4, "Audit explainer card");
    T(s, "What the audit log shows", 0.9, 4.4, 6.5, 0.4, { fontSize: 18, bold: true, color: CYAN, objectName: "Audit heading" });
    T(s, [
      { text: "Every action: who, what, when — metadata only, never document text.", options: { bullet: true, breakLine: true } },
      { text: "A hash chain flags any edit to history (“27 entries, intact”).", options: { bullet: true, breakLine: true } },
      { text: "It even records each compliance run's outcome — PASS 3, 2, 4, 1, 2.", options: { bullet: true } },
    ], 0.9, 4.85, 6.6, 1.7, { fontSize: 16, paraSpaceAfter: 8, objectName: "Audit bullets" });
    const rows = [
      ["FiLock", CYAN, "Hash-chained audit log", "Tamper-evident, metadata only"],
      ["FiUsers", BLUE, "Roles and API keys", "Viewer, analyst, admin; bearer-token API"],
      ["FiDatabase", VIOLET, "Postgres + migrations", "Alembic-managed schema changes"],
      ["FiCreditCard", AMBER, "Stripe billing", "Free, Pro, Enterprise with seat limits"],
      ["FiCheckCircle", GREEN, "163 automated tests", "CI on every push: lint, types, scan, Docker"],
    ];
    for (let i = 0; i < 5; i++) {
      const y = 1.5 + i * 1.02;
      card(s, 8.0, y, 4.73, 0.9, `Trust row ${i + 1}`);
      await iconCircle(s, rows[i][0], 8.5, y + 0.45, 0.56, rows[i][1], `Trust icon ${i + 1}`);
      T(s, rows[i][2], 8.95, y + 0.09, 3.7, 0.38, { fontSize: 16, bold: true, objectName: `Trust title ${i + 1}` });
      T(s, rows[i][3], 8.95, y + 0.47, 3.7, 0.36, { fontSize: 14, color: MUTED, objectName: `Trust text ${i + 1}` });
    }
  }
  notes(s, `
Judges often ask whether this is a demo or something you could run for a team. This slide is the answer.
The screenshot is the real audit log: 27 entries, chain intact. Each entry records who did what and when — metadata only, never document text. A hash chain means any edit to history is detected. Notice it even records the outcome of every compliance run, which is how we measured the run-to-run variability we reported.
On the right: role-based access and API keys, a Postgres database with managed migrations, Stripe billing with seat limits, and 163 automated tests, with continuous integration on every push — lint, type checks, a secret and dependency scan, and a Docker build. (Seven torch-based tests run locally rather than in CI.)`);

  // ═════════════ 13 · COMPARISON ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Beyond the model" });
  T(s, "How Lexi AI compares", 0, 0, 0, 0, { placeholder: "title" });
  {
    const Y = { text: "✓", options: { color: HEX.accent4, bold: true, fontSize: 18 } };
    const M = { text: "◐", options: { color: HEX.accent5, bold: true, fontSize: 18 } };
    const X = { text: "✗", options: { color: HEX.accent6, bold: true, fontSize: 18 } };
    const cell = (mark, label, us = false) => ({ text: [Object.assign({}, mark, { text: mark.text + "  " }), { text: label, options: { color: HEX.lt1, fontSize: 14 } }], options: us ? { fill: { color: "12304F" } } : {} });
    const hdr = (t, us = false) => ({ text: t, options: { bold: true, color: us ? HEX.accent1 : HEX.lt2, fontSize: 14, fill: { color: us ? "12304F" : HEX.dk2 } } });
    const rows = [
      [hdr("What matters"), hdr("Reading it yourself"), hdr("General cloud chatbot"), hdr("Lexi AI", true)],
      [{ text: "Searches a whole document set", options: { bold: true } }, cell(M, "Slow and tiring"), cell(M, "Limited by paste size"), cell(Y, "Hybrid search, every page", true)],
      [{ text: "Cites document + page", options: { bold: true } }, cell(Y, "By hand"), cell(X, "Rarely verifiable"), cell(Y, "Numbered, page, relevance", true)],
      [{ text: "Says “not found”, not a guess", options: { bold: true } }, cell(Y, "Human judgement"), cell(M, "Often answers anyway"), cell(Y, "Similarity threshold", true)],
      [{ text: "Documents stay on your machine", options: { bold: true } }, cell(Y, "Yes"), cell(X, "Sent to a provider"), cell(Y, "Local LLM, zero-retention", true)],
      [{ text: "Tamper-evident audit trail", options: { bold: true } }, cell(X, "Manual notes"), cell(X, "Not by default"), cell(Y, "Hash-chained log", true)],
      [{ text: "Repeatable compliance checklist", options: { bold: true } }, cell(M, "Checklists by hand"), cell(M, "Ad-hoc prompts"), cell(Y, "PASS / REVIEW + quotes", true)],
      [{ text: "Team roles, API and billing", options: { bold: true } }, cell(X, "—"), cell(M, "Account-level only"), cell(Y, "Roles, keys, seat plans", true)],
    ];
    s.addTable(rows, {
      x: 0.6, y: 1.5, w: 12.13, colW: [3.6, 2.6, 2.9, 3.03], rowH: 0.56, fontSize: 14, color: HEX.lt1, fontFace: "Calibri",
      border: { type: "solid", pt: 0.5, color: "2A3A5E" }, fill: { color: HEX.dk1 }, valign: "middle", margin: [0.04, 0.12, 0.04, 0.12],
    });
    T(s, "✓ yes   ◐ partly   ✗ no   ·   A qualitative comparison of approaches in general — not a benchmark of any named product.", 0.6, 6.15, 12.13, 0.35, { fontSize: 12, color: MUTED, objectName: "Comparison footnote" });
  }
  notes(s, `
Compare approaches, not products: reading it yourself, pasting into a general cloud chatbot, and Lexi AI.
Walk the Lexi column: hybrid search over every page; numbered citations with page and relevance; a threshold that lets it refuse; documents stay local; a hash-chained audit log; a repeatable compliance checklist; roles, API keys and seat-based plans.
Be fair about the other columns — reading it yourself is excellent at judgement and citing, just slow. And say plainly this is a qualitative comparison, not a benchmark of any named product.`);

  // ═════════════ 14 · ROADMAP ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Beyond the model" });
  T(s, "Where Lexi AI goes next", 0, 0, 0, 0, { placeholder: "title" });
  {
    const R = [
      ["Shipped", GREEN, ["Cited Q&A and hybrid search", "Briefings and compliance checks", "Entities, actions, ANN tagging", "Roles, audit log, billing"]],
      ["Next", CYAN, ["Single sign-on (SSO)", "Multi-tenancy for many organisations", "Blind, larger evaluation"]],
      ["Later", VIOLET, ["Hosted deployment pipeline", "Monitoring and alerting", "Optional hosted-LLM tier"]],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.6 + i * 4.09;
      card(s, x, 1.5, 3.95, 3.65, `Roadmap card ${i + 1}`);
      chip(s, R[i][0].toUpperCase(), x + 0.3, 1.78, 1.45, R[i][1], `Roadmap chip ${i + 1}`, 0.42);
      T(s, R[i][2].map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < R[i][2].length - 1 } })), x + 0.3, 2.45, 3.4, 2.6, { fontSize: 18, paraSpaceAfter: 10, objectName: `Roadmap list ${i + 1}` });
    }
    card(s, 0.6, 5.45, 12.13, 1.2, "Decision banner");
    await iconCircle(s, "FiTarget", 1.4, 6.05, 0.7, AMBER, "Decision icon");
    T(s, [{ text: "Key product decision: ", options: { bold: true, color: AMBER } }, { text: "self-hosted per customer vs shared multi-tenant SaaS — it shapes billing, sign-in and data isolation.", options: { color: WHITE } }],
      2.05, 5.45, 10.4, 1.2, { fontSize: 18, valign: "middle", objectName: "Decision text" });
  }
  notes(s, `
What is shipped is on the left. Next: single sign-on, because enterprise buyers usually require it; multi-tenancy; and a larger blind evaluation to firm up the numbers. Later: a hosted deployment pipeline, monitoring, and an optional hosted-LLM tier for customers who prefer it to running their own model.
The amber banner is a real open question we are weighing: sell it as a self-hosted product per customer, or run one shared multi-tenant service. Our billing is per-deployment today, which suits the first model; the second would need multi-tenancy first. We would welcome the judges' view.`);

  // ═════════════ 15 · TEAM ═════════════
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Close" });
  T(s, "The team behind Lexi AI", 0, 0, 0, 0, { placeholder: "title" });
  {
    const team = [
      ["vidushi", "Vidushi Bhadauria", "Project lead · Full-stack", "Web app, API, database, billing, CI", CYAN],
      ["aryama", "Aryama Sharma", "NLP & retrieval", "Pre-processing, embeddings, hybrid search", BLUE],
      ["ashi", "Ashi Srivastava", "GenAI & extraction", "LLM prompts, citations, NER", VIOLET],
      ["parth", "Parth Nawal", "ML · classification", "Labelled dataset, ANN / CNN / LSTM", AMBER],
      ["simran", "Simran Karan Bora", "UX, data & quality", "UI, test sets, testing, docs", GREEN],
    ];
    const w = 2.3, gap = 0.1575;
    for (let i = 0; i < 5; i++) {
      const x = 0.6 + i * (w + gap);
      card(s, x, 1.5, w, 5.05, `Team card ${i + 1}`);
      s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 1.7, w: 1.7, h: 1.7, fill: { color: team[i][4] }, line: { type: "none" }, objectName: `Photo ring ${i + 1}` });
      s.addImage({ path: path.join(ASSETS, "photos", team[i][0] + ".jpg"), x: x + 0.37, y: 1.77, w: 1.56, h: 1.56, rounding: true, objectName: `Photo ${team[i][1]}`, altText: `Photo of ${team[i][1]}` });
      T(s, team[i][1], x + 0.1, 3.6, w - 0.2, 0.7, { fontSize: 18, bold: true, align: "center", valign: "middle", objectName: `Team name ${i + 1}` });
      T(s, team[i][2], x + 0.1, 4.3, w - 0.2, 0.62, { fontSize: 14, bold: true, color: team[i][4], align: "center", valign: "top", objectName: `Team role ${i + 1}` });
      T(s, team[i][3], x + 0.2, 5.0, w - 0.4, 1.45, { fontSize: 16, color: MUTED, objectName: `Team focus ${i + 1}` });
    }
  }
  notes(s, `
Introduce each person with one phrase of what they owned. [Presenter: confirm the roles on this slide match who actually did what — they were drafted from the project's modules and should be corrected before presenting.]
Vidushi — project lead and full-stack: the web app, API, database, billing and CI. Aryama — natural-language processing and retrieval: pre-processing, embeddings and hybrid search. Ashi — generative AI and extraction: the LLM prompts, citations and entity extraction. Parth — machine learning: the labelled dataset and the ANN, CNN and LSTM comparison. Simran — UX, data and quality: the interface, the sector test sets and the testing and documentation.`);

  // ═════════════ 16 · CLOSING ═════════════
  s = pres.addSlide({ masterName: "TITLE_SLIDE", sectionTitle: "Close" });
  {
    T(s, [{ text: "Ask your documents. ", options: { color: WHITE } }, { text: "Trust the answer.", options: { color: CYAN } }], 0.8, 0.95, 11.7, 1.2, { fontSize: 50, bold: true, valign: "middle", objectName: "Closing headline" });
    const tk = [
      ["98.4%", "Recall@5 with hybrid retrieval — better Recall@1 than keyword search in 3 of 5 sectors, never worse on any measure", CYAN],
      ["Cited", "Every answer lists numbered sources, shows its confidence and flags what needs a human", VIOLET],
      ["Honest", "We report the limits — run-to-run variance, small test sets — along with the wins", GREEN],
    ];
    for (let i = 0; i < 3; i++) {
      const x = 0.8 + i * 4.0;
      card(s, x, 2.6, 3.8, 2.7, `Takeaway card ${i + 1}`);
      T(s, tk[i][0], x + 0.3, 2.8, 3.2, 0.9, { fontSize: 40, bold: true, color: tk[i][2], valign: "middle", objectName: `Takeaway title ${i + 1}` });
      T(s, tk[i][1], x + 0.3, 3.75, 3.2, 1.45, { fontSize: 16, color: WHITE, objectName: `Takeaway text ${i + 1}` });
    }
    T(s, "Thank you — questions welcome", 0.8, 5.65, 11.7, 0.8, { fontSize: 36, bold: true, valign: "middle", objectName: "Thank you" });
    T(s, "Vidushi Bhadauria  ·  Parth Nawal  ·  Aryama Sharma  ·  Ashi Srivastava  ·  Simran Karan Bora", 0.8, 6.55, 11.7, 0.4, { fontSize: 16, color: MUTED, objectName: "Closing team names" });
  }
  notes(s, `
Close on three things. It works where we measured it: 98.4 percent Recall@5 and hybrid retrieval that is never worse than keyword search. It is built to be checked: numbered citations, shown confidence and a human-review lane. And we are honest about limits.
Then stop talking and take questions — the appendix has likely questions and the references.`);

  // ═════════════ A1 · LIKELY QUESTIONS ═════════════
  pres.addSection({ title: "Appendix" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
  T(s, "Questions you may hear", 0, 0, 0, 0, { placeholder: "title" });
  {
    const Q = [
      ["Why a local LLM instead of a cloud API?", "Privacy and control: documents never leave the machine. The trade-off is a smaller, more cautious model — a hosted tier is on the roadmap."],
      ["How do you limit hallucination?", "Answer only from retrieved passages, numbered citations, verbatim-quote checks, a refusal threshold and a human-review lane. Limited, not eliminated."],
      ["How big was the evaluation?", "85 questions across 5 sectors and 280 labelled sentences. Small and partly tuned on itself; a blind, larger set is next."],
      ["Why did the ANN beat the LSTM?", "A sentence embedding has no time axis for an LSTM to exploit; a simple feed-forward net fits the data. Chance is 14.3 %, ANN scored 84 %."],
      ["Is it production-ready?", "Strong base: roles, audit log, migrations, billing, 163 tests with CI on every push. Not yet: SSO, multi-tenancy, hosted deployment and monitoring."],
      ["How is user data protected?", "Processed locally; the audit log stores metadata only; an optional zero-retention mode keeps state in memory (single-worker)."],
    ];
    for (let i = 0; i < 6; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 0.6 + col * 6.18, y = 1.5 + row * 1.8;
      card(s, x, y, 5.95, 1.65, `Question card ${i + 1}`);
      T(s, Q[i][0], x + 0.25, y + 0.14, 5.45, 0.4, { fontSize: 16, bold: true, color: CYAN, objectName: `Question ${i + 1}` });
      T(s, Q[i][1], x + 0.25, y + 0.56, 5.45, 1.05, { fontSize: 15, objectName: `Answer ${i + 1}` });
    }
  }
  notes(s, `Backup slide — use only if asked. Each answer is a short, honest summary of the corresponding point from the main deck.`);

  // ═════════════ A2 · REFERENCES ═════════════
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Appendix" });
  T(s, "References", 0, 0, 0, 0, { placeholder: "title" });
  {
    const refs = [
      "[1] Robertson, S. & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. Foundations and Trends in Information Retrieval, 3(4), 333–389.",
      "[2] Johnson, J., Douze, M. & Jégou, H. (2021). Billion-scale similarity search with GPUs. IEEE Transactions on Big Data, 7(3), 535–547.",
      "[3] Reimers, N. & Gurevych, I. (2019). Sentence-BERT: sentence embeddings using Siamese BERT-networks. EMNLP-IJCNLP.",
      "[4] Wang, W. et al. (2020). MiniLM: deep self-attention distillation for task-agnostic compression of pre-trained transformers. NeurIPS.",
      "[5] Lewis, P. et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS.",
      "[6] Devlin, J. et al. (2019). BERT: pre-training of deep bidirectional transformers for language understanding. NAACL-HLT.",
      "[7] Tjong Kim Sang, E. & De Meulder, F. (2003). Introduction to the CoNLL-2003 shared task: language-independent named entity recognition. CoNLL.",
      "[8] Hochreiter, S. & Schmidhuber, J. (1997). Long short-term memory. Neural Computation, 9(8), 1735–1780.",
      "[9] Dubey, A. et al. (2024). The Llama 3 herd of models. arXiv:2407.21783.",
      "[10] Bird, S., Klein, E. & Loper, E. (2009). Natural Language Processing with Python. O'Reilly Media.",
    ];
    card(s, 0.6, 1.5, 6.0, 5.1, "References card left");
    card(s, 6.73, 1.5, 6.0, 5.1, "References card right");
    T(s, refs.slice(0, 5).map((t, k) => ({ text: t, options: { breakLine: k < 4 } })), 0.85, 1.7, 5.5, 4.7, { fontSize: 14, color: WHITE, paraSpaceAfter: 12, objectName: "References left" });
    T(s, refs.slice(5).map((t, k) => ({ text: t, options: { breakLine: k < 4 } })), 6.98, 1.7, 5.5, 4.7, { fontSize: 14, color: WHITE, paraSpaceAfter: 12, objectName: "References right" });
  }
  notes(s, `Backup slide. Retrieval and indexing: [1] BM25, [2] FAISS, [3][4] sentence embeddings. Generation and extraction: [5] retrieval-augmented generation, [6][7] BERT and the CoNLL-2003 NER benchmark, [9] Llama 3. Models and tooling: [8] LSTM, [10] NLTK.`);

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("built", OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });
