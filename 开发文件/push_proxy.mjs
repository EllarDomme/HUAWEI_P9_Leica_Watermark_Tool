// 极简 CONNECT 代理：把 github.com:443 的流量转发到固定 IP，绕过本机 hosts
import net from 'node:net';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.dirname(fileURLToPath(import.meta.url));
try { fs.writeFileSync(path.join(DIR, '.proxy.pid'), String(process.pid)); } catch (e) {}

const LISTEN = { host: '127.0.0.1', port: 8443 };
const TARGET_IP = process.env.GH_IP || '140.82.112.3';

const server = net.createServer((client) => {
  client.once('data', (chunk) => {
    const head = chunk.toString('latin1');
    const m = head.match(/^CONNECT\s+([^\s:]+):(\d+)\s+HTTP/i);
    if (!m) { client.end('HTTP/1.1 400 Bad Request\r\n\r\n'); return; }
    const upstream = net.connect({ host: TARGET_IP, port: 443 }, () => {
      client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
      upstream.write(chunk.subarray(head.indexOf('\r\n\r\n') + 4));
      client.pipe(upstream);
      upstream.pipe(client);
    });
    upstream.on('error', () => { try { client.destroy(); } catch (e) {} });
    client.on('error', () => { try { upstream.destroy(); } catch (e) {} });
  });
});

server.listen(LISTEN.port, LISTEN.host, () => {
  console.log(`proxy on ${LISTEN.host}:${LISTEN.port} -> ${TARGET_IP}:443`);
});
