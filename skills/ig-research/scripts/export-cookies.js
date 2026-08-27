#!/usr/bin/env node
import CDP from 'chrome-remote-interface';
import { writeFileSync } from 'fs';

const [,, portStr] = process.argv;
const port = parseInt(portStr || '9222');

async function main() {
  const client = await CDP({ port });
  await client.Network.enable();

  const cookies = await client.Network.getAllCookies();
  const nc = [];
  for (const c of cookies.cookies) {
    nc.push(`${c.domain}\tTRUE\t${c.path}\t${c.secure ? 'TRUE' : 'FALSE'}\t${Math.floor(c.expires || 0)}\t${c.name}\t${c.value}`);
  }
  writeFileSync('/tmp/instagram_cookies.txt', '# Netscape HTTP Cookie File\n' + nc.join('\n'));
  console.log(`Exported ${nc.length} cookies`);
  await client.close();
}

main().catch(e => { console.error(e.message); process.exit(1); });
