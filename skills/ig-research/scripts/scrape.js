
//#!/usr/bin / env node
// =============================================================================
// Instagram Research — Single-pass scraper
// For each post: navigate → engagement + caption → screenshots → audio → next
// One visit per post. No second pass.
// Usage: node scripts/scrape.js <project-name>
// =============================================================================

import CDP from 'chrome-remote-interface';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { execSync } from 'child_process';
import { homedir } from 'os';

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
function genTimestamp() { return new Date().toISOString().slice(0, 19).replace('T', '_').replace(/:/g, ''); }
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
  return { projectName, sessionId: sessionId || genTimestamp(), dataRoot: dataRoot || resolveDataRoot() };
}
const { projectName, sessionId, dataRoot } = parseArgs();
if (!projectName) {
  console.error('Usage: node scripts/scrape.js <project-name> [sessionId] [--session <id>] [--data-root <path>]');
  process.exit(1);
}
const projectDir = join(dataRoot, 'projects', projectName);
const sessionDir = join(projectDir, sessionId);
mkdirSync(sessionDir, { recursive: true });
const configFile = join(projectDir, 'config.json');
if (!existsSync(configFile)) {
  console.error(`Project not found: ${configFile}\nCreate a config.json first (skill ig-research-setup).`);
  process.exit(1);
}
const config = JSON.parse(readFileSync(configFile, 'utf8'));
const outputFile = join(sessionDir, 'raw-posts.json');
const transcriptsDir = join(sessionDir, 'transcripts');
const hooksDir = join(sessionDir, 'hook-screenshots');
[transcriptsDir, hooksDir, sessionDir].forEach(d => { if (!existsSync(d)) mkdirSync(d, { recursive: true }); });

const wait = ms => new Promise(r => setTimeout(r, ms));

function getPort() {
  const portNum = config.browserPort || 9222;
  // Try the port file first, fall back to config port
  const portFile = join(homedir(), '.browser-tools', 'port');
  if (existsSync(portFile)) {
    return parseInt(readFileSync(portFile, 'utf8'));
  }
  return portNum;
}

async function getClient() {
  const port = getPort();
  let targets;
  try {
    targets = await CDP.List({ port });
  } catch (e) {
    console.error(`\nCannot connect to Chrome on port ${port}.`);
    console.error('Make sure Chrome is running with: --remote-debugging-port=9222');
    console.error('Close Chrome completely, then relaunch it with that flag.\n');
    process.exit(1);
  }
  let target = targets.find(t => t.type === 'page' && t.url.includes('instagram.com'));
  if (!target) {
    target = await CDP.New({ port, url: 'https://www.instagram.com/' });
    await wait(5000);
  }
  const client = await CDP({ port, target: target.id });
  await client.Page.enable();
  await client.Runtime.enable();
  await client.DOM.enable();
  return client;
}

// Collect post links from a hashtag search page
async function collectSearchPosts(client, searchTerm, maxPosts) {
  const searchUrl = `https://www.instagram.com/explore/tags/${searchTerm.replace(/\s+/g, '').replace(/^#/, '')}/`;
  console.log(`  Navigating to: ${searchUrl}`);
  await client.Page.navigate({ url: searchUrl });
  await wait(5000);

  const scrollRounds = Math.ceil(maxPosts / 12);
  for (let i = 0; i < scrollRounds; i++) {
    await client.Runtime.evaluate({ expression: 'window.scrollBy(0, 1500)' });
    await wait(2000);
  }

  const postLinks = await client.Runtime.evaluate({
    expression: `
      (() => {
        const links = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
        const hrefs = [];
        const seen = new Set();
        for (const l of links) {
          const h = l.getAttribute('href');
          if (!seen.has(h)) { seen.add(h); hrefs.push(h); }
          if (hrefs.length >= ${maxPosts}) break;
        }
        return hrefs;
      })()
    `,
    returnByValue: true
  });
  return postLinks.result.value;
}

// Collect post links from a profile page
async function collectProfilePosts(client, profileUrl, maxPosts) {
  console.log(`  Navigating to: ${profileUrl}`);
  await client.Page.navigate({ url: profileUrl });
  await wait(5000);
  await client.Runtime.evaluate({ expression: 'window.scrollBy(0, 800)' });
  await wait(2000);

  const postLinks = await client.Runtime.evaluate({
    expression: `
      (() => {
        const links = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
        const hrefs = [];
        const seen = new Set();
        for (const l of links) {
          const h = l.getAttribute('href');
          if (!seen.has(h)) { seen.add(h); hrefs.push(h); }
          if (hrefs.length >= ${maxPosts}) break;
        }
        return hrefs;
      })()
    `,
    returnByValue: true
  });
  return postLinks.result.value;
}

// =============================================================================
// SINGLE-PASS: scrape + screenshot + audio for ONE post
// =============================================================================
async function processPost(client, href, source) {
  const postId = href.match(/\/(p|reel)\/([\w-]+)/)?.[2] || '';
  const postUrl = href.startsWith('http') ? href : 'https://www.instagram.com' + href;
  const audioFile = join(transcriptsDir, `${postId}.m4a`);
  const ssFile0 = join(hooksDir, `${postId}_0s.jpg`);

  // Skip if fully processed already
  if (existsSync(audioFile) && existsSync(ssFile0)) {
    return { postId, skipped: true };
  }

  // 1. Navigate to post — wait for content to load, then pause video
  await client.Page.navigate({ url: postUrl });
  await wait(2000);

  // Wait for post content to actually render (spans with engagement data or caption)
  for (let attempt = 0; attempt < 20; attempt++) {
    const loaded = await client.Runtime.evaluate({
      expression: `(() => { const spans = document.querySelectorAll('span'); for (const s of spans) { if (s.textContent.match(/^[\\\\d,.]+[KkMm]?$/) && s.textContent.trim() !== '0') return true; } return false; })()`,
      returnByValue: true
    });
    if (loaded.result.value) break;
    await wait(500);
  }

  // Pause video to capture true first frames
  for (let attempt = 0; attempt < 15; attempt++) {
    const paused = await client.Runtime.evaluate({
      expression: `(() => { const v = document.querySelector('video'); if(v) { v.pause(); v.muted = true; return true; } return false; })()`,
      returnByValue: true
    });
    if (paused.result.value) break;
    await wait(300);
  }
  await wait(1000);

  // 2. Extract engagement + caption + author
  const data = await client.Runtime.evaluate({
    expression: `
      (() => {
        const result = { url: window.location.href };

        // Engagement — raw numbers from spans
        const allSpans = document.querySelectorAll('span');
        const rawNumbers = [];
        for (const el of allSpans) {
          const t = el.textContent.trim();
          if (t.match(/^[\\d,.]+[KkMm]?$/) && t.length < 15 && t !== '0') {
            rawNumbers.push(t);
          }
          if (t.match(/^Liked by/i) && !result.likesContext) result.likesContext = t.substring(0, 150);
          if (t.match(/^[\\d,.]+[KM]?\\s+views?$/i) && !result.views) result.views = t;
          if (t.match(/^View all (\\d[\\d,]*) comments/i) && !result.comments) result.comments = t;
        }

        const uniqueNums = [...new Set(rawNumbers)];
        result.rawNumbers = uniqueNums.slice(0, 10);
        if (uniqueNums.length >= 1) result.likes = uniqueNums[0];
        if (uniqueNums.length >= 2) result.commentsCount = uniqueNums[1];
        if (uniqueNums.length >= 3) result.shares = uniqueNums[2];

        // Caption
        const h1 = document.querySelector('h1');
        result.caption = h1 ? h1.textContent.substring(0, 500) : '';
        if (!result.caption) {
          const spans = document.querySelectorAll('span[dir="auto"]');
          for (const s of spans) {
            if (s.textContent.length > 20 && s.textContent.length < 5000) {
              result.caption = s.textContent.substring(0, 500);
              break;
            }
          }
        }
        result.fullCaption = h1 ? h1.textContent : '';
        if (!result.fullCaption) {
          const spans = document.querySelectorAll('span[dir="auto"]');
          for (const s of spans) {
            if (s.textContent.length > 20) { result.fullCaption = s.textContent; break; }
          }
        }

        // Type, date, author
        result.type = document.querySelector('video') ? 'reel' : 'image';
        const timeEl = document.querySelector('time[datetime]');
        result.date = timeEl ? timeEl.getAttribute('datetime') : '';
        result.dateText = timeEl ? timeEl.textContent : '';

        // Author: find first profile link whose visible text matches the username
        const allPageLinks = document.querySelectorAll('a[href]');
        let foundAuthor = '';
        for (const a of allPageLinks) {
          const href = a.getAttribute('href') || '';
          if (href.length > 2 && href[0] === '/' && href[href.length - 1] === '/' && href.indexOf('/', 1) === href.length - 1) {
            const username = href.slice(1, -1);
            const text = a.textContent.trim().toLowerCase().replace('verified', '');
            if (text === username.toLowerCase()) {
              foundAuthor = username;
              break;
            }
          }
        }
        result.author = foundAuthor;

        return result;
      })()
    `,
    returnByValue: true
  });

  const post = data.result.value;
  if (!post) {
    console.log('failed (page did not load)');
    return { postId, skipped: true };
  }
  post.href = href;
  post.source = source;
  post.postId = postId;

  // 3. Screenshots (only for reels)
  if (post.type === 'reel' && !existsSync(ssFile0)) {
    try {
      // Video is already paused from page load — just seek and screenshot
      for (const sec of [0, 1, 2]) {
        const ssFile = join(hooksDir, `${postId}_${sec}s.jpg`);
        await client.Runtime.evaluate({
          expression: `(() => { const v = document.querySelector('video'); if(v) { v.currentTime = ${sec}; } })()`,
        });
        await wait(800);
        const ss = await client.Page.captureScreenshot({ format: 'jpeg', quality: 70 });
        writeFileSync(ssFile, Buffer.from(ss.data, 'base64'));
      }
      post.hasScreenshots = true;
    } catch (e) {
      post.hasScreenshots = false;
    }
  }

  // 4. Audio download (only for reels)
  if (post.type === 'reel' && !existsSync(audioFile)) {
    try {
      execSync(
        `python3 -m yt_dlp --format worstaudio --no-warnings --quiet -o "${audioFile}" "${postUrl}"`,
        { timeout: 45000, stdio: 'pipe' }
      );
      post.hasAudio = existsSync(audioFile);
    } catch (e) {
      post.hasAudio = false;
    }
  }

  return post;
}

// Parse engagement string to number for sorting
function parseEngagement(post) {
  const likeStr = post.likes || post.likesFromBtn || '';
  const match = likeStr.match(/([\d,.]+)\s*([KkMm])?/);
  if (!match) return 0;
  let num = parseFloat(match[1].replace(/,/g, ''));
  if (match[2]?.match(/[Kk]/)) num *= 1000;
  if (match[2]?.match(/[Mm]/)) num *= 1000000;
  return num;
}

// =============================================================================
// Main
// =============================================================================
(async () => {
  try {
    const client = await getClient();
    const allPosts = [];

    // Search terms
    for (const term of config.searchTerms) {
      console.log(`\n========================================`);
      console.log(`  Searching: "${term}"`);
      console.log(`========================================`);

      const links = await collectSearchPosts(client, term, config.maxPostsPerSearch || 50);
      console.log(`  Found ${links.length} posts\n`);

      for (let i = 0; i < links.length; i++) {
        const postId = links[i].match(/\/(p|reel)\/([\w-]+)/)?.[2] || '';
        process.stdout.write(`  [${i + 1}/${links.length}] ${postId} — `);

        const post = await processPost(client, links[i], `search:${term}`);
        if (post.skipped) {
          console.log('skipped (done)');
        } else {
          const eng = post.likes || 'no data';
          const ss = post.hasScreenshots ? 'ss' : '';
          const audio = post.hasAudio ? 'audio' : '';
          console.log(`[${post.type}] ${eng} ${[ss, audio].filter(Boolean).join(' ')}`);
          allPosts.push(post);
        }
      }
    }

    // Competitor profiles
    for (const profileUrl of (config.competitors || [])) {
      const handle = profileUrl.match(/instagram\.com\/([^/]+)/)?.[1] || profileUrl;
      console.log(`\n========================================`);
      console.log(`  Competitor: @${handle}`);
      console.log(`========================================`);

      const links = await collectProfilePosts(client, profileUrl, config.maxCompetitorPosts || 10);
      console.log(`  Found ${links.length} posts\n`);

      for (let i = 0; i < links.length; i++) {
        const postId = links[i].match(/\/(p|reel)\/([\w-]+)/)?.[2] || '';
        process.stdout.write(`  [${i + 1}/${links.length}] ${postId} — `);

        const post = await processPost(client, links[i], `competitor:@${handle}`);
        if (post.skipped) {
          console.log('skipped (done)');
        } else {
          const eng = post.likes || 'no data';
          console.log(`[${post.type}] ${eng}`);
          allPosts.push(post);
        }
      }
    }

    // Deduplicate
    const seen = new Set();
    const unique = allPosts.filter(p => {
      const key = p.href || p.url;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    unique.sort((a, b) => parseEngagement(b) - parseEngagement(a));

    const output = {
      project: config.name,
      niche: config.niche,
      scrapedAt: new Date().toISOString(),
      sessionId,
      searchTerms: config.searchTerms,
      competitors: config.competitors,
      totalPosts: unique.length,
      reels: unique.filter(p => p.type === 'reel').length,
      images: unique.filter(p => p.type === 'image').length,
      posts: unique
    };

    writeFileSync(outputFile, JSON.stringify(output, null, 2));
    // legacy copy at projectDir for back-compat
    try { writeFileSync(join(projectDir, 'raw-posts.json'), JSON.stringify(output, null, 2)); } catch {}
    try { writeFileSync(join(projectDir, 'latest.json'), JSON.stringify({ sessionId, scrapedAt: output.scrapedAt }, null, 2)); } catch {}

    console.log(`\n========================================`);
    console.log(`  Complete!`);
    console.log(`  Total: ${unique.length} unique posts`);
    console.log(`  Reels: ${output.reels} | Images: ${output.images}`);
    console.log(`  Screenshots: ${hooksDir}`);
    console.log(`  Audio: ${transcriptsDir}`);
    console.log(`  Data: ${outputFile}`);
    console.log(`  Session: ${sessionDir}`);
    console.log(`========================================`);

    await client.close();
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();