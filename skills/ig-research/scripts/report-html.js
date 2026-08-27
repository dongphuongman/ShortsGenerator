#!/usr/bin/env node
// =============================================================================
// Social Media Research — HTML Report Generator
// Platform-agnostic: works with raw-posts.json from any platform
// Reads transcripts + hook screenshots + engagement data, generates styled HTML
// Usage: node scripts/report-html.js <project-name>
// =============================================================================

import { readFileSync, writeFileSync, existsSync, readdirSync } from 'fs';

import { join, dirname, resolve } from 'path';

function resolveDataRoot(dotName = '.ig-research') {
  const envKey = dotName.replace(/^\./, '').replace(/-/g, '_').toUpperCase() + '_ROOT';
  if (process.env[envKey]) return resolve(process.env[envKey]);
  if (process.env.IG_RESEARCH_ROOT) return resolve(process.env.IG_RESEARCH_ROOT);
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
  for (let i=0;i<raw.length;i++) {
    const a=raw[i];
    if (a==='--session' && raw[i+1]) { sessionId=raw[++i]; continue; }
    if (a.startsWith('--session=')) { sessionId=a.split('=')[1]; continue; }
    if (a==='--data-root' && raw[i+1]) { dataRoot=resolve(raw[++i]); continue; }
    if (a.startsWith('--data-root=')) { dataRoot=resolve(a.split('=')[1]); continue; }
    if (a.startsWith('--')) continue;
    if (!projectName) projectName=a;
    else if (!sessionId) sessionId=a;
  }
  return { projectName, sessionId, dataRoot: dataRoot || resolveDataRoot() };
}
const { projectName, sessionId, dataRoot } = parseArgs();
if (!projectName) {
  console.error('Usage: node scripts/report-html.js <project-name> [sessionId] [--session <id>] [--data-root <path>]');
  process.exit(1);
}
const projectDir = join(dataRoot, 'projects', projectName);
let sessionDir = null;
if (sessionId) sessionDir = join(projectDir, sessionId);
else {
  try {
    const latestFile = join(projectDir, 'latest.json');
    if (existsSync(latestFile)) {
      const latest = JSON.parse(readFileSync(latestFile, 'utf8'));
      if (latest.sessionId && existsSync(join(projectDir, latest.sessionId))) sessionDir = join(projectDir, latest.sessionId);
    }
    if (!sessionDir) {
      const entries = readdirSync(projectDir, { withFileTypes: true }).filter(d=>d.isDirectory() && /^\d{4}-\d{2}-\d{2}_\d{6}$/.test(d.name)).map(d=>d.name).sort();
      if (entries.length) sessionDir = join(projectDir, entries[entries.length-1]);
    }
  } catch {}
}
const effectiveDir = sessionDir && existsSync(sessionDir) ? sessionDir : projectDir;
const dataFile = join(effectiveDir, 'raw-posts.json');
const transcriptsDir = join(effectiveDir, 'transcripts');
const hooksDir = join(effectiveDir, 'hook-screenshots');
if (!existsSync(dataFile)) {
  // fallback to projectDir
  const fallback = join(projectDir, 'raw-posts.json');
  if (existsSync(fallback)) {
    // use fallback but set effective to projectDir
  } else {
    console.error(`No data found: ${dataFile} (also checked ${fallback})\nRun scrape first.`);
    process.exit(1);
  }
}

const data = JSON.parse(readFileSync(dataFile, 'utf8'));
const posts = (data.posts || []).sort((a, b) => parseEngagement(b) - parseEngagement(a));

function parseEngagement(post) {
  const likeStr = post.likes || post.likesFromBtn || '';
  const match = likeStr.match(/([\d,.]+)\s*([KkMm])?/);
  if (!match) return 0;
  let num = parseFloat(match[1].replace(/,/g, ''));
  if (match[2]?.match(/[Kk]/)) num *= 1000;
  if (match[2]?.match(/[Mm]/)) num *= 1000000;
  return num;
}

function formatNumber(str) {
  if (!str) return '0';
  const match = str.match(/([\d,.]+)\s*([KkMm])?/);
  if (!match) return str;
  const num = parseFloat(match[1].replace(/,/g, ''));
  const suffix = match[2]?.toUpperCase() || '';
  if (suffix) return num + suffix;
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

// Read transcript
function getTranscript(postId) {
  const txtFile = join(transcriptsDir, `${postId}.txt`);
  if (existsSync(txtFile)) {
    return readFileSync(txtFile, 'utf8').trim();
  }
  return '';
}

// Check screenshots
function hasScreenshots(postId) {
  return existsSync(join(hooksDir, `${postId}_0s.jpg`));
}

function getScreenshotPath(postId, sec) {
  const p = join(hooksDir, `${postId}_${sec}s.jpg`);
  if (existsSync(p)) {
    const rel = join('hook-screenshots', `${postId}_${sec}s.jpg`);
    // keep legacy path for report portability; effective is sessionDir
    return rel;
  }
  return null;
}

function postUrl(postId) {
  return `https://www.instagram.com/p/${postId}/`;
}

// Analyze "why it worked"
function analyzePost(post) {
  const findings = [];
  const transcript = getTranscript(post.postId);
  const caption = (post.fullCaption || post.caption || '').toLowerCase();
  const combined = (caption + ' ' + transcript).toLowerCase();
  const likes = parseEngagement(post);

  // Comment-bait CTAs
  if (/comment/i.test(combined) || /type\s+/.test(combined) || /drop\s+(a\s+)?/i.test(combined) || /save this/i.test(combined)) {
    findings.push('Uses comment-bait CTA to boost engagement signal');
  }

  // Specific numbers in hooks
  if (/\d{2,}/.test(combined) && /(ways|tips|steps|rules|things|habits|mistakes|reasons|secrets|hacks)/i.test(combined)) {
    findings.push('Uses specific numbers for anchoring effect');
  }

  // Named frameworks
  if (/(method|framework|technique|system|strategy|formula|principle|rule)/i.test(combined) && /[A-Z][a-z]+/.test(combined)) {
    findings.push('Uses named framework for authority and memorability');
  }

  // Short punchy hooks
  const sentences = (post.caption || transcript || '').split(/[.!?]/).filter(Boolean);
  if (sentences.length > 0 && sentences[0].trim().split(' ').length <= 8) {
    findings.push('Short punchy hook (\u22648 words) for immediate grab');
  }

  // Question format
  if (/^(\w+\s+){1,5}\?/.test(post.caption?.trim() || '') || /^(\w+\s+){1,5}\?/.test(transcript.trim() || '')) {
    findings.push('Opens with a question to trigger curiosity gap');
  }

  // High engagement
  if (likes > 50000) {
    findings.push('Exceptionally high engagement signals broad appeal');
  } else if (likes > 10000) {
    findings.push('Strong engagement indicates resonance with audience');
  }

  // Comparison format
  if (/(vs\.?|versus|better than|worse than|instead of|rather than)/i.test(combined)) {
    findings.push('Uses comparison format for contrast and clarity');
  }

  // Time promises
  if (/(minutes?|seconds?|days?|hours?|weeks?)\s+(or\s+)?(less|under|save|in\s+just|in\s+only)/i.test(combined)) {
    findings.push('Promises time efficiency (loss aversion trigger)');
  }

  if (findings.length === 0) {
    findings.push('Engagement appears driven by authority/credibility of creator');
  }

  return findings;
}

// Infer visual hook type
function inferVisualHook(post) {
  const transcript = getTranscript(post.postId);
  const caption = (post.fullCaption || post.caption || '').toLowerCase();
  const combined = caption + ' ' + transcript;

  if (/(split\s*screen|duet|stitch)/i.test(combined)) return 'Split screen / Duet';
  if (/(whiteboard|drawing|sketch|doodle)/i.test(combined)) return 'Whiteboard animation';
  if (/(screen\s*record|screen\s*capture|screen\s*share|tutorial|demo)/i.test(combined)) return 'Screen recording';
  if (/(podcast|microphone|interview|conversation)/i.test(combined)) return 'Podcast / Interview format';
  if (/(text\s*overlay|caption|subtitles?)/i.test(combined) && /face|talking|speaking/i.test(combined)) return 'Talking head with bold text overlay';
  if (/(b-roll|stock|footage|montage)/i.test(combined)) return 'B-roll montage with voiceover';
  if (/(before|after|transformation|progress)/i.test(combined)) return 'Before / After transformation';
  if (/(list|numbered|countdown|top\s*\d+)/i.test(combined)) return 'Numbered list format';

  return 'Talking head with text overlay';
}

// Get spoken hook from transcript
function getSpokenHook(post) {
  const transcript = getTranscript(post.postId);
  if (!transcript) return '';
  const sentences = transcript.split(/[.!?]/).filter(Boolean);
  if (sentences.length === 0) return '';
  let hook = sentences[0].trim();
  if (hook.length > 120) hook = hook.substring(0, 117) + '...';
  return hook;
}

// Count transcribed
const transcribedCount = posts.filter(p => getTranscript(p.postId)).length;
const reelCount = posts.filter(p => p.type === 'reel').length;
const screenshotCount = posts.filter(p => hasScreenshots(p.postId)).length;
const topLikes = posts.length > 0 ? formatNumber(posts[0].likes || posts[0].likesFromBtn) : '0';

const topPosts = posts.slice(0, 6);
const reelPercent = posts.length > 0 ? Math.round((reelCount / posts.length) * 100) : 0;

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Pattern analysis
const commentCtaCount = posts.filter(p => {
  const c = (p.fullCaption || p.caption || '').toLowerCase();
  return /comment|type\s+|drop\s+|save this/i.test(c);
}).length;

const questionHookCount = posts.filter(p => {
  const c = (p.fullCaption || '').trim();
  return /^(\w+\s+){1,5}\?/.test(c);
}).length;

const numberHookCount = posts.filter(p => {
  const c = (p.fullCaption || '').toLowerCase();
  return /\d+\s+(ways|tips|steps|rules|things|habits|mistakes|reasons|secrets|hacks)/i.test(c);
}).length;

const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(data.project)} — Content Research Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #0A0A08;
      color: #E8E6E0;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }
    .container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }

    /* Hero */
    .hero {
      background: linear-gradient(135deg, #0A0A08 0%, #1A1508 50%, #0A0A08 100%);
      border-bottom: 1px solid #2A2518;
      padding: 80px 0 60px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }
    .hero::before {
      content: '';
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: radial-gradient(circle at 50% 50%, rgba(212, 168, 67, 0.03) 0%, transparent 50%);
      pointer-events: none;
    }
    .hero-label {
      display: inline-block;
      background: rgba(212, 168, 67, 0.1);
      border: 1px solid rgba(212, 168, 67, 0.2);
      color: #D4A843;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 2px;
      text-transform: uppercase;
      padding: 6px 16px;
      border-radius: 20px;
      margin-bottom: 24px;
    }
    .hero h1 {
      font-size: 48px;
      font-weight: 800;
      color: #FFF;
      letter-spacing: -1.5px;
      margin-bottom: 12px;
      position: relative;
    }
    .hero h1 span { color: #D4A843; }
    .hero .subtitle {
      font-size: 18px;
      color: #9A9488;
      font-weight: 400;
      margin-bottom: 8px;
    }
    .hero .meta {
      font-size: 14px;
      color: #6B6558;
    }
    .hero .meta span { margin: 0 12px; }

    /* Stats Bar */
    .stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 16px;
      margin-top: -32px;
      padding: 0 24px;
      max-width: 1200px;
      margin-left: auto;
      margin-right: auto;
      position: relative;
      z-index: 1;
    }
    .stat-card {
      background: #121210;
      border: 1px solid #1E1C18;
      border-radius: 16px;
      padding: 24px 20px;
      text-align: center;
      transition: border-color 0.2s;
    }
    .stat-card:hover { border-color: #D4A843; }
    .stat-card .number {
      font-size: 32px;
      font-weight: 800;
      color: #D4A843;
      letter-spacing: -1px;
      margin-bottom: 4px;
    }
    .stat-card .label {
      font-size: 13px;
      color: #6B6558;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    /* Section */
    .section { padding: 60px 0; }
    .section-title {
      font-size: 28px;
      font-weight: 700;
      color: #FFF;
      letter-spacing: -0.5px;
      margin-bottom: 8px;
    }
    .section-subtitle {
      font-size: 15px;
      color: #6B6558;
      margin-bottom: 40px;
    }

    /* Post Card */
    .post-card {
      background: #121210;
      border: 1px solid #1E1C18;
      border-radius: 20px;
      overflow: hidden;
      margin-bottom: 32px;
      transition: all 0.3s ease;
    }
    .post-card:hover {
      border-color: #D4A843;
      transform: translateY(-2px);
      box-shadow: 0 12px 40px rgba(212, 168, 67, 0.06);
    }
    .post-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      border-bottom: 1px solid #1E1C18;
    }
    .post-rank {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .post-rank .number {
      width: 36px;
      height: 36px;
      background: rgba(212, 168, 67, 0.1);
      border: 1px solid rgba(212, 168, 67, 0.2);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      font-weight: 700;
      color: #D4A843;
    }
    .post-rank .author {
      font-size: 16px;
      font-weight: 600;
      color: #FFF;
    }
    .post-rank .author a {
      color: #D4A843;
      text-decoration: none;
    }
    .post-rank .author a:hover { text-decoration: underline; }
    .post-rank .type-badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      padding: 3px 10px;
      border-radius: 6px;
      margin-left: 8px;
    }
    .type-badge.reel { background: rgba(212, 168, 67, 0.1); color: #D4A843; border: 1px solid rgba(212, 168, 67, 0.2); }
    .type-badge.image { background: rgba(100, 100, 100, 0.15); color: #9A9488; border: 1px solid rgba(100, 100, 100, 0.2); }
    .post-engagement {
      display: flex;
      gap: 20px;
    }
    .post-engagement .stat {
      text-align: right;
    }
    .post-engagement .stat .val {
      font-size: 16px;
      font-weight: 700;
      color: #FFF;
    }
    .post-engagement .stat .lbl {
      font-size: 11px;
      color: #6B6558;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .post-card-body { padding: 24px; }

    /* Hook screenshots row */
    .hook-screenshots {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 24px;
      border-radius: 12px;
      overflow: hidden;
    }
    .hook-screenshots img {
      width: 100%;
      height: 200px;
      object-fit: cover;
      border-radius: 8px;
      background: #1A1A16;
      border: 1px solid #1E1C18;
    }
    .hook-screenshots .no-ss {
      height: 200px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #1A1A16;
      border: 1px solid #1E1C18;
      border-radius: 8px;
      color: #6B6558;
      font-size: 13px;
    }

    /* Analysis grid */
    .analysis-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 20px;
    }
    @media (max-width: 768px) {
      .analysis-grid { grid-template-columns: 1fr; }
    }
    .analysis-block {
      background: #0E0E0C;
      border: 1px solid #1E1C18;
      border-radius: 12px;
      padding: 16px;
    }
    .analysis-block h4 {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #6B6558;
      margin-bottom: 10px;
    }
    .analysis-block .hook-desc {
      font-size: 14px;
      color: #D4A843;
      font-weight: 500;
    }
    .analysis-block .spoken-hook {
      font-size: 14px;
      color: #E8E6E0;
      font-style: italic;
      line-height: 1.5;
    }
    .analysis-block .spoken-hook::before { content: '\\201c'; }
    .analysis-block .spoken-hook::after { content: '\\201d'; }

    .findings-list {
      list-style: none;
      padding: 0;
    }
    .findings-list li {
      font-size: 13px;
      color: #C8C4BC;
      padding: 6px 0;
      border-bottom: 1px solid #1A1814;
    }
    .findings-list li:last-child { border-bottom: none; }
    .findings-list li::before {
      content: '\\2713';
      color: #D4A843;
      margin-right: 8px;
      font-weight: 700;
    }

    .transcript-block {
      margin-top: 16px;
    }
    .transcript-block summary {
      font-size: 13px;
      font-weight: 500;
      color: #D4A843;
      cursor: pointer;
      padding: 8px 0;
    }
    .transcript-block summary:hover { opacity: 0.8; }
    .transcript-block .transcript-text {
      font-size: 13px;
      color: #9A9488;
      line-height: 1.7;
      max-height: 150px;
      overflow-y: auto;
      padding: 12px;
      background: #0A0A08;
      border: 1px solid #1E1C18;
      border-radius: 8px;
      margin-top: 8px;
    }
    .transcript-block .transcript-text::-webkit-scrollbar { width: 6px; }
    .transcript-block .transcript-text::-webkit-scrollbar-track { background: #0A0A08; }
    .transcript-block .transcript-text::-webkit-scrollbar-thumb { background: #2A2518; border-radius: 3px; }

    .caption-preview {
      font-size: 13px;
      color: #6B6558;
      margin-top: 12px;
      padding: 12px;
      background: #0A0A08;
      border: 1px solid #1E1C18;
      border-radius: 8px;
      line-height: 1.5;
      max-height: 60px;
      overflow: hidden;
      position: relative;
    }
    .caption-preview::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 24px;
      background: linear-gradient(transparent, #0A0A08);
    }

    /* Patterns */
    .patterns-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 20px;
    }
    .pattern-card {
      background: #121210;
      border: 1px solid #1E1C18;
      border-radius: 16px;
      padding: 24px;
      transition: border-color 0.2s;
    }
    .pattern-card:hover { border-color: #D4A843; }
    .pattern-card .pattern-icon {
      font-size: 28px;
      margin-bottom: 12px;
    }
    .pattern-card h3 {
      font-size: 16px;
      font-weight: 600;
      color: #FFF;
      margin-bottom: 8px;
    }
    .pattern-card p {
      font-size: 13px;
      color: #9A9488;
      line-height: 1.6;
    }
    .pattern-card .stat-row {
      display: flex;
      gap: 8px;
      margin-top: 12px;
      flex-wrap: wrap;
    }
    .pattern-card .stat-row .pill {
      font-size: 12px;
      font-weight: 500;
      padding: 4px 12px;
      border-radius: 12px;
      background: rgba(212, 168, 67, 0.1);
      color: #D4A843;
      border: 1px solid rgba(212, 168, 67, 0.15);
    }

    /* Footer */
    .footer {
      text-align: center;
      padding: 40px 0;
      border-top: 1px solid #1E1C18;
      color: #6B6558;
      font-size: 13px;
    }
    .footer a {
      color: #D4A843;
      text-decoration: none;
    }
    .footer a:hover { text-decoration: underline; }

    .no-data {
      text-align: center;
      padding: 60px 0;
      color: #6B6558;
      font-size: 16px;
    }
  </style>
</head>
<body>
  <section class="hero">
    <div class="container">
      <div class="hero-label">${escapeHtml(data.platform || 'instagram')} Content Research</div>
      <h1>${escapeHtml(data.project)}</h1>
      <p class="subtitle">${escapeHtml(data.niche)}</p>
      <p class="meta">
        ${data.searchTerms?.map(t => '#' + t).join('  \\00b7  ') || ''}
        <span>\\00b7</span>
        ${data.totalPosts || 0} posts analyzed
        <span>\\00b7</span>
        ${new Date(data.scrapedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
      </p>
    </div>
  </section>

  <div class="stats-bar">
    <div class="stat-card">
      <div class="number">${data.totalPosts || 0}</div>
      <div class="label">Total Posts</div>
    </div>
    <div class="stat-card">
      <div class="number">${reelPercent}%</div>
      <div class="label">Reels</div>
    </div>
    <div class="stat-card">
      <div class="number">${transcribedCount}</div>
      <div class="label">Transcribed</div>
    </div>
    <div class="stat-card">
      <div class="number">${screenshotCount}</div>
      <div class="label">Visual Hooks</div>
    </div>
    <div class="stat-card">
      <div class="number">${topLikes}</div>
      <div class="label">Top Likes</div>
    </div>
  </div>

  <section class="section">
    <div class="container">
      <h2 class="section-title">Top ${Math.min(topPosts.length, 6)} Performing Posts</h2>
      <p class="section-subtitle">Ranked by engagement, with hooks, transcripts, and psychological analysis</p>

      ${topPosts.length === 0 ? '<div class="no-data">No posts found. Run the scraper first.</div>' : ''}

      ${topPosts.map((post, i) => {
  const transcript = getTranscript(post.postId);
  const findings = analyzePost(post);
  const visualHook = inferVisualHook(post);
  const spokenHook = getSpokenHook(post);
  const ss0 = getScreenshotPath(post.postId, 0);
  const ss1 = getScreenshotPath(post.postId, 1);
  const ss2 = getScreenshotPath(post.postId, 2);
  const caption = post.caption || post.fullCaption || '';

  return `
      <div class="post-card">
        <div class="post-card-header">
          <div class="post-rank">
            <div class="number">${i + 1}</div>
            <div>
              <span class="author">${post.author ? '<a href="https://www.instagram.com/' + escapeHtml(post.author) + '/" target="_blank">@' + escapeHtml(post.author) + '</a>' : 'Unknown'}</span>
              <span class="type-badge ${post.type}">${post.type}</span>
            </div>
          </div>
          <div class="post-engagement">
            <div class="stat">
              <div class="val">${formatNumber(post.likes)}</div>
              <div class="lbl">Likes</div>
            </div>
            ${post.commentsCount || post.comments ? `<div class="stat"><div class="val">${formatNumber(post.commentsCount || post.comments)}</div><div class="lbl">Comments</div></div>` : ''}
          </div>
        </div>
        <div class="post-card-body">
          ${post.type === 'reel' ? `
          <div class="hook-screenshots">
            ${ss0 ? `<img src="${ss0}" alt="Hook at 0s" loading="lazy">` : '<div class="no-ss">No screenshot</div>'}
            ${ss1 ? `<img src="${ss1}" alt="Hook at 1s" loading="lazy">` : '<div class="no-ss">No screenshot</div>'}
            ${ss2 ? `<img src="${ss2}" alt="Hook at 2s" loading="lazy">` : '<div class="no-ss">No screenshot</div>'}
          </div>` : ''}

          <div class="analysis-grid">
            <div>
              <div class="analysis-block">
                <h4>Visual Hook</h4>
                <p class="hook-desc">${escapeHtml(visualHook)}</p>
              </div>
              ${spokenHook ? `
              <div class="analysis-block" style="margin-top: 16px;">
                <h4>Spoken Hook</h4>
                <p class="spoken-hook">${escapeHtml(spokenHook)}</p>
              </div>` : ''}
            </div>
            <div>
              <div class="analysis-block">
                <h4>Why It Worked</h4>
                <ul class="findings-list">
                  ${findings.map(f => `<li>${escapeHtml(f)}</li>`).join('')}
                </ul>
              </div>
            </div>
          </div>

          ${transcript ? `
          <div class="transcript-block">
            <details>
              <summary>Full Transcript (${transcript.split(' ').length} words)</summary>
              <div class="transcript-text">${escapeHtml(transcript)}</div>
            </details>
          </div>` : ''}

          ${caption ? `
          <div class="caption-preview">${escapeHtml(caption)}</div>` : ''}
        </div>
      </div>`;
}).join('')}
    </div>
  </section>

  <section class="section" style="padding-top: 0;">
    <div class="container">
      <h2 class="section-title">Winning Patterns</h2>
      <p class="section-subtitle">Recurring formats and techniques driving engagement in this niche</p>

      <div class="patterns-grid">
        <div class="pattern-card">
          <div class="pattern-icon">\\01F4F1</div>
          <h3>Format Breakdown</h3>
          <p>${reelCount} of ${data.totalPosts} posts were reels (${reelPercent}%). ${data.images || 0} were static images. ${reelPercent >= 70 ? 'Video content dominates this niche.' : 'Mixed format approach used.'}</p>
          <div class="stat-row">
            <span class="pill">${reelPercent}% Reels</span>
            <span class="pill">${data.images || 0} Images</span>
          </div>
        </div>

        <div class="pattern-card">
          <div class="pattern-icon">\\01F4AC</div>
          <h3>Comment CTA Usage</h3>
          <p>${commentCtaCount} of ${data.totalPosts} posts use explicit comment-bait CTAs (${data.totalPosts > 0 ? Math.round(commentCtaCount / data.totalPosts * 100) : 0}%). ${commentCtaCount > data.totalPosts / 2 ? 'Comment CTAs are a dominant engagement strategy.' : 'Comment CTAs present but not dominant.'}</p>
          <div class="stat-row">
            <span class="pill">${Math.round(commentCtaCount / Math.max(data.totalPosts, 1) * 100)}% of posts</span>
          </div>
        </div>

        <div class="pattern-card">
          <div class="pattern-icon">\\01F3AF</div>
          <h3>Hook Analysis</h3>
          <p>${questionHookCount} posts open with a question hook. ${numberHookCount} use numbered frameworks. ${questionHookCount + numberHookCount > data.totalPosts / 2 ? 'Question hooks and numbered lists are the primary hook styles.' : 'Hooks vary, with no single dominant style.'}</p>
          <div class="stat-row">
            <span class="pill">${questionHookCount} Question hooks</span>
            <span class="pill">${numberHookCount} Number hooks</span>
          </div>
        </div>

        <div class="pattern-card">
          <div class="pattern-icon">\\01F4A1</div>
          <h3>Content Themes</h3>
          <p>Top performers in ${escapeHtml(data.niche)} leverage ${reelPercent >= 70 ? 'video-first storytelling with hooks in the first 2 seconds' : 'a mix of carousel posts and short-form video'}. ${commentCtaCount > data.totalPosts / 2 ? 'Interactive engagement (comments, saves, shares) drives algorithmic reach.' : 'Algorithmic reach appears driven by watch time and shares.'}</p>
          <div class="stat-row">
            <span class="pill">${escapeHtml(data.niche.split(' ')[0] || 'niche')}</span>
            <span class="pill">${data.totalPosts} samples</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <footer class="footer">
    <div class="container">
      Created using the <a href="https://magicSync.dev" target="_blank">magicSync</a> &mdash;
      <a href="https://www.instagram.com/magicSyncdotdev" target="_blank">@magicSyncdotdev</a>
      &nbsp;\\00b7&nbsp;
      <a href="https://github.com/leamsigc/shortGenerator" target="_blank">View Source</a>
    </div>
  </footer>
</body>
</html>`;

const outputFile = join(effectiveDir, 'report.html');
writeFileSync(outputFile, html);
if (effectiveDir !== projectDir) { try { writeFileSync(join(projectDir, 'report.html'), html); } catch {} }

console.log(`\nReport generated: ${outputFile}` + (effectiveDir !== projectDir ? ` (also mirrored to ${projectDir}/report.html)` : ''));
console.log(`Session: ${effectiveDir}`);
