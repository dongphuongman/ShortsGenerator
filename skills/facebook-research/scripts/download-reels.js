// =============================================================================
// Facebook Research — Download top 5 reels via Chrome DevTools Protocol
// Navigates to each top post, extracts the <video> src, downloads with curl.
// Usage: node scripts/download-reels.js <project-name> [sessionId] [--session <id>] [--data-root <path>]
// =============================================================================

import CDP from 'chrome-remote-interface';
import { readFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { homedir } from 'os';
import { execSync } from 'child_process';

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
if (!projectName) { console.error('Usage: node scripts/download-reels.js <project-name> [sessionId]'); process.exit(1); }

const projectDir = join(dataRoot, 'projects', projectName);

// Resolve session dir: explicit or latest
let sessionDir = null;
if (sessionId) {
  sessionDir = join(projectDir, sessionId);
} else {
  try {
    const latestFile = join(projectDir, 'latest.json');
    if (existsSync(latestFile)) {
      const latest = JSON.parse(readFileSync(latestFile, 'utf8'));
      if (latest.sessionId && existsSync(join(projectDir, latest.sessionId))) sessionDir = join(projectDir, latest.sessionId);
    }
    if (!sessionDir) {
      const { readdirSync } = await import('fs');
      const entries = readdirSync(projectDir, { withFileTypes: true }).filter(d => d.isDirectory() && /^\d{4}-\d{2}-\d{2}_\d{6}$/.test(d.name)).map(d => d.name).sort();
      if (entries.length) sessionDir = join(projectDir, entries[entries.length - 1]);
    }
  } catch {}
}

function pickJson(name) {
  if (sessionDir && existsSync(join(sessionDir, name))) return join(sessionDir, name);
  return join(projectDir, name);
}

const configPath = join(projectDir, 'config.json');
if (!existsSync(configPath)) { console.error(`Project not found: ${configPath}`); process.exit(1); }
const config = JSON.parse(readFileSync(configPath, 'utf8'));
const analyticsPath = pickJson('page-analytics.json');
const analytics = existsSync(analyticsPath) ? JSON.parse(readFileSync(analyticsPath, 'utf8')) : null;

const effectiveDir = sessionDir && existsSync(sessionDir) ? sessionDir : projectDir;
const dlDir = join(effectiveDir, 'video-template', 'downloads');
mkdirSync(dlDir, { recursive: true });

const wait = ms => new Promise(r => setTimeout(r, ms));

function getPort() {
  const portFile = join(homedir(), '.browser-tools', 'port');
  if (existsSync(portFile)) return parseInt(readFileSync(portFile, 'utf8'), 10);
  return config.browserPort || 9222;
}

async function getClient() {
  const port = getPort();
  const targets = await CDP.List({ port });
  let target = targets.find(t => t.type === 'page' && /facebook\.com/.test(t.url));
  if (!target) target = await CDP.New({ port, url: 'https://www.facebook.com/' });
  await wait(5000);
  const client = await CDP({ port, target: target.id });
  await client.Page.enable();
  await client.Runtime.enable();
  return client;
}

async function evalJson(client, fn) {
  const { result } = await client.Runtime.evaluate({ expression: `(${fn})()`, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || 'Evaluation error');
  return result.value;
}

(async () => {
  const top5 = analytics?.top5 || [];
  if (!top5.length) { console.error('No top5 data. Run scrape first. Analytics path:', analyticsPath); process.exit(1); }
  console.log(`Downloading to: ${dlDir} (session: ${effectiveDir})`);
  const client = await getClient();

  for (let i = 0; i < top5.length; i++) {
    const post = top5[i];
    console.log(`[${i + 1}/${top5.length}] ${post.title || post.url}`);
    try {
      await client.Page.navigate({ url: post.url });
      await wait(8000);
      const src = await evalJson(client, `() => {
        const v = document.querySelector('video');
        if (v) return v.getAttribute('src') || v.getAttribute('data-src') || '';
        const allVideos = document.querySelectorAll('video');
        for (const el of allVideos) {
          const s = el.getAttribute('src') || el.getAttribute('data-src') || (el.querySelector('source') ? el.querySelector('source').getAttribute('src') : '');
          if (s) return s;
        }
        return '';
      }`);
      if (src && !src.startsWith('blob:')) {
        const out = join(dlDir, `post-${i + 1}.mp4`);
        execSync(`curl -sL "${src}" -o "${out}" --max-time 90`);
        console.log('  downloaded:', out);
      } else {
        console.log('  no direct src (blob or blocked) — skipping');
      }
    } catch (e) {
      console.log('  failed:', e.message);
    }
  }
  console.log('\n✅ Reels download complete:', dlDir);
  process.exit(0);
})().catch(e => { console.error(e.message); process.exit(1); });
