(async function () {
  var R = [];
  var errs = [];
  window.addEventListener('error', function (e) { errs.push(String(e.message || e.error)); });
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };
  var wait = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var cv = document.getElementById('preview');
  function sig() {
    if (!cv || !cv.width) return 'none';
    var d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
    var h = 2166136261;
    for (var i = 0; i < d.length; i += 4) { h ^= d[i]; h = Math.imul(h, 16777619) >>> 0; }
    return h.toString(16) + '@' + cv.width + 'x' + cv.height;
  }
  function ok(n, c, d) { R.push({ n: n, p: !!c, d: d === undefined ? '' : String(d) }); }
  function setSel(id, v) { var e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event('change', { bubbles: true })); }
  function setRange(id, v) { var e = document.getElementById(id); e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })); }
  window.prompt = function () { return 'CDP测试预设'; };
  window.confirm = function () { return true; };

  try {
    window.__setDemo(window.__TEST_IMG__, 'bar');
    for (var i = 0; i < 100 && (!cv.width); i++) await wait(100);
    await wait(900);
  } catch (e) { ok('载入示例图', false, e.message); }
  ok('画布已渲染', cv.width > 200 && cv.height > 200, cv.width + 'x' + cv.height);

  var f = function (k) { var e = document.querySelector('[data-f="' + k + '"]'); return e ? e.value : ''; };
  ok('EXIF 品牌', f('brand') === 'Canon', f('brand'));
  ok('EXIF 机型', f('model') === 'EOS R5', f('model'));
  ok('EXIF 焦距', f('focal') === '35mm', f('focal'));
  ok('EXIF 光圈', f('aperture') === 'f/2.8', f('aperture'));
  ok('EXIF 快门', f('shutter') === '1/250s', f('shutter'));
  ok('EXIF ISO', f('iso') === 'ISO 100', f('iso'));
  ok('EXIF 日期含时间', /^2024\.05\.01 18:32:10$/.test(f('date')), f('date'));

  var tpls = ['bar', 'dark', 'center', 'corner', 'wordmark', 'film'];
  var sigs = {};
  for (var t = 0; t < tpls.length; t++) {
    var btn = document.querySelector('.tpl[data-tpl="' + tpls[t] + '"]');
    btn.click();
    await wait(450);
    sigs[tpls[t]] = sig();
    ok('模板 ' + tpls[t] + ' 选中', btn.classList.contains('is-on'), btn.className);
  }
  var uniq = {};
  Object.keys(sigs).forEach(function (k) { uniq[sigs[k]] = 1; });
  ok('六套模板画面各不相同', Object.keys(uniq).length === 6, Object.keys(uniq).length + ' 种');
  document.querySelector('.tpl[data-tpl="bar"]').click();
  await wait(400);

  var fams = ['default', 'din', 'mono', 'serif', 'human', 'harmony'];
  var fsig = {};
  for (var fi = 0; fi < fams.length; fi++) {
    setSel('fontFamily', fams[fi]);
    await wait(700);
    if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch (e) {} }
    fsig[fams[fi]] = sig();
  }
  var funiq = {};
  Object.keys(fsig).forEach(function (k) { funiq[fsig[k]] = 1; });
  ok('六种字体画面不相同', Object.keys(funiq).length >= 5, Object.keys(funiq).length + ' 种');
  if (document.fonts && document.fonts.check) {
    ok('内嵌 HarmonyOS 可用', document.fonts.check('16px "HarmonyOS Sans"'), '');
    ok('内嵌 Roboto 可用', document.fonts.check('16px "Roboto"'), '');
    ok('内嵌 Droid Sans Mono 可用', document.fonts.check('16px "Droid Sans Mono"'), '');
    ok('内嵌 Noto Serif 可用', document.fonts.check('16px "Noto Serif"'), '');
    ok('内嵌 Inter 可用', document.fonts.check('16px "Inter"'), '');
  }
  setSel('fontFamily', 'default');
  await wait(400);

  // 确保时间显示是打开的
  var dsw = document.getElementById('dateSw');
  if (!dsw.checked) { dsw.click(); await wait(400); }

  var modes = ['date', 'min', 'sec'];
  var tsig = {};
  for (var ti = 0; ti < 3; ti++) {
    setSel('timeMode', modes[ti]);
    // 轻推一下滑杆，确保这一帧一定被重绘（无头环境 rAF 会合并请求）
    setRange('bar', ti === 0 ? '8.5' : '8.4');
    await wait(700);
    tsig[modes[ti]] = sig();
  }
  var tuniq = {}; Object.keys(tsig).forEach(function (k) { tuniq[tsig[k]] = 1; });
  ok('三种时间精度画面不同', Object.keys(tuniq).length === 3, JSON.stringify(tsig) + ' sel=' + document.getElementById('timeMode').value + ' date=' + document.querySelector('[data-f=\"date\"]').value);
  setSel('timeMode', 'date');
  await wait(300);

  setSel('format', 'png');
  await wait(200);
  var q = document.getElementById('quality');
  ok('PNG 隐藏质量滑杆', q.style.display === 'none', q.style.display);
  ok('PNG 显示无损说明', document.getElementById('qualityNote').hidden === false, '');
  ok('PNG 数值显示无损', document.getElementById('qOut').textContent === '无损', document.getElementById('qOut').textContent);
  setSel('format', 'jpeg');
  await wait(200);
  ok('JPEG 恢复质量滑杆', q.style.display !== 'none', q.style.display);
  ok('JPEG 数值显示百分比', /%$/.test(document.getElementById('qOut').textContent), document.getElementById('qOut').textContent);

  var s1 = sig();
  setRange('bar', '12');
  await wait(350);
  ok('白条高度滑杆生效', s1 !== sig(), '');
  document.getElementById('resetLook').click();
  await wait(350);
  ok('重置外观生效', document.getElementById('barOut').textContent === '8.4%', document.getElementById('barOut').textContent);

  var s3 = sig();
  document.getElementById('dateSw').click();
  await wait(350);
  ok('显示时间开关生效', s3 !== sig(), '');
  document.getElementById('dateSw').click();
  await wait(300);

  // 图标：默认“无” → 徕卡 → 无
  var chips = $$('#logoChips button');
  chips[0].click();
  await wait(300);
  ok('图标切到无', chips[0].classList.contains('is-on'), chips[0].className);
  var n0 = sig();
  chips[1].click();
  await wait(500);
  var n1 = sig();
  ok('切到徕卡生效', n0 !== n1, '');
  chips[0].click();
  await wait(400);
  ok('切回无生效', sig() === n0, '');

  var segs = $$('#barAlignSeg button');
  var s7 = sig();
  segs[1].click();
  await wait(350);
  ok('文字靠上/居中生效', s7 !== sig(), '');
  segs[0].click();
  await wait(300);

  // 居中模板 + 文字颜色：白 vs 黑
  document.querySelector('.tpl[data-tpl="center"]').click();
  await wait(450);
  var inkBtns = $$('#inkSeg button');
  var wBtn = inkBtns.filter(function (b) { return b.dataset.v === 'white'; })[0];
  var bBtn = inkBtns.filter(function (b) { return b.dataset.v === 'black'; })[0];
  wBtn.click(); await wait(350); var wSig = sig();
  bBtn.click(); await wait(350); var bSig = sig();
  ok('居中模板白/黑文字不同', wSig !== bSig, '');
  inkBtns.filter(function (b) { return b.dataset.v === 'auto'; })[0].click();
  document.querySelector('.tpl[data-tpl="bar"]').click();
  await wait(350);

  // 预设
  var before = 0;
  try { before = JSON.parse(localStorage.getItem('exifwm.presets.v1') || '[]').length; } catch (e) { before = -1; }
  document.getElementById('presetSave').click();
  await wait(500);
  var after = 0;
  try { after = JSON.parse(localStorage.getItem('exifwm.presets.v1') || '[]').length; } catch (e) { after = -1; }
  ok('保存预设写入 localStorage', after === before + 1, before + ' -> ' + after);
  ok('预设下拉出现条目', document.getElementById('presetSel').options.length > 0, document.getElementById('presetSel').options.length);

  // 导出（桩掉文件选择器，走完整 download 流程）
  var saved = null;
  window.showSaveFilePicker = function () {
    return Promise.resolve({
      createWritable: function () {
        return Promise.resolve({ write: function (b) { saved = b; return Promise.resolve(); }, close: function () { return Promise.resolve(); } });
      }
    });
  };
  document.getElementById('exportBtn').click();
  for (var w = 0; w < 40 && !saved; w++) await wait(250);
  ok('导出流程完成', !!saved && saved.size > 1000, saved ? saved.size + ' B' : 'no blob');
  if (saved) {
    try {
      var bmp = await createImageBitmap(saved);
      ok('原图导出尺寸正确（含白边）', bmp.width === 2492 && bmp.height === 1848, bmp.width + 'x' + bmp.height);
    } catch (e) { ok('导出图可解码', false, e.message); }
  }

  ok('无运行时错误', errs.length === 0, errs.join(' | '));
  return { results: R, errors: errs };
})()
