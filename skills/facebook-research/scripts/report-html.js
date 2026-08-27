import { readFileSync, writeFileSync, existsSync, readdirSync } from 'fs';
import { join, dirname, resolve } from 'path';

function resolveDataRoot(dotName = '.fb-research') {
  const envKey = dotName.replace(/^\./, '').replace(/-/g, '_').toUpperCase() + '_ROOT';
  if (process.env[envKey]) return resolve(process.env[envKey]);
  if (process.env.FB_RESEARCH_ROOT) return resolve(process.env.FB_RESEARCH_ROOT);
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
  let projectName = null, sessionId = null, dataRoot = null;
  for (let i = 0; i < raw.length; i++) {
    const a = raw[i];
    if (a === '--session' && raw[i+1]) { sessionId = raw[++i]; continue; }
    if (a.startsWith('--session=')) { sessionId = a.split('=')[1]; continue; }
    if (a === '--data-root' && raw[i+1]) { dataRoot = resolve(raw[++i]); continue; }
    if (a.startsWith('--data-root=')) { dataRoot = resolve(a.split('=')[1]); continue; }
    if (a.startsWith('--')) continue;
    if (!projectName) projectName = a;
    else if (!sessionId) sessionId = a;
  }
  return { projectName, sessionId, dataRoot: dataRoot || resolveDataRoot() };
}

const { projectName, sessionId, dataRoot } = parseArgs();
if (!projectName) { console.error('Usage: node scripts/report-html.js <project-name> [sessionId] [--session <id>] [--data-root <path>]'); process.exit(1); }

const projectDir = join(dataRoot, 'projects', projectName);
let sessionDir = null;
if (sessionId) {
  sessionDir = join(projectDir, sessionId);
} else {
  // auto-detect latest session if exists
  try {
    const latestFile = join(projectDir, 'latest.json');
    if (existsSync(latestFile)) {
      const latest = JSON.parse(readFileSync(latestFile, 'utf8'));
      if (latest.sessionId && existsSync(join(projectDir, latest.sessionId))) sessionDir = join(projectDir, latest.sessionId);
    }
    if (!sessionDir) {
      const entries = readdirSync(projectDir, { withFileTypes: true }).filter(d => d.isDirectory() && /^\d{4}-\d{2}-\d{2}_\d{6}$/.test(d.name)).map(d => d.name).sort();
      if (entries.length) sessionDir = join(projectDir, entries[entries.length - 1]);
    }
  } catch {}
}

function pickFile(filename) {
  if (sessionDir && existsSync(join(sessionDir, filename))) return join(sessionDir, filename);
  return join(projectDir, filename);
}

const read = (p, f = '') => existsSync(p) ? readFileSync(p, 'utf8') : f;
const readJson = (p, f = null) => existsSync(p) ? JSON.parse(readFileSync(p, 'utf8')) : f;

const config = readJson(join(projectDir, 'config.json')) || {};
const analytics = readJson(pickFile('page-analytics.json')) || {};
const history = readJson(join(projectDir, 'page-analytics-history.json')) || { snapshots: [] };
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const effectiveDir = sessionDir && existsSync(sessionDir) ? sessionDir : projectDir;
const top5 = (analytics.top5 || []).map((p, i) => `
  <div class="card">
    <div class="card-head"><span class="rank">#${i + 1}</span><span class="author">${esc(p.title || 'Post')}</span></div>
    <div class="stats">views ${esc(p.views || 0)} | likes ${esc(p.likes || 0)} | comments ${esc(p.comments || 0)}</div>
    <a class="btn" href="${esc(p.url)}" target="_blank">Open post</a>
  </div>`).join('') || '<p class="muted">No post data.</p>';

const snapshotRows = history.snapshots.map((s, i) => `<tr><td>Round ${s.analysisRound || i + 1} · ${esc(s.sessionId || '')}</td><td>${esc(s.pageStats?.followers || '-')}</td><td>${esc(s.aggregateMetrics?.avgViews || '-')}</td><td>${esc(s.aggregateMetrics?.topPostViews || '-')}</td></tr>`).join('');

const replicationDir = join(effectiveDir, 'replication-scripts');
const replicationFiles = existsSync(replicationDir) ? readdirSync(replicationDir).filter(f => f.endsWith('.md')) : [];
const fallbackRep = !replicationFiles.length && existsSync(join(projectDir, 'replication-scripts')) ? readdirSync(join(projectDir, 'replication-scripts')).filter(f => f.endsWith('.md')) : [];
const repFiles = replicationFiles.length ? replicationFiles : fallbackRep;
const replicationLinks = repFiles.map(f => `<li><a href="replication-scripts/${esc(f)}">${esc(f)}</a></li>`).join('');

let verdict = 'Stable (baseline)';
if (history.snapshots.length >= 2) {
  const a = parseFloat(history.snapshots[0].aggregateMetrics?.avgViews || 0);
  const b = parseFloat(history.snapshots[history.snapshots.length - 1].aggregateMetrics?.avgViews || 0);
  if (a && b) {
    const pct = ((b - a) / a) * 100;
    verdict = pct > 10 ? `Improving (+${pct.toFixed(0)}% avg views)` : pct < -10 ? `Declining (${pct.toFixed(0)}% avg views)` : 'Stable';
  }
}

const analysisContent = read(pickFile('top5-analysis.md')) || read(join(projectDir, 'top5-analysis.md'));

const html = `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Facebook Research — ${esc(config.pageName || projectName)}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f14; color: #e7e9ea; line-height: 1.6; }
  .container { max-width: 960px; margin: 0 auto; padding: 20px; }
  h1 { font-size: 2rem; color: #fff; margin-bottom: 4px; }
  h2 { font-size: 1.4rem; margin: 30px 0 15px; color: #1877f2; border-bottom: 2px solid #1877f2; padding-bottom: 8px; }
  .meta { color: #8a94a6; font-size: 0.9rem; margin-bottom: 20px; }
  .card { background: #151c26; border: 1px solid #1f2835; border-radius: 12px; padding: 18px; margin-bottom: 14px; }
  .card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .rank { color: #1877f2; font-weight: 800; } .author { font-weight: 700; }
  .stats { color: #8a94a6; font-size: 0.9rem; margin-bottom: 10px; }
  .btn { display: inline-block; padding: 6px 14px; border-radius: 8px; background: #1877f2; color: #fff; text-decoration: none; font-weight: 600; font-size: 0.85rem; }
  table { width: 100%; border-collapse: collapse; margin: 10px 0; }
  th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #1f2835; }
  th { color: #1877f2; } .muted { color: #8a94a6; }
  .verdict { display: inline-block; padding: 4px 14px; border-radius: 999px; background: #1877f2; color: #fff; font-weight: 600; }
  .footer { text-align: center; color: #8a94a6; padding: 30px 0; font-size: 0.85rem; }
</style></head><body><div class="container">
  <h1>Facebook Page Analysis — Round ${history.snapshots.length || 1} ${sessionId ? `· ${esc(sessionId)}` : ''}</h1>
  <p class="meta"><strong>Page:</strong> ${esc(config.pageName || projectName)} | <strong>Niche:</strong> ${esc(config.niche || '-')} | <strong>Trend:</strong> <span class="verdict">${esc(verdict)}</span></p>

  <h2>Top 5 Posts</h2>
  ${top5}

  <h2>Performance History</h2>
  <table><tr><th>Round</th><th>Followers</th><th>Avg Views</th><th>Top Post Views</th></tr>${snapshotRows}</table>

  <h2>Analysis</h2>
  <div class="card">${esc(analysisContent).substring(0, 2000) || '<p class="muted">No analysis yet — run facebook-research-analyze.</p>'}</div>

  <h2>Replication Scripts</h2>
  <div class="card">${replicationLinks.length ? `<ul>${replicationLinks}</ul>` : '<p class="muted">None yet.</p>'}</div>

  <div class="footer">Generated by facebook-research · ${esc(projectName)} ${sessionId ? `· ${esc(sessionId)}` : ''}</div>
</div></body></html>`;

const outDir = effectiveDir;
writeFileSync(join(outDir, 'REPORT.html'), html);
// also mirror to projectDir for back-compat if sessionDir differs
if (outDir !== projectDir) {
  try { writeFileSync(join(projectDir, 'REPORT.html'), html); } catch {}
}
console.log('Report generated:', join(outDir, 'REPORT.html'));
if (sessionDir) console.log('Session:', sessionDir);
