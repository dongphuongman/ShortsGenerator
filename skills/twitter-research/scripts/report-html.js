// =============================================================================
// Twitter/X Research — HTML Report Generator
// Renders REPORT.html from raw-posts.json + optional audience-scores.json,
// content-drafts.json, engagement-responses.json.
// Usage: node scripts/report-html.js <timestamp>
// =============================================================================

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join, dirname, resolve } from 'path';

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
function parseTimestamp() {
  const raw = process.argv.slice(2);
  let ts=null, dataRoot=null;
  for (let i=0;i<raw.length;i++) {
    const a=raw[i];
    if (a==='--data-root' && raw[i+1]) { dataRoot=resolve(raw[++i]); continue; }
    if (a.startsWith('--data-root=')) { dataRoot=resolve(a.split('=')[1]); continue; }
    if (a==='--session' && raw[i+1]) { ts=raw[++i]; continue; }
    if (a.startsWith('--session=')) { ts=a.split('=')[1]; continue; }
    if (a.startsWith('--')) continue;
    if (!ts) ts=a;
  }
  return { timestamp: ts, dataRoot: dataRoot || resolveDataRoot() };
}
const { timestamp, dataRoot } = parseTimestamp();
if (!timestamp) {
  console.error('Usage: node scripts/report-html.js <timestamp> [--session <id>] [--data-root <path>]');
  process.exit(1);
}
const sessionDir = join(dataRoot, timestamp);
const read = (name) => {
  const p = join(sessionDir, name);
  return existsSync(p) ? JSON.parse(readFileSync(p, 'utf8')) : null;
};

const config = read('config.json') || {};
const raw = read('raw-posts.json') || { posts: [] };
const scores = read('audience-scores.json') || null;
const drafts = read('content-drafts.json') || null;
const responses = read('engagement-responses.json') || null;

const posts = raw.posts || [];
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function fmt(n) {
  if (!n && n !== 0) return '0';
  const num = Number(n);
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return String(num);
}

const scoreBadge = score => {
  if (score >= 9) return '<span class="badge g9">' + score + '/10</span>';
  if (score >= 7) return '<span class="badge g7">' + score + '/10</span>';
  if (score >= 5) return '<span class="badge g5">' + score + '/10</span>';
  return '<span class="badge g0">' + score + '/10</span>';
};

const segmentsHtml = scores && scores.segments && scores.segments.length ? scores.segments.map((s, i) => `
  <div class="seg-row">
    <span class="rank">${['🥇','🥈','🥉'][i] || i + 1}</span>
    <span class="seg-name">${esc(s.segment)}</span>
    ${scoreBadge(s.finalScore)}
    <span class="verdict">${esc(s.verdict || '')}</span>
  </div>`).join('') : '<p class="muted">No audience scoring data.</p>';

const postsHtml = posts.map(p => `
  <div class="card">
    <div class="card-head">
      <span class="author">${esc(p.handle || 'unknown')}</span>
      <span class="stats">❤️ ${fmt(p.likes)} · 🔁 ${fmt(p.retweets)} · 💬 ${fmt(p.replies)}</span>
    </div>
    <div class="tweet-text">"${esc((p.text || '').substring(0, 280))}"</div>
    <a class="btn" href="${esc(p.url)}" target="_blank">View on X ↗</a>
  </div>`).join('') || '<p class="muted">No posts scraped.</p>';

const draftsHtml = drafts ? (drafts.postDrafts || []).map((d, i) => `
  <div class="card">
    <div class="draft-head">Post Draft #${i + 1} — 🎯 ${esc(d.targetSegment || '')}</div>
    <p class="draft-line"><strong>Headline:</strong> ${esc(d.headline)}</p>
    <p class="draft-line"><strong>Body:</strong> ${esc(d.body)}</p>
    <p class="draft-line"><strong>CTA:</strong> ${esc(d.cta)}</p>
    <p class="draft-line">${esc((d.hashtags || []).join(' '))}</p>
  </div>`).join('') : '';

const scriptsHtml = drafts ? (drafts.videoScripts || []).map((s, i) => `
  <div class="card">
    <div class="draft-head">Video Script #${i + 1} — 🎯 ${esc(s.targetSegment || '')}</div>
    <p class="draft-line"><strong>Hook:</strong> ${esc(s.hook)}</p>
    <p class="draft-line"><strong>Body:</strong> ${esc(s.body)}</p>
    <p class="draft-line"><strong>CTA:</strong> ${esc(s.cta)}</p>
  </div>`).join('') : '';

const responsesHtml = responses ? (responses.responses || []).map(r => `
  <div class="card">
    <div class="card-head"><span class="author">${esc(r.targetHandle)}</span><a class="btn small" href="${esc(r.targetPostUrl)}" target="_blank">Reply on X ↗</a></div>
    <p class="tweet-text">${esc(r.postPreview)}</p>
    ${(r.responses || []).map(v => `<div class="resp"><span class="rtype t-${v.type}">${esc(v.type)}</span> "${esc(v.text)}"</div>`).join('')}
  </div>`).join('') : '';

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Twitter/X Research — ${esc(config.topic || timestamp)}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1419; color: #e7e9ea; line-height: 1.6; }
  .container { max-width: 960px; margin: 0 auto; padding: 20px; }
  h1 { font-size: 2rem; color: #fff; margin-bottom: 4px; }
  h2 { font-size: 1.4rem; margin: 30px 0 15px; color: #1d9bf0; border-bottom: 2px solid #1d9bf0; padding-bottom: 8px; }
  .meta { color: #71767b; font-size: 0.9rem; margin-bottom: 20px; }
  .card { background: #1a1f2e; border: 1px solid #2f3336; border-radius: 12px; padding: 18px; margin-bottom: 16px; }
  .card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .author { font-weight: 700; font-size: 1.05rem; }
  .stats { font-size: 0.85rem; color: #71767b; }
  .tweet-text { background: #0f1419; padding: 12px; border-radius: 8px; border: 1px solid #2f3336; font-style: italic; margin-bottom: 10px; }
  .btn { display: inline-block; padding: 7px 16px; border-radius: 999px; background: #1d9bf0; color: #fff; text-decoration: none; font-weight: 600; font-size: 0.85rem; }
  .btn.small { padding: 4px 12px; font-size: 0.8rem; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-weight: 700; font-size: 0.85rem; }
  .g9 { background: #00ba7c; color: #000; } .g7 { background: #1d9bf0; color: #fff; }
  .g5 { background: #ffd700; color: #000; } .g0 { background: #f4212e; color: #fff; }
  .seg-row { display: flex; align-items: center; gap: 14px; padding: 12px; background: #1a1f2e; border: 1px solid #2f3336; border-radius: 10px; margin-bottom: 10px; }
  .rank { font-size: 1.4rem; min-width: 34px; } .seg-name { flex: 1; font-weight: 600; }
  .verdict { font-size: 0.85rem; color: #71767b; }
  .draft-head { font-weight: 700; color: #fff; margin-bottom: 8px; }
  .draft-line { margin-bottom: 6px; color: #e7e9ea; }
  .resp { margin: 8px 0; padding: 10px 12px; background: #162d3f; border-left: 3px solid #1d9bf0; border-radius: 0 8px 8px 0; }
  .rtype { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; margin-right: 8px; }
  .t-value_add { background: #00ba7c; color: #000; } .t-discussion_starter { background: #1d9bf0; color: #fff; } .t-agree_amplify { background: #ffd700; color: #000; }
  .muted { color: #71767b; }
  .footer { text-align: center; color: #71767b; padding: 30px 0; font-size: 0.85rem; }
  @media (max-width: 600px) { .container { padding: 12px; } }
</style>
</head>
<body>
<div class="container">
  <h1>🐦 Twitter/X Research Report</h1>
  <p class="meta"><strong>Topic:</strong> ${esc(config.topic)} | <strong>Accounts:</strong> ${raw.distinctAccounts || 0} | <strong>Posts:</strong> ${posts.length} | <strong>Generated:</strong> ${new Date().toLocaleString()}</p>

  <h2>📊 Target Audience Scoring</h2>
  ${segmentsHtml}

  <h2>🎯 Top Posts</h2>
  ${postsHtml}

  ${drafts && drafts.postDrafts && drafts.postDrafts.length ? `<h2>📝 Content Drafts</h2>${draftsHtml}` : ''}
  ${drafts && drafts.videoScripts && drafts.videoScripts.length ? `<h2>🎬 Video Scripts</h2>${scriptsHtml}` : ''}
  ${responses && responses.responses && responses.responses.length ? `<h2>💬 Engagement Responses</h2>${responsesHtml}` : ''}

  <div class="footer">Generated by twitter-research · ${esc(timestamp)}</div>
</div>
</body>
</html>`;

writeFileSync(join(sessionDir, 'REPORT.html'), html);
console.log(`Report generated: ${join(sessionDir, 'REPORT.html')}`);
