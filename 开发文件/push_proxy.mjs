// 极简 CONNECT 代理：把 github.com:443 的流量转发到可用的 GitHub IP，绕过本机 hosts
import net from 'node:net';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.dirname(fileURLToPath(import.meta.url));
try { fs.writeFileSync(path.join(DIR, '.proxy.pid'), String(process.pid)); } catch (e) {}

const LISTEN = { host: '127.0.0.1', port: 8443 };
const IPS = process.env.GH_IP
  ? [process.env.GH_IP]
  : ['20.27.177.113', '20.205.243.166', '140.82.112.3', '140.82.113.3', '140.82.114.3', '140.82.121.3'];

let good = 0;

function tryConnect(chunk, head, client, idx) {
  if (idx >= IPS.length) {
    try { client.end('HTTP/1.1 502 Bad Gateway\r\n\r\n'); } catch (e) {}
    return;
  }
  const upstream = net.connect({ host: IPS[idx], port: 443 });
  let done = false;

  upstream.once('connect', () => {
    done = true;
    good = idx;
    client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
    const rest = chunk.subarray(head.indexOf('\r\n\r\n') + 4);
    if (rest.length) upstream.write(rest);
    client.pipe(upstream);
    upstream.pipe(client);
  });

  upstream.once('error', () => {
    if (done) return;
    try { upstream.destroy(); } catch (e) {}
    tryConnect(chunk, head, client, idx + 1);
  });

  client.on('error', () => { try { upstream.destroy(); } catch (e) {} });
}

const server = net.createServer((client) => {
  client.once('data', (chunk) => {
    const head = chunk.toString('latin1');
    if (!/^CONNECT\s+/i.test(head)) { client.end('HTTP/1.1 400 Bad Request\r\n\r\n'); return; }
    tryConnect(chunk, head, client, good);
  });
});

server.listen(LISTEN.port, LISTEN.host, () => {
  console.log(`proxy on ${LISTEN.host}:${LISTEN.port} -> ${IPS[good]}:443`);
});
