import fs from 'node:fs';

const PORT = 9333;
const FILE_URL = 'file:///E:/DeskTop/P9%E5%BE%95%E5%8D%A1%E6%B0%B4%E5%8D%B0%E5%B7%A5%E5%85%B7/index.html';

async function getJSON(url) {
  const r = await fetch(url);
  return r.json();
}

let targets = null;
for (let i = 0; i < 60; i++) {
  try {
    targets = await getJSON(`http://127.0.0.1:${PORT}/json/list`);
    if (targets && targets.length) break;
  } catch (e) { /* not ready */ }
  await new Promise(r => setTimeout(r, 250));
}
if (!targets) { console.error('CDP not reachable'); process.exit(1); }
const page = targets.find(t => t.type === 'page') || targets[0];

const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let id = 0;
const pending = new Map();
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
};
function send(method, params = {}) {
  return new Promise((res) => {
    const i = ++id;
    pending.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
}

await send('Page.enable');
await send('Runtime.enable');
await send('Page.navigate', { url: FILE_URL });
await new Promise(r => setTimeout(r, 2500));
// 清空旧存档，保证测试从默认状态开始
await send('Runtime.evaluate', { expression: 'localStorage.clear()' });
await send('Page.reload');
await new Promise(r => setTimeout(r, 2500));

const img = fs.readFileSync('E:/DeskTop/P9徕卡水印工具/开发文件/demo.jpg').toString('base64');
await send('Runtime.evaluate', { expression: `window.__TEST_IMG__ = "data:image/jpeg;base64,${img}"` });

const body = fs.readFileSync('E:/DeskTop/P9徕卡水印工具/开发文件/tests/test_body.js', 'utf8');
const out = await send('Runtime.evaluate', {
  expression: body,
  awaitPromise: true,
  returnByValue: true,
  timeout: 180000
});

if (out.result && out.result.exceptionDetails) {
  console.error('EXCEPTION', JSON.stringify(out.result.exceptionDetails, null, 2));
  process.exit(2);
}
const val = out.result && out.result.result && out.result.result.value;

// 重载后检查预设与自动存档是否还在
await send('Page.reload');
await new Promise(r => setTimeout(r, 3000));
const chk = await send('Runtime.evaluate', {
  expression: `(function(){
    var sel = document.getElementById('presetSel');
    var names = Array.prototype.map.call(sel.options, function(o){ return o.textContent; });
    var brandEl = document.querySelector('[data-f="brand"]');
    var dateEl = document.querySelector('[data-f="date"]');
    var on = document.querySelector('.tpl.is-on');
    var res = localStorage.getItem('exifwm.presets.v1');
    return {
      presetNames: names,
      presetCount: res ? JSON.parse(res).length : 0,
      brand: brandEl ? brandEl.value : '',
      date: dateEl ? dateEl.value : '',
      template: on ? on.getAttribute('data-tpl') : '',
      autosave: !!localStorage.getItem('exifwm.autosave.v1')
    };
  })()`,
  returnByValue: true
});

console.log('RESULT_JSON_START');
console.log(JSON.stringify(val, null, 1));
console.log('RESULT_JSON_END');
console.log('RELOAD_JSON_START');
console.log(JSON.stringify(chk.result && chk.result.result && chk.result.result.value, null, 1));
console.log('RELOAD_JSON_END');
ws.close();
process.exit(0);
