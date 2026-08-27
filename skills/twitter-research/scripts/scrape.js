// =============================================================================
// Twitter/X Research — Topic scraper via Chrome DevTools Protocol
// Searches X by topic, collects 10+ posts from many accounts, extracts
// engagement metrics, ranks them. Optionally augments with seed accounts.
// Usage: node scripts/scrape.js <timestamp>  (reads .twitter-research/<ts>/config.json)
// =============================================================================

import CDP from 'chrome-remote-interface';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { homedir } from 'os';

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
  let ts = null, dataRoot = null;
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
  console.error('Usage: node scripts/scrape.js <timestamp> [--session <id>] [--data-root <path>]');
  console.error('  timestamp format: YYYY-MM-DD_HHMMSS, e.g. 2026-08-25_143000');
  process.exit(1);
}
const sessionDir = join(dataRoot, timestamp);
const configFile = join(sessionDir, 'config.json');
if (!existsSync(configFile)) {
  console.error(`Session not found: ${configFile}\nRun setup first (creates .twitter-research/<timestamp>/config.json).`);
  console.error(`Looked in dataRoot: ${dataRoot}`);
  process.exit(1);
}

const config = JSON.parse(readFileSync(configFile, 'utf8'));
const outputFile = join(sessionDir, 'raw-posts.json');
mkdirSync(join(sessionDir, 'screenshots'), { recursive: true });

const topic = config.topic;
const topicKeywords = config.topicKeywords || [];
const minPosts = config.minPosts || 10;
const accounts = (config.accounts || []).filter(a => a.isSeed);
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
  let target = targets.find(t => t.type === 'page' && /x\.com|twitter\.com/.test(t.url));
  if (!target) {
    target = await CDP.New({ port, url: 'https://x.com/home' });
    await wait(6000);
  }
  const client = await CDP({ port, target: target.id });
  await client.Page.enable();
  await client.Runtime.enable();
  return client;
}

const parseCount = str => {
  if (!str) return 0;
  str = String(str).replace(/,/g, '');
  if (str.includes('K')) return parseFloat(str) * 1000;
  if (str.includes('M')) return parseFloat(str) * 1000000;
  if (str.includes('B')) return parseFloat(str) * 1000000000;
  return parseFloat(str) || 0;
};

const EXTRACT_FN = `() => {
  const tweets = document.querySelectorAll('[data-testid="tweet"]');
  const seen = new Set();
  const results = [];
  const parseCount = (str) => {
    if (!str) return 0;
    str = str.replace(/,/g, '');
    if (str.includes('K')) return parseFloat(str) * 1000;
    if (str.includes('M')) return parseFloat(str) * 1000000;
    if (str.includes('B')) return parseFloat(str) * 1000000000;
    return parseInt(str) || 0;
  };
  const getCount = (el) => {
    if (!el) return 0;
    const ariaLabel = el.getAttribute('aria-label') || '';
    const match = ariaLabel.match(/([\\d,.KMB]+)/);
    if (!match) {
      const span = el.querySelector('span[data-testid="app-text-transition-container"]');
      const text = span ? span.innerText : '';
      const m = text.match(/([\\d,.KMB]+)/);
      return m ? parseCount(m[1]) : 0;
    }
    return parseCount(match[1]);
  };
  tweets.forEach(tweet => {
    const tweetText = tweet.querySelector('[data-testid="tweetText"]') ? tweet.querySelector('[data-testid="tweetText"]').innerText : '';
    if (!tweetText || seen.has(tweetText.substring(0, 40))) return;
    seen.add(tweetText.substring(0, 40));

    const userEl = tweet.querySelector('[data-testid="User-Name"]');
    const userText = userEl ? userEl.innerText : '';
    const handleMatch = userText.match(/@(\\w+)/);
    const handle = handleMatch ? '@' + handleMatch[1] : '';

    const timeEl = tweet.querySelector('time');
    const timestamp = timeEl ? timeEl.getAttribute('datetime') : '';

    const linkEl = tweet.querySelector('a[href*="/status/"]');
    let tweetUrl = '';
    if (linkEl) {
      const href = linkEl.getAttribute('href');
      tweetUrl = href.startsWith('http') ? href : 'https://x.com' + href;
    }

    const replyEl = tweet.querySelector('[data-testid="reply"]');
    const retweetEl = tweet.querySelector('[data-testid="retweet"]');
    const likeEl = tweet.querySelector('[data-testid="like"]');
    const replies = getCount(replyEl);
    const retweets = getCount(retweetEl);
    const likes = getCount(likeEl);

    const mediaEls = tweet.querySelectorAll('img[alt*="Image"], video');
    const mediaUrls = Array.from(mediaEls).slice(0, 4).map(m => m.getAttribute('src')).filter(Boolean);

    results.push({
      handle,
      author: userText.substring(0, 60),
      text: tweetText.substring(0, 500),
      timestamp,
      url: tweetUrl,
      replies, retweets, likes,
      media: mediaUrls,
      engagement: likes + retweets * 2 + replies * 3,
      source: 'search'
    });
  });
  return JSON.stringify(results);
}`;

async function evalJson(client, fn) {
  const { result } = await client.Runtime.evaluate({
    expression: `(${fn})()`,
    awaitPromise: true,
    returnByValue: true
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || 'Evaluation error');
  }
  return JSON.parse(result.value);
}

async function scroll(client, rounds = 12) {
  const fn = `async () => {
    let lastHeight = 0;
    for (let i = 0; i < ${rounds}; i++) {
      window.scrollTo(0, document.body.scrollHeight);
      await new Promise(r => setTimeout(r, 1800));
      const h = document.body.scrollHeight;
      if (h === lastHeight) break;
      lastHeight = h;
    }
    return 'scrolled';
  }`;
  await evalJson(client, fn);
}

async function searchTopic(client, query, searchTab) {
  const url = `https://x.com/search?q=${encodeURIComponent(query)}&src=typed_query&f=${searchTab}`;
  console.log(`  Searching X: ${query} (${searchTab})`);
  await client.Page.navigate({ url });
  await wait(6000);
  await scroll(client, 12);
  return await evalJson(client, EXTRACT_FN);
}

async function scrapeProfile(client, handle) {
  const clean = handle.replace(/^@/, '');
  const url = `https://x.com/${clean}`;
  console.log(`  Visiting seed profile: @${clean}`);
  await client.Page.navigate({ url });
  await wait(5000);
  await scroll(client, 5);
  const posts = await evalJson(client, EXTRACT_FN);
  return posts
    .filter(p => {
      const t = p.text.toLowerCase();
      const kw = [topic, ...topicKeywords].map(k => k.toLowerCase());
      return kw.some(k => t.includes(k));
    })
    .map(p => ({ ...p, source: 'profile' }));
}

// MAIN
(async () => {
  const client = await getClient();
  const searchPosts = [];

  const queries = [topic, ...topicKeywords];
  const usedQueries = new Set();
  const searchTabs = ['top', 'live'];

  for (const tab of searchTabs) {
    if (searchPosts.length >= minPosts) break;
    for (const q of queries) {
      if (usedQueries.has(q)) continue;
      if (searchPosts.length >= minPosts) break;
      usedQueries.add(q);
      const results = await searchTopic(client, q, tab);
      searchPosts.push(...results);
      console.log(`    -> ${results.length} tweets collected (total ${searchPosts.length})`);
    }
  }

  let profilePosts = [];
  for (const acc of accounts) {
    if (!acc.handle) continue;
    const posts = await scrapeProfile(client, acc.handle);
    profilePosts.push(...posts);
    console.log(`    -> ${posts.length} topic-relevant tweets from @${acc.handle.replace(/^@/, '')}`);
  }

  const merged = [...searchPosts, ...profilePosts];
  const deduped = Array.from(new Map(merged.map(p => [p.url || p.text.substring(0, 40), p])).values());
  const ranked = deduped
    .filter(p => p.url)
    .sort((a, b) => b.engagement - a.engagement)
    .slice(0, Math.max(minPosts, 10));

  const distinctAccounts = new Set(ranked.map(p => p.handle).filter(Boolean));

  const output = {
    timestamp,
    topic,
    searchQueryUsed: topic,
    totalPostsCollected: ranked.length,
    distinctAccounts: distinctAccounts.size,
    minPostsRequested: minPosts,
    posts: ranked.map((p, i) => ({
      rank: i + 1,
      handle: p.handle,
      author: p.author,
      text: p.text,
      url: p.url,
      timestamp: p.timestamp,
      likes: p.likes,
      retweets: p.retweets,
      replies: p.replies,
      views: 0,
      media: p.media,
      engagementScore: p.engagement,
      source: p.source
    })),
    accountsSummary: Array.from(distinctAccounts).map(h => ({
      handle: h,
      postsCollected: ranked.filter(p => p.handle === h).length
    }))
  };

  writeFileSync(outputFile, JSON.stringify(output, null, 2));
  console.log(`\n✅ Scraped ${ranked.length} posts from ${distinctAccounts.size} accounts.`);
  console.log(`Saved: ${outputFile}`);
  process.exit(0);
})().catch(e => {
  console.error('Scrape error:', e.message);
  process.exit(1);
});
