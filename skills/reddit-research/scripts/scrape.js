// =============================================================================
// Reddit Research — Scraper via Reddit JSON API
// Gets CORRECT upvotes/comment counts (the HTML shows 1), extracts top comments,
// generates a viral Spanish script via the local Flask backend, writes markdown.
// Usage: node scripts/scrape.js <subreddit> [limit] [sort] [lang] [--session <id>] [--data-root <path>]
//   e.g. node scripts/scrape.js soccer 10 hot es
//   e.g. node scripts/scrape.js soccer --session 2026-08-25_143000 --data-root /tmp/myproj/.reddit-research
//   Bundled inside skill: resolves dataRoot via CWD walk-up, env, or --data-root.
// =============================================================================

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname, resolve } from 'path';

function resolveDataRoot(dotName = '.reddit-research', dataRootArg = null) {
  if (dataRootArg) return resolve(dataRootArg);
  const envKey = dotName.replace(/^\./, '').replace(/-/g, '_').toUpperCase() + '_ROOT';
  if (process.env[envKey]) return resolve(process.env[envKey]);
  if (process.env.REDDIT_RESEARCH_ROOT) return resolve(process.env.REDDIT_RESEARCH_ROOT);
  let dir = process.cwd();
  while (true) {
    if (existsSync(join(dir, dotName))) return join(dir, dotName);
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return join(process.cwd(), dotName);
}

function parseRedditArgs() {
  const raw = process.argv.slice(2);
  let subreddit = null, limit = '10', sort = 'hot', lang = 'es', dataRoot = null, sessionId = null;
  const tsRe = /^\d{4}-\d{2}-\d{2}_\d{6}$/;
  for (let i = 0; i < raw.length; i++) {
    const a = raw[i];
    if (a === '--data-root' && raw[i + 1]) { dataRoot = raw[++i]; continue; }
    if (a.startsWith('--data-root=')) { dataRoot = a.split('=')[1]; continue; }
    if (a === '--session' && raw[i + 1]) { sessionId = raw[++i]; continue; }
    if (a.startsWith('--session=')) { sessionId = a.split('=')[1]; continue; }
    if (a.startsWith('--')) continue;
    if (!subreddit) subreddit = a;
    else if (tsRe.test(a) && !sessionId) sessionId = a;
    else if (/^[0-9]+$/.test(a) && limit === '10') limit = a;
    else if (['hot', 'new', 'top', 'rising', 'controversial'].includes(a) && sort === 'hot') sort = a;
    else if (['es', 'en', 'fr', 'de'].includes(a) && lang === 'es') lang = a;
    else if (limit === '10') limit = a;
    else if (sort === 'hot') sort = a;
    else if (lang === 'es') lang = a;
  }
  return { subreddit, limit, sort, lang, dataRoot, sessionId };
}

const { subreddit, limit, sort, lang, dataRoot: _dataRootArg, sessionId: _sessionArg } = parseRedditArgs();
if (!subreddit) {
  console.error('Usage: node scripts/scrape.js <subreddit> [limit] [sort] [lang] [--session <id>] [--data-root <path>]');
  process.exit(1);
}

const UA = { headers: { 'User-Agent': 'Mozilla/5.0' } };

function slugify(title) {
  return title
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
    .substring(0, 60);
}

function now() {
  return new Date().toISOString().replace('T', ' ').substring(0, 19);
}

async function fetchJson(url) {
  const resp = await fetch(url, UA);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return resp.json();
}

async function genScript({ title, selftext, comments }) {
  const extraPrompt =
    'Genera un guion viral en ' + (lang === 'es' ? 'español' : lang) +
    ' para YouTube Shorts basado en ESTE contenido exacto de Reddit:\n\n' +
    'TÍTULO: ' + title + '\n\nCONTENIDO: ' + (selftext || '') +
    '\n\nCOMENTARIOS DESTACADOS:\n' +
    comments.slice(0, 10).map(c => '- "' + c.body + '" (' + c.score + ' pts)').join('\n') +
    '\n\nUsa los comentarios más populares como parte del guion. Hazlo emocionante, estilo viral, con gancho al inicio. Máximo 60 segundos de duración.';
  try {
    const resp = await fetch('http://localhost:8080/api/script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ videoSubject: title, extraPrompt, aiModel: 'g4f', scriptTemplate: 'viral_shorts' })
    });
    if (!resp.ok) return '';
    const data = await resp.json();
    return (data.script || data.script_text || JSON.stringify(data)).trim();
  } catch (e) {
    return '';
  }
}

(async () => {
  const listingUrl = `https://www.reddit.com/r/${subreddit}/${sort}.json?limit=${limit}`;
  console.log('Fetching listing:', listingUrl);
  const listing = await fetchJson(listingUrl);
  const posts = listing.data.children.map(c => c.data).filter(p => p && p.url);

  const dataRoot = resolveDataRoot('.reddit-research', _dataRootArg);
  const ts = _sessionArg || new Date().toISOString().slice(0, 19).replace('T', '_').replace(/:/g, '');
  const sessionDir = join(dataRoot, ts);
  mkdirSync(sessionDir, { recursive: true });

  const index = { timestamp: ts, subreddit, sort, posts: [] };

  for (let i = 0; i < posts.length; i++) {
    const p = posts[i];
    const slug = slugify(p.title);
    console.log(`[${i + 1}/${posts.length}] ${p.title}`);
    let post = p, comments = [];
    try {
      const detail = await fetchJson(`https://www.reddit.com${p.permalink}.json`);
      post = detail[0].data.children[0].data || p;
      const walk = (children, depth = 0) => {
        if (!children || depth > 2) return;
        for (const c of children) {
          const d = c.data || {};
          if (d.body && comments.length < 10) comments.push({ author: d.author, body: d.body, score: d.ups, depth: d.depth });
          if (d.replies?.data?.children) walk(d.replies.data.children, depth + 1);
        }
      };
      walk(detail[1]?.data?.children || []);
    } catch (e) {
      console.log('    (could not fetch detail, using listing data)');
    }

    const script = await genScript({ title: post.title, selftext: post.selftext, comments });

    const md = [
      `# ${post.title}`,
      '',
      `**Author**: ${post.author}`,
      `**Upvotes**: ${post.ups}`,
      `**Comments**: ${post.num_comments}`,
      `**Source**: https://www.reddit.com${post.permalink}`,
      `**Scraped**: ${now()}`,
      '',
      '## Content',
      '',
      post.selftext || (post.url ? `(link/video post — ${post.url})` : ''),
      '',
      '## Viral Video Script (' + (lang === 'es' ? 'Spanish' : lang) + ')',
      '',
      script ? '```\n' + script + '\n```' : '*(no script generated — backend unavailable)*',
      '',
      '## Videos',
      '',
      post.media?.reddit_video?.fallback_url ? `- ${post.media.reddit_video.fallback_url}` : '- (none)',
      '',
      '## Sourced Videos',
      '',
      '*(Populated in Phase 2 — search DuckDuckGo for videos related to this topic)*',
      '',
      '## Top Comments',
      ''
    ].join('\n');

    const commentsMd = comments.map((c, i) => `### Comment ${i + 1} — ${c.author} (${c.score} pts)\n${c.body}`).join('\n\n');
    writeFileSync(join(sessionDir, `${slug}.md`), md + commentsMd + '\n');
    index.posts.push({ index: i, title: post.title, file: `${slug}.md`, url: `https://www.reddit.com${post.permalink}`, upvotes: post.ups, comments: post.num_comments });
  }

  writeFileSync(join(sessionDir, 'index.json'), JSON.stringify(index, null, 2));
  console.log(`\n✅ Scraped ${posts.length} posts into ${sessionDir}/`);
  console.log(`Session: ${ts} — DataRoot: ${dataRoot}`);
})().catch(e => {
  console.error('Scrape error:', e.message);
  process.exit(1);
});
