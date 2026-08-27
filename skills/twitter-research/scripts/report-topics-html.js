// =============================================================================
// Twitter/X Research — Topics Mode HTML Report Generator
// Renders REPORT.html from the topic-research-*.md files produced by Topics Mode.
// Usage: node scripts/report-topics-html.js [sessionId] [outputName] [--session <id>] [--data-root <path>] [--output <name>]
//   If sessionId given, reads from .twitter-research/<sessionId>/; else from .twitter-research/ root (legacy fallback).
//   Bundled inside skill: resolves dataRoot via CWD walk-up, env, or --data-root.
// =============================================================================

import { readFileSync, writeFileSync, readdirSync, existsSync } from 'fs';
import { join, basename, dirname, resolve } from 'path';

function resolveDataRoot(dotName = '.twitter-research') {
  const envKey = dotName.replace(/^\./, '').replace(/-/g, '_').toUpperCase() + '_ROOT';
  if (process.env[envKey]) return resolve(process.env[envKey]);
  if (process.env.TWITTER_RESEARCH_ROOT) return resolve(process.env.TWITTER_RESEARCH_ROOT);
  let dir = process.cwd();
  while (true) {
    if (existsSync(join(dir, dotName))) return join(dir, dotName);
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return join(process.cwd(), dotName);
}

function parseArgs() {
  const raw = process.argv.slice(2);
  let session = null, outputName = 'REPORT.html', dataRoot = null;
  const tsRe = /^\d{4}-\d{2}-\d{2}_\d{6}$/;
  for (let i = 0; i < raw.length; i++) {
    const a = raw[i];
    if (a === '--session' && raw[i+1]) { session = raw[++i]; continue; }
    if (a.startsWith('--session=')) { session = a.split('=')[1]; continue; }
    if (a === '--data-root' && raw[i+1]) { dataRoot = resolve(raw[++i]); continue; }
    if (a.startsWith('--data-root=')) { dataRoot = resolve(a.split('=')[1]); continue; }
    if (a === '--output' && raw[i+1]) { outputName = raw[++i]; continue; }
    if (a.startsWith('--output=')) { outputName = a.split('=')[1]; continue; }
    if (a.startsWith('--')) continue;
    if (!session && tsRe.test(a)) session = a;
    else if (outputName === 'REPORT.html' && !tsRe.test(a) && !a.includes('/')) {
      // could be output name without session
      if (!session) {
        // if we haven't seen a session yet, treat first non-ts as outputName only if no session follows
        // heuristic: if next arg is ts, this is session; else output
        const next = raw[i+1];
        if (next && tsRe.test(next)) { session = a; } else { outputName = a; }
      } else outputName = a;
    } else if (!session) session = a;
  }
  return { session, outputName, dataRoot: dataRoot || resolveDataRoot() };
}

const { session, outputName, dataRoot } = parseArgs();
const root = session ? join(dataRoot, session) : dataRoot;
const fallbackRoot = dataRoot;

const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function hotnessToEmoji(n) {
  const m = (n || '').match(/🔥/g);
  return m ? m.length : 0;
}

function mdToHtml(src) {
  let html = '';
  for (const rawLine of src.split('\n')) {
    let line = rawLine;
    if (line.startsWith('> ')) {
      const content = inline(line.slice(2));
      html += `<blockquote>${content}</blockquote>`;
    } else if (line.startsWith('### ')) {
      html += `<h4>${inline(line.slice(4))}</h4>`;
    } else if (line.startsWith('## ')) {
      html += `<h3>${inline(line.slice(3))}</h3>`;
    } else if (line.startsWith('# ')) {
      html += `<h2>${inline(line.slice(2))}</h2>`;
    } else if (line.startsWith('- ')) {
      html += `<li>${inline(line.slice(2))}</li>`;
    } else if (line.trim() === '') {
      html += '';
    } else {
      html += `<p>${inline(line)}</p>`;
    }
  }
  return html;
}

function inline(s) {
  let t = esc(s);
  t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1 ↗</a>');
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  return t;
}

function listMdFiles(dir) {
  try { return readdirSync(dir).filter(f => /^topic-research-.*\.md$/.test(f)).sort(); } catch { return []; }
}

let mdFiles = listMdFiles(root);
let effectiveRoot = root;
if (mdFiles.length === 0 && session) {
  const fb = listMdFiles(fallbackRoot);
  if (fb.length) { mdFiles = fb; effectiveRoot = fallbackRoot; }
}

if (mdFiles.length === 0) {
  console.error('No topic-research-*.md files found in ' + root + (session ? ' nor ' + fallbackRoot : ''));
  process.exit(1);
}

const reportPath = join(effectiveRoot, 'topics-report.md');
const fallbackReport = join(fallbackRoot, 'topics-report.md');
const reportMd = existsSync(reportPath) ? readFileSync(reportPath, 'utf8') : (existsSync(fallbackReport) ? readFileSync(fallbackReport, 'utf8') : '');

const topicsHtml = mdFiles.map(file => {
  const md = readFileSync(join(effectiveRoot, file), 'utf8');
  const lines = md.split('\n');
  const titleLine = lines.find(l => l.startsWith('# ')) || '# Sin título';
  const title = titleLine.slice(2);
  const hot = lines.find(l => l.startsWith('**Nivel de calor')) || '';
  const heat = hotnessToEmoji(hot.match(/\u{1F525}+/u)?.[0] || '');
  const flame = '🔥'.repeat(heat || 1);
  return `<section class="topic-card">
    <div class="topic-head">
      <div>
        <h2>${esc(title)}</h2>
        <div class="heat">${flame} <span>${esc(hot.replace(/\*\*/g, '').replace('Nivel de calor (hotness):', '').trim())}</span></div>
      </div>
      <span class="file-tag">${esc(file)}</span>
    </div>
    <div class="topic-body">${mdToHtml(md.split('\n').slice(1).join('\n'))}</div>
  </section>`;
}).join('\n');

const html = `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Topics Report — twitter-research</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1419; color: #e7e9ea; line-height: 1.6; }
  .container { max-width: 960px; margin: 0 auto; padding: 20px; }
  h1 { font-size: 2rem; color: #fff; margin-bottom: 6px; }
  h2 { font-size: 1.4rem; color: #fff; }
  h3 { font-size: 1.05rem; color: #1d9bf0; margin: 18px 0 8px; }
  h4 { font-size: 0.92rem; color: #ffd700; margin: 12px 0 6px; text-transform: uppercase; letter-spacing: 0.04em; }
  .meta { color: #71767b; font-size: 0.9rem; margin-bottom: 20px; }
  .topic-card { background: #1a1f2e; border: 1px solid #2f3336; border-radius: 14px; padding: 22px; margin-bottom: 22px; }
  .topic-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 14px; border-bottom: 1px solid #2f3336; padding-bottom: 14px; }
  .heat { margin-top: 6px; color: #ffd700; font-size: 0.9rem; }
  .heat span { color: #71767b; }
  .file-tag { font-size: 0.72rem; color: #71767b; background: #0f1419; border: 1px solid #2f3336; padding: 4px 10px; border-radius: 999px; white-space: nowrap; }
  .topic-body p { margin-bottom: 8px; }
  .topic-body li { margin-left: 20px; margin-bottom: 4px; }
  .topic-body a { color: #1d9bf0; text-decoration: none; word-break: break-all; }
  .topic-body a:hover { text-decoration: underline; }
  .topic-body blockquote { background: #162d3f; border-left: 3px solid #1d9bf0; border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 6px 0; white-space: pre-line; font-style: italic; }
  .summary-table { width: 100%; border-collapse: collapse; margin: 12px 0 24px; background: #1a1f2e; border-radius: 10px; overflow: hidden; }
  .summary-table th, .summary-table td { text-align: left; padding: 10px 14px; border-bottom: 1px solid #2f3336; }
  .summary-table th { background: #162d3f; color: #fff; font-size: 0.85rem; text-transform: uppercase; }
  .summary-table a { color: #1d9bf0; text-decoration: none; }
  .footer { text-align: center; color: #71767b; padding: 30px 0; font-size: 0.85rem; }
  @media (max-width: 600px) { .container { padding: 12px; } .topic-head { flex-direction: column; } }
</style>
</head>
<body>
<div class="container">
  <h1>⚽ Twitter/X Topics Report</h1>
  <p class="meta">Categoría: <strong>futbol mexico</strong> · Audiencia: <strong>Mexicanos en USA</strong> · Temas: ${mdFiles.length} · Generado: ${new Date().toLocaleString('es-MX')} · Sesión: ${esc(session || 'root')}</p>

  ${reportMd ? `<h2>📋 Resumen de temas</h2>` + renderSummary(reportMd) : ''}
  ${topicsHtml}

  <div class="footer">Generated by twitter-research · topics mode · ${esc(effectiveRoot)}</div>
</div>
</body>
</html>`;

function renderSummary(md) {
  const rows = [];
  for (const line of md.split('\n')) {
    const m = line.match(/^\|\s*(\d+)\s*\|(.+?)\s*\|\s*(\u{1F525}+)\s*\|.*?(topic-research-[a-z0-9-]+\.md)\s*\|/u);
    if (m) {
      rows.push(`<tr><td>${m[1]}</td><td>${inline(m[2])}</td><td>${m[3]}</td><td><a href="${m[4]}">${m[4]}</a></td></tr>`);
    }
  }
  return rows.length ? `<table class="summary-table"><thead><tr><th>#</th><th>Tema</th><th>Calor</th><th>Archivo</th></tr></thead><tbody>${rows.join('')}</tbody></table>` : '';
}

writeFileSync(join(effectiveRoot, outputName), html);
console.log(`Report generated: ${join(effectiveRoot, outputName)} (session: ${effectiveRoot})`);
