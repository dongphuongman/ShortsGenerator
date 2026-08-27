// =============================================================================
// Reddit Research — Build MagicSync bulk-scheduling CSV
// Reads a session dir, generates a social media post per post (Flask backend or
// fallback to the viral script), validates image/video URLs, calculates optimal
// US scheduling times, writes posts.csv.
// Usage: node scripts/build-csv.js <timestamp>
// =============================================================================

import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { execSync } from 'child_process';

function resolveDataRoot(dotName = '.reddit-research', dataRootArg=null) {
  if (dataRootArg) return resolve(dataRootArg);
  const envKey = dotName.replace(/^\./,'').replace(/-/g,'_').toUpperCase()+'_ROOT';
  if (process.env[envKey]) return resolve(process.env[envKey]);
  if (process.env.REDDIT_RESEARCH_ROOT) return resolve(process.env.REDDIT_RESEARCH_ROOT);
  let dir=process.cwd();
  while (true) {
    if (existsSync(join(dir, dotName))) return join(dir, dotName);
    const parent=dirname(dir);
    if (parent===dir) break;
    dir=parent;
  }
  return join(process.cwd(), dotName);
}
function parseArgs() {
  const raw=process.argv.slice(2);
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
  return { timestamp: ts, dataRoot };
}
const { timestamp, dataRoot: _dataRoot } = parseArgs();
if (!timestamp) {
  console.error('Usage: node scripts/build-csv.js <timestamp> [--session <id>] [--data-root <path>]');
  process.exit(1);
}
const dataRoot = _dataRoot || resolveDataRoot();
const sessionDir = join(dataRoot, timestamp);
const indexFile = join(sessionDir, 'index.json');
if (!existsSync(indexFile)) {
  console.error(`Session not found: ${indexFile}`);
  console.error(`Looked in dataRoot: ${dataRoot}`);
  process.exit(1);
}

const index = JSON.parse(readFileSync(indexFile, 'utf8'));
mkdirSync(join(sessionDir, 'videos'), { recursive: true });

async function genSocialPost(post) {
  const md = readFileSync(join(sessionDir, post.file), 'utf8');
  const scriptMatch = md.match(/```\n([\s\S]*?)\n```/);
  const script = scriptMatch ? scriptMatch[1] : '';
  const title = post.title;
  const extraPrompt =
    'Genera un post viral para redes sociales (Facebook/Instagram/LinkedIn/X) en español basado en este contenido. Debe tener gancho, incluir 3-5 hashtags relevantes, máximo 300 caracteres. No uses markdown ni formato, solo texto plano.\n\n' +
    'TÍTULO: ' + title + '\n\nCONTENIDO: ' + (md.split('## Viral')[0] || '') + '\n\nGUIÓN: ' + script;
  try {
    const resp = await fetch('http://localhost:8080/api/script', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ videoSubject: title, extraPrompt, aiModel: 'g4f', scriptTemplate: 'viral_shorts' })
    });
    if (resp.ok) {
      const data = await resp.json();
      const text = (data.script || data.script_text || JSON.stringify(data)).trim();
      if (text) return text;
    }
  } catch (e) {}
  return (script ? script.split('\n').slice(0, 3).join(' ') : title) + '\n\n#viral #reddit';
}

function csvEscape(s) {
  return '"' + String(s).replace(/"/g, '""') + '"';
}

async function contentType(url) {
  try {
    const resp = await fetch(url, { method: 'HEAD', redirect: 'follow' });
    return resp.headers.get('content-type') || '';
  } catch (e) { return ''; }
}

// Find image/video URLs for a post by priority
async function resolveMedia(post, md) {
  const candidates = [];
  const videoMatch = md.match(/## Videos\s*\n- (.+)/);
  if (videoMatch) candidates.push({ url: videoMatch[1].trim(), kind: 'video' });
  const sourcedMatch = md.match(/## Sourced Videos[\s\S]*?```?/);
  const sourced = md.match(/## Sourced Videos\n([\s\S]*?)(?=\n## |$)/);
  if (sourced) {
    for (const m of sourced[1].matchAll(/\[([^\]]*)\]\(([^)]+)\)/g)) candidates.push({ url: m[2], kind: 'video' });
  }
  candidates.push({ url: post.url, kind: 'link' });
  for (const c of candidates) {
    const ct = await contentType(c.url);
    if (ct.startsWith('image/')) return { imageUrl: c.url };
    if (ct.startsWith('video/')) return { videoUrl: c.url, ct };
  }
  return {};
}

function nextSlot(dateStr) {
  // Produce ISO 8601 UTC times distributed across US-optimal slots
  const nowMs = Date.now();
  const slots = ['09:00', '10:00', '11:00', '13:00', '19:00', '20:00', '21:00', '08:00', '12:00'];
  const d = new Date(nowMs + 60 * 60 * 1000);
  d.setUTCHours(0, 0, 0, 0);
  const offset = (dateStr.charCodeAt(0) + dateStr.charCodeAt(dateStr.length - 1)) % slots.length;
  d.setDate(d.getDate() + Math.floor(offset / 2));
  const [h, m] = slots[offset].split(':').map(Number);
  d.setUTCHours(h + 5, m, 0, 0); // EST -> UTC
  return d.toISOString();
}

(async () => {
  const rows = [];
  const localVideos = [];
  let i = 0;
  for (const post of index.posts) {
    const md = readFileSync(join(sessionDir, post.file), 'utf8');
    const content = await genSocialPost(post);
    const media = await resolveMedia(post, md);
    let imageUrl = media.imageUrl || '';
    if (media.videoUrl) {
      const file = join(sessionDir, 'videos', post.file.replace('.md', '.mp4'));
      try {
        execSync(`curl -sL "${media.videoUrl}" -o "${file}" --max-time 60`);
        localVideos.push({ title: post.title, file });
      } catch (e) {}
    }
    rows.push({ content, image_url: imageUrl, scheduled_time: nextSlot(post.title + i) });
    i++;
  }

  const csv = ['content,image_url,scheduled_time',
    ...rows.map(r => [csvEscape(r.content), r.image_url, r.scheduled_time].join(','))].join('\n');
  const csvFile = join(sessionDir, 'posts.csv');
  writeFileSync(csvFile, csv);

  console.log('✅ CSV Generation Complete!');
  console.log(`Session: ${sessionDir}/`);
  console.log(`Total posts: ${rows.length}`);
  console.log(`CSV file: ${csvFile}`);
  if (localVideos.length) {
    console.log('⚠️  Posts with local video downloads (need manual image_url update):');
    for (const v of localVideos) console.log(`  - ${v.title} -> ${v.file}`);
  }
})().catch(e => {
  console.error('CSV error:', e.message);
  process.exit(1);
});
