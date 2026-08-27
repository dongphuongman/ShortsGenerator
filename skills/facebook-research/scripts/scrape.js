// =============================================================================
// Facebook Research — Page + competitor scraper via Chrome DevTools Protocol
// Extracts page stats, top video posts, engagement metrics, hook screenshots,
// computes ratios, appends a history snapshot for trend comparison.
// Usage: node scripts/scrape.js <project-name> [sessionId] [--session <id>] [--data-root <path>]
//   sessionId defaults to YYYY-MM-DD_HHMMSS (UTC). Outputs to
//   <dataRoot>/projects/<project>/<sessionId>/ with history at projects/<project>/.
//   Bundled inside skill: resolves dataRoot via CWD walk-up, env FB_RESEARCH_ROOT,
//   or --data-root. Global-install safe.
// =============================================================================

import CDP from 'chrome-remote-interface';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { homedir } from 'os';

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

function genTimestamp() {
  return new Date().toISOString().slice(0, 19).replace('T', '_').replace(/:/g, '');
}

function parseArgs() {
  const raw = process.argv.slice(2);
  let projectName = null;
  let sessionId = null;
  let dataRoot = null;
  for (let i = 0; i < raw.length; i++) {
    const a = raw[i];
    if (a === '--session' && raw[i + 1]) { sessionId = raw[++i]; continue; }
    if (a.startsWith('--session=')) { sessionId = a.split('=')[1]; continue; }
    if (a === '--data-root' && raw[i + 1]) { dataRoot = resolve(raw[++i]); continue; }
    if (a.startsWith('--data-root=')) { dataRoot = resolve(a.split('=')[1]); continue; }
    if (a.startsWith('--')) continue;
    if (!projectName) projectName = a;
    else if (!sessionId) sessionId = a;
  }
  return { projectName, sessionId: sessionId || genTimestamp(), dataRoot: dataRoot || resolveDataRoot() };
}

const { projectName, sessionId, dataRoot } = parseArgs();
if (!projectName) {
  console.error('Usage: node scripts/scrape.js <project-name> [sessionId] [--session <id>] [--data-root <path>]');
  process.exit(1);
}

const projectDir = join(dataRoot, 'projects', projectName);
const sessionDir = join(projectDir, sessionId);
const configFile = join(projectDir, 'config.json');
if (!existsSync(configFile)) {
  console.error(`Project not found: ${configFile}\nCreate a config.json first (skill facebook-research-setup).`);
  process.exit(1);
}

const config = JSON.parse(readFileSync(configFile, 'utf8'));
const browserPort = config.browserPort || 9222;
const wait = ms => new Promise(r => setTimeout(r, ms));

function getPort() {
  const portFile = join(homedir(), '.browser-tools', 'port');
  if (existsSync(portFile)) return parseInt(readFileSync(portFile, 'utf8'), 10);
  return browserPort;
}

async function getClient() {
  const port = getPort();
  let targets;
  try {
    targets = await CDP.List({ port });
  } catch (e) {
    console.error(`\nCannot connect to Chrome on port ${port}.`);
    console.error('Make sure Chrome is running with: --remote-debugging-port=9222');
    process.exit(1);
  }
  let target = targets.find(t => t.type === 'page' && /facebook\.com/.test(t.url));
  if (!target) {
    target = await CDP.New({ port, url: 'https://www.facebook.com/' });
    await wait(8000);
  }
  const client = await CDP({ port, target: target.id });
  await client.Page.enable();
  await client.Runtime.enable();
  return client;
}

async function evalJson(client, fn, awaitPromise = true) {
  const { result } = await client.Runtime.evaluate({
    expression: `(${fn})()`,
    awaitPromise,
    returnByValue: true
  });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'Evaluation error');
  return result.value;
}

const NAV_STATS_FN = `() => {
  const result = { pageName: '', followers: '', likes: '', pageCategory: '', description: '' };
  const allText = document.body ? document.body.innerText : '';
  const followerMatch = allText.match(/([\\d,.KM]+)\\s*(?:follower|seguidor)/i);
  if (followerMatch) result.followers = followerMatch[1];
  const likeMatch = allText.match(/([\\d,.KM]+)\\s*(?:like|me gusta)/i);
  if (likeMatch) result.likes = likeMatch[1];
  const metaDesc = document.querySelector('meta[property="og:description"]');
  if (metaDesc) result.description = (metaDesc.getAttribute('content') || '').substring(0, 500);
  return JSON.stringify(result);
}`;

const LIST_VIDEO_FN = `() => {
  const videoLinks = document.querySelectorAll('a[href*="/videos/"], a[href*="/reel/"], a[href*="/watch/"]');
  const seen = new Set();
  const posts = [];
  videoLinks.forEach(a => {
    const href = a.getAttribute('href');
    if (!href || seen.has(href)) return;
    seen.add(href);
    const fullUrl = href.startsWith('http') ? href : 'https://www.facebook.com' + href;
    const parent = a.closest('[role="article"]') || a.parentElement;
    const text = parent ? parent.innerText : '';
    const viewMatch = text.match(/([\\d,.KM]+)\\s*(?:views|reproducciones)/i);
    posts.push({ url: fullUrl, estimatedViews: viewMatch ? viewMatch[1] : null, title: a.getAttribute('aria-label') || a.innerText ? a.innerText.trim() : '' });
  });
  return JSON.stringify({ total: posts.length, posts: posts.slice(0, 30) });
}`;

const POST_METRICS_FN = `() => {
  const text = document.body ? document.body.innerText : '';
  const grab = (re) => { const m = text.match(re); return m ? m[1] : null; };
  const result = {
    views: grab(/([\\d,.KM]+)\\s*(?:views|reproducciones)/i),
    likes: grab(/([\\d,.KM]+)\\s*(?:reactions|likes|reacciones|me gusta)/i),
    comments: grab(/([\\d,.KM]+)\\s*(?:comments|comentarios)/i),
    shares: grab(/([\\d,.KM]+)\\s*(?:shares|compartidos|veces compartido)/i),
    caption: (text.match(/^[\\s\\S]{1,500}/) || [])[0] ? text.substring(0, 500) : ''
  };
  const metaTitle = document.querySelector('meta[property="og:title"]');
  if (metaTitle) result.ogTitle = metaTitle.getAttribute('content');
  return JSON.stringify(result);
}`;

const SCROLL_FN = `async () => {
  let lastHeight = 0;
  for (let i = 0; i < 20; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(r => setTimeout(r, 2000));
    const h = document.body.scrollHeight;
    if (h === lastHeight) break;
    lastHeight = h;
  }
  return 'scrolled';
}`;

const parseNum = s => {
  if (!s) return 0;
  s = String(s).replace(/,/g, '');
  if (s.includes('K')) return parseFloat(s) * 1000;
  if (s.includes('M')) return parseFloat(s) * 1000000;
  if (s.includes('B')) return parseFloat(s) * 1000000000;
  return parseFloat(s) || 0;
};

const compositeScore = (p) => {
  const v = parseNum(p.views) || 1, l = parseNum(p.likes), c = parseNum(p.comments);
  return (0.5 * (v / Math.max(v, 1))) + (0.3 * Math.min(l / Math.max(v, 1) * 100, 1)) + (0.2 * Math.min(c / Math.max(v, 1) * 100, 1));
};

async function scrapePage(client, pageUrl, label) {
  console.log(`  Navigating to ${label}: ${pageUrl}`);
  await client.Page.navigate({ url: pageUrl });
  await wait(7000);
  const stats = JSON.parse(await evalJson(client, NAV_STATS_FN));
  await evalJson(client, SCROLL_FN);
  const listRaw = JSON.parse(await evalJson(client, LIST_VIDEO_FN));
  const posts = [];
  for (const p of listRaw.posts.slice(0, 10)) {
    await client.Page.navigate({ url: p.url });
    await wait(5000);
    const m = JSON.parse(await evalJson(client, POST_METRICS_FN));
    posts.push({ ...p, ...m, composite: compositeScore(m) });
  }
  posts.sort((a, b) => (parseNum(b.views) || 0) - (parseNum(a.views) || 0));
  return { stats, posts };
}

function aggregate(posts) {
  if (!posts.length) return {};
  const nums = posts.map(p => ({ v: parseNum(p.views), l: parseNum(p.likes), c: parseNum(p.comments), s: parseNum(p.shares) }));
  const avg = k => (nums.reduce((a, n) => a + n[k], 0) / nums.length).toFixed(0);
  const med = k => { const a = nums.map(n => n[k]).sort((x, y) => x - y); return a[Math.floor(a.length / 2)] || 0; };
  const top = p => nums.reduce((m, n) => Math.max(m, n[p]), 0);
  return {
    totalPostsScanned: posts.length,
    avgViews: avg('v'), avgLikes: avg('l'), avgComments: avg('c'), avgShares: avg('s'),
    medianViewToLikeRatio: (med('l') / (med('v') || 1)).toFixed(4),
    medianViewToCommentRatio: (med('c') / (med('v') || 1)).toFixed(4),
    medianViewToShareRatio: (med('s') / (med('v') || 1)).toFixed(4),
    topPostViews: top('v'), topPostLikes: top('l'), topPostComments: top('c'), topPostShares: top('s')
  };
}

function trendComparison(current, previous) {
  if (!previous) return { isFirst: true, message: 'First snapshot — baseline established' };
  const changes = {};
  for (const metric of ['followers', 'avgViews', 'avgLikes', 'topPostViews']) {
    const curr = parseFloat(current[metric]), prev = parseFloat(previous[metric]);
    if (curr && prev) {
      const pct = ((curr - prev) / prev) * 100;
      changes[metric] = { previous: prev, current: curr, change: +pct.toFixed(1), direction: pct > 5 ? 'up' : pct < -5 ? 'down' : 'stable' };
    }
  }
  return changes;
}

(async () => {
  mkdirSync(sessionDir, { recursive: true });
  mkdirSync(join(sessionDir, 'screenshots'), { recursive: true });
  const client = await getClient();
  const historyFile = join(projectDir, 'page-analytics-history.json');
  const history = existsSync(historyFile) ? JSON.parse(readFileSync(historyFile, 'utf8')) : { snapshots: [] };
  const round = config.analysisRound || (history.snapshots.length + 1);

  // Main page
  const { stats, posts } = await scrapePage(client, config.pageUrl, 'page');
  const aggr = aggregate(posts);
  const prevSnapshot = history.snapshots[history.snapshots.length - 1] || null;
  const trends = trendComparison({ followers: parseNum(stats.followers), ...aggr }, prevSnapshot ? { followers: parseNum(prevSnapshot.pageStats?.followers), ...prevSnapshot.aggregateMetrics } : null);

  const top5 = posts.slice(0, 5).map((p, i) => ({
    rank: i + 1, title: p.ogTitle || p.title || `Post ${i + 1}`, url: p.url,
    views: p.views, likes: p.likes, comments: p.comments, shares: p.shares,
    viewToLikeRatio: (parseNum(p.likes) / (parseNum(p.views) || 1)).toFixed(4),
    viewToCommentRatio: (parseNum(p.comments) / (parseNum(p.views) || 1)).toFixed(4),
    compositeScore: +p.composite.toFixed(3)
  }));

  const snapshot = {
    analysisRound: round,
    sessionId,
    scrapedAt: new Date().toISOString().replace('T', ' ').substring(0, 19),
    pageStats: { followers: stats.followers, likes: stats.likes, category: stats.pageCategory },
    aggregateMetrics: aggr,
    top5,
    competitors: {}
  };

  // Competitors
  for (const comp of config.competitors || []) {
    try {
      const cPage = await scrapePage(client, comp.url, 'competitor ' + comp.name);
      snapshot.competitors[comp.name] = {
        followers: cPage.stats.followers, topPostViews: cPage.posts[0]?.views || null,
        avgViews: cPage.posts.length ? aggregate(cPage.posts).avgViews : null, avgLikes: cPage.posts.length ? aggregate(cPage.posts).avgLikes : null
      };
      mkdirSync(join(sessionDir, 'competitors', comp.name), { recursive: true });
      writeFileSync(join(sessionDir, 'competitors', comp.name, 'raw-posts.json'), JSON.stringify({ posts: cPage.posts, stats: cPage.stats }, null, 2));
      // also mirror to legacy projectDir for back-compat
      mkdirSync(join(projectDir, 'competitors', comp.name), { recursive: true });
      writeFileSync(join(projectDir, 'competitors', comp.name, 'raw-posts.json'), JSON.stringify({ posts: cPage.posts, stats: cPage.stats }, null, 2));
    } catch (e) {
      console.log('    competitor failed:', comp.name, e.message);
    }
  }

  history.snapshots.push(snapshot);
  writeFileSync(historyFile, JSON.stringify(history, null, 2));
  // Write session-specific + legacy root copies
  writeFileSync(join(sessionDir, 'page-analytics.json'), JSON.stringify({ ...stats, aggregateMetrics: aggr, top5, scrapedAt: snapshot.scrapedAt, sessionId }, null, 2));
  writeFileSync(join(sessionDir, 'raw-posts.json'), JSON.stringify({ posts, stats, aggregateMetrics: aggr, scrapedAt: snapshot.scrapedAt, sessionId }, null, 2));
  writeFileSync(join(projectDir, 'page-analytics.json'), JSON.stringify({ ...stats, aggregateMetrics: aggr, top5, scrapedAt: snapshot.scrapedAt, sessionId }, null, 2));
  writeFileSync(join(projectDir, 'raw-posts.json'), JSON.stringify({ posts, stats, aggregateMetrics: aggr, scrapedAt: snapshot.scrapedAt, sessionId }, null, 2));
  // Mark latest
  try { writeFileSync(join(projectDir, 'latest.json'), JSON.stringify({ sessionId, scrapedAt: snapshot.scrapedAt }, null, 2)); } catch {}

  console.log(`\n✅ Facebook scrape complete for ${projectName}`);
  console.log(`Session: ${sessionId} → ${sessionDir}`);
  console.log(`Round ${round} · Posts: ${posts.length} · History snapshots: ${history.snapshots.length}`);
  console.log('Trend:', JSON.stringify(trends.isFirst ? trends.message : trends));
  process.exit(0);
})().catch(e => {
  console.error('Scrape error:', e.message);
  process.exit(1);
});
