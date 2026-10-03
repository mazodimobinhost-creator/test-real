"""رابط کاربری پنل (HTML/CSS/JS تک‌فایلی، RTL، برند اختصاصی).

همه‌ی متغیرهای ظاهری از تنظیمات برند خوانده می‌شوند، پس پنل «کپی» هیچ پنل دیگری
به‌نظر نمی‌رسد: نام، شعار، رنگ‌ها، لوگو و مسیر مخفی همه قابل تغییرند.
"""

from __future__ import annotations

from . import store
from .settings import APP_NAME, APP_VERSION

CSS = """
:root{--bg:#080c18;--card:#111730;--card2:#16203f;--line:#233056;--fg:#eaf0ff;--mut:#8ea0c9;
--acc:#5b6cff;--acc2:#a855f7;--ok:#22c55e;--warn:#f59e0b;--bad:#ef4444;--radius:15px}
*{box-sizing:border-box;font-family:Vazirmatn,Tahoma,'Segoe UI',sans-serif}
body{margin:0;background:radial-gradient(1200px 600px at 80% -10%,rgba(91,108,255,.14) 0%,var(--bg) 55%);
color:var(--fg);direction:rtl;font-size:14px;min-height:100vh}
a{color:var(--acc)}
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.login{width:100%;max-width:390px;background:var(--card);border:1px solid var(--line);border-radius:22px;padding:28px;
box-shadow:0 30px 80px rgba(0,0,0,.45)}
.login h1{margin:0 0 4px;font-size:20px;display:flex;align-items:center;gap:10px}
.login p{margin:0 0 20px;color:var(--mut);font-size:12.5px}
.mark{width:34px;height:34px;border-radius:11px;display:flex;align-items:center;justify-content:center;
background:linear-gradient(135deg,var(--acc),var(--acc2));font-size:17px}
input,select,textarea{width:100%;background:#0b1226;border:1px solid var(--line);color:var(--fg);
border-radius:11px;padding:10px 12px;font-size:13px;margin-bottom:10px;font-family:inherit}
textarea{min-height:96px;line-height:1.8}
label{font-size:12px;color:var(--mut);display:block;margin-bottom:5px}
button{cursor:pointer;border:0;border-radius:11px;padding:10px 15px;background:var(--acc);color:#fff;font-weight:700;font-size:13px}
button:hover{filter:brightness(1.08)}
button.ghost{background:var(--card2);color:var(--fg)}
button.ok{background:var(--ok)}button.bad{background:var(--bad)}button.warn{background:var(--warn)}
button.sm{padding:6px 11px;font-size:12px;border-radius:9px}
header{position:sticky;top:0;z-index:5;background:rgba(8,12,24,.9);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.hrow{max-width:1240px;margin:0 auto;padding:12px 16px;display:flex;align-items:center;gap:12px}
.brand{font-weight:800;font-size:16px;display:flex;align-items:center;gap:9px}
.dot{width:9px;height:9px;border-radius:99px;background:var(--ok);box-shadow:0 0 12px var(--ok)}
.spacer{flex:1}
nav{max-width:1240px;margin:0 auto;padding:0 12px 8px;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none}
nav::-webkit-scrollbar{display:none}
nav button{background:transparent;color:var(--mut);border-radius:10px;padding:8px 13px;font-weight:600;white-space:nowrap}
nav button.on{background:var(--card2);color:var(--fg)}
main{max-width:1240px;margin:0 auto;padding:18px 16px 70px}
.grid{display:grid;gap:13px}
.g4{grid-template-columns:repeat(auto-fit,minmax(185px,1fr))}
.g2{grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:17px}
.card h3{margin:0 0 12px;font-size:15px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.stat small{color:var(--mut);font-size:12px}
.stat b{display:block;font-size:23px;margin-top:6px}
.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.pill{font-size:11px;padding:4px 10px;border-radius:99px;background:var(--card2);color:var(--mut);display:inline-block}
.pill.ok{background:rgba(34,197,94,.15);color:#7ee2a3}
.pill.bad{background:rgba(239,68,68,.15);color:#ff9b9b}
.pill.warn{background:rgba(245,158,11,.15);color:#f7c46c}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:right;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:middle}
th{color:var(--mut);font-weight:600;font-size:12px}
tr:hover td{background:rgba(91,108,255,.05)}
.bar{height:7px;background:#1b2547;border-radius:99px;overflow:hidden;margin-top:6px;min-width:80px}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--acc),var(--acc2))}
.mut{color:var(--mut);font-size:12px}
code,pre{direction:ltr;text-align:left;background:#0a1024;border:1px solid var(--line);border-radius:11px;padding:11px;
font-size:11.5px;overflow:auto;display:block;color:#cfe0ff;white-space:pre-wrap;word-break:break-all}
.modal{position:fixed;inset:0;background:rgba(3,6,14,.8);display:none;align-items:flex-start;justify-content:center;
padding:24px 14px;z-index:20;overflow:auto}
.modal.on{display:flex}
.modal .box{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:22px;width:100%;max-width:700px}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#111a36;border:1px solid var(--line);
padding:11px 19px;border-radius:13px;opacity:0;transition:.25s;z-index:40;font-size:13px}
.toast.on{opacity:1}
.chk{display:inline-flex;align-items:center;gap:7px;background:#0b1226;border:1px solid var(--line);padding:7px 11px;
border-radius:10px;font-size:12px;margin:0 0 8px 8px}
.chk input{width:auto;margin:0}
.step{position:relative;padding-inline-start:46px;margin-bottom:14px}
.step .num{position:absolute;inset-inline-start:0;top:0;width:34px;height:34px;border-radius:12px;display:flex;
align-items:center;justify-content:center;background:linear-gradient(135deg,var(--acc),var(--acc2));font-weight:800}
.step h4{margin:4px 0 6px;font-size:15px}
.tip{background:rgba(91,108,255,.09);border:1px solid rgba(91,108,255,.3);border-radius:12px;padding:10px 12px;
font-size:12.5px;color:#cfd9ff;margin:8px 0}
.swatch{width:34px;height:34px;border-radius:10px;border:1px solid var(--line);display:inline-block;vertical-align:middle}
"""

JS = r"""
const S = { page:'dash', data:{}, locs:[], users:[], plans:[], orders:[], resellers:[], wallet:[], announcements:[], steps:[], files:{} };
const ADMIN = "__ADMIN_PATH__";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const J = (x) => JSON.stringify(x == null ? '' : x);
const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`(.+?)`/g, '<code style="display:inline;padding:1px 5px">$1</code>').replace(/\n/g, '<br>');

function toast(msg, bad) {
  const t = $('toast'); t.textContent = msg;
  t.style.borderColor = bad ? 'var(--bad)' : 'var(--line)';
  t.classList.add('on'); setTimeout(() => t.classList.remove('on'), 2600);
}
async function api(path, method = 'GET', body) {
  const opt = { method, credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opt.body = JSON.stringify(body);
  const res = await fetch(path, opt);
  let data = {};
  try { data = await res.json(); } catch (e) { data = {}; }
  if (!res.ok) throw new Error(data.detail || ('HTTP ' + res.status));
  return data;
}
function copy(text) {
  if (navigator.clipboard) navigator.clipboard.writeText(text).then(() => toast('کپی شد ✓'), () => fb(text));
  else fb(text);
}
function fb(text) {
  const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
  try { document.execCommand('copy'); toast('کپی شد ✓'); } catch (e) { toast('کپی نشد', 1); }
  document.body.removeChild(ta);
}
function download(name, content) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
function fmtBytes(b) {
  b = Number(b) || 0; const u = ['B','KB','MB','GB','TB']; let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return (b >= 100 ? Math.round(b) : b.toFixed(2)) + ' ' + u[i];
}
function money(n) { return (Number(n) || 0).toLocaleString('en-US') + ' تومان'; }
function openModal(html) { $('modalBox').innerHTML = html; $('modal').classList.add('on'); }
function closeModal() { $('modal').classList.remove('on'); }
function ago(sec) {
  if (sec === null || sec === undefined) return 'هرگز';
  if (sec < 60) return sec + ' ثانیه پیش';
  if (sec < 3600) return Math.round(sec / 60) + ' دقیقه پیش';
  if (sec < 86400) return Math.round(sec / 3600) + ' ساعت پیش';
  return Math.round(sec / 86400) + ' روز پیش';
}
function modal() { return '<div class="modal" id="modal"><div class="box" id="modalBox"></div></div>'; }

// ═════════════════════ داشبورد ═════════════════════
function pageDash() {
  const s = S.data.stats || {}, locs = S.data.locations || [], tr = S.data.traffic || [], ev = S.data.events || [];
  const max = Math.max(1, ...tr.map(x => x.bytes));
  const bars = tr.length ? tr.map(x => '<div title="' + x.hour + ' · ' + fmtBytes(x.bytes) + '" style="flex:1;display:flex;align-items:flex-end;height:100%">' +
      '<div style="width:100%;height:' + Math.max(3, Math.round(x.bytes / max * 100)) + '%;background:linear-gradient(180deg,var(--acc),var(--acc2));border-radius:4px 4px 0 0"></div></div>').join('')
    : '<div class="mut">هنوز ترافیکی ثبت نشده است.</div>';
  const locCards = locs.map(l => {
    const st = l.status || {};
    return '<div class="card stat" style="border-color:' + (l.online ? 'rgba(34,197,94,.35)' : 'var(--line)') + '">' +
      '<div class="row" style="justify-content:space-between"><div><div style="font-weight:700">' + esc(l.flag) + ' ' + esc(l.name) + '</div>' +
      '<small class="mut">' + esc(l.host || 'بدون دامنه') + '</small></div>' +
      '<span class="pill ' + (l.online ? 'ok' : 'bad') + '">' + (l.online ? 'آنلاین' : 'آفلاین') + '</span></div>' +
      '<div class="grid" style="margin-top:10px;grid-template-columns:1fr 1fr">' +
      '<div><small class="mut">آنلاین</small><b>' + (st.users_online || 0) + '</b></div>' +
      '<div><small class="mut">کاربران</small><b>' + (st.clients || 0) + '</b></div>' +
      '<div><small class="mut">CPU</small><b>' + (st.cpu ? st.cpu + '%' : '—') + '</b></div>' +
      '<div><small class="mut">موتور</small><b style="font-size:15px">' + esc((st.engine || l.engine || 'python')) + '</b></div></div>' +
      '<div class="mut" style="margin-top:8px">مسیر خروج: ' + esc(l.egress_mode || 'direct') + ' · آخرین خبر: ' + ago(l.seen_ago) + '</div></div>';
  }).join('') || '<div class="card mut">هنوز لوکیشنی نساخته‌ای. از تب «لوکیشن‌ها» یا «آموزش راه‌اندازی» شروع کن.</div>';
  return '<div class="grid g4">' +
    '<div class="card stat"><small>کاربران</small><b>' + (s.users || 0) + '</b><div class="mut">فعال ' + (s.active_users || 0) + ' · محدود ' + (s.limited_users || 0) + ' · منقضی ' + (s.expired_users || 0) + '</div></div>' +
    '<div class="card stat"><small>لوکیشن‌های آنلاین</small><b>' + (s.online_locations || 0) + '/' + (s.locations || 0) + '</b><div class="mut">وضعیت لحظه‌ای</div></div>' +
    '<div class="card stat"><small>ترافیک ۲۴ ساعت</small><b>' + fmtBytes(s.total_traffic || 0) + '</b><div class="mut">مجموع ثبت‌شده</div></div>' +
    '<div class="card stat"><small>سفارش / کیف پول</small><b>' + (s.pending_orders || 0) + ' / ' + (s.pending_topups || 0) + '</b><div class="mut">در انتظار تأیید</div></div></div>' +
    '<div class="card" style="margin-top:14px"><h3>📈 ترافیک ساعتی</h3><div style="display:flex;gap:3px;align-items:flex-end;height:120px">' + bars + '</div></div>' +
    '<h3 style="margin:18px 4px 8px">🛰 لوکیشن‌ها</h3><div class="grid g4">' + locCards + '</div>' +
    '<div class="card" style="margin-top:16px"><h3>🧾 آخرین رویدادها</h3>' +
    (ev.map(e => '<div class="row" style="border-bottom:1px solid var(--line);padding:7px 0">' +
      '<span class="pill ' + (e.level === 'error' ? 'bad' : (e.level === 'warn' ? 'warn' : 'ok')) + '">' + esc(e.kind) + '</span>' +
      '<span style="flex:1">' + esc(e.message) + '</span></div>').join('') || '<div class="mut">رویدادی نیست</div>') + '</div>' + modal();
}

// ═════════════════════ لوکیشن‌ها ═════════════════════
function pageLocations() {
  const rows = (S.locs || []).map(l => '<tr>' +
    '<td><b>' + esc(l.flag) + ' ' + esc(l.name) + '</b><div class="mut">' + esc(l.region || '') + '</div></td>' +
    '<td><code style="padding:4px 6px">' + esc(l.host || '—') + '</code>' +
    (l.cf_host ? '<div class="mut">CF: ' + esc(l.cf_host) + '</div>' : '') + '</td>' +
    '<td>' + (l.transports || []).map(t => '<span class="pill">' + esc(t) + '</span>').join(' ') +
    '<div class="mut">موتور: ' + esc(l.engine || 'python') + '</div></td>' +
    '<td>' + egressPill(l) + '<div class="mut">' + esc((l.status || {}).egress_mode || '') + '</div></td>' +
    '<td><span class="pill ' + (l.online ? 'ok' : 'bad') + '">' + (l.online ? 'آنلاین' : 'آفلاین') + '</span><div class="mut">' + ago(l.seen_ago) + '</div></td>' +
    '<td><div class="row"><button class="sm ghost" onclick="locEdit(' + l.id + ')">ویرایش</button>' +
    '<button class="sm ghost" onclick="locEnv(' + l.id + ')">متغیرهای نود</button>' +
    '<button class="sm ghost" onclick="locEgressTest(' + l.id + ')">تست خروج</button>' +
    '<button class="sm ghost" onclick="locRotate(' + l.id + ')">توکن جدید</button>' +
    '<button class="sm bad" onclick="locDel(' + l.id + ')">حذف</button></div></td></tr>').join('')
    || '<tr><td colspan="6" class="mut">لوکیشنی ثبت نشده است.</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>🛰 لوکیشن‌ها</h3>' +
    '<div class="row"><button class="ghost" onclick="openSetup()">راهنمای ساخت</button>' +
    '<button onclick="locEdit()">+ لوکیشن جدید</button></div></div>' +
    '<table><thead><tr><th>نام</th><th>دامنه</th><th>ترابرد / موتور</th><th>مسیر خروج</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>' + rows + '</tbody></table>' +
    '<div class="mut" style="margin-top:12px">هر لوکیشن = یک سرویس جدا روی Railway (ریجن دلخواه) با <code style="display:inline;padding:2px 6px">MLP_ROLE=node</code>؛ یا یک ورکر Cloudflare؛ یا یک VPS خودت.</div></div>' + modal();
}
function locForm(l) {
  l = l || {};
  const t = l.transports || ['ws'];
  return '<h3>' + (l.id ? 'ویرایش لوکیشن' : 'لوکیشن جدید') + '</h3>' +
  '<label>نام</label><input id="l_name" value="' + esc(l.name || '') + '" placeholder="Germany">' +
  '<div class="row"><div style="flex:1"><label>فلگ</label><input id="l_flag" value="' + esc(l.flag || '🌍') + '"></div>' +
  '<div style="flex:2"><label>ریجن</label><input id="l_region" value="' + esc(l.region || '') + '" placeholder="europe-west4"></div></div>' +
  '<label>دامنه‌ی عمومی نود</label><input id="l_host" value="' + esc(l.host || '') + '" placeholder="node-eu.up.railway.app">' +
  '<label>لوکیشن Cloudflare (اختیاری)</label><input id="l_cf" value="' + esc(l.cf_host || '') + '" placeholder="mlp-cf.example.workers.dev">' +
  '<label>سایت پوششی این لوکیشن (اگر خالی باشد از env یا auto استفاده می‌شود)</label><select id="l_decoy">' +
  [['','خودکار (پیش‌فرض)'],['shop','فروشگاه'],['corp','شرکت'],['blog','وبلاگ'],['none','خاموش']].map(x =>
    '<option value="' + x[0] + '"' + ((l.decoy || '') === x[0] ? ' selected' : '') + '>' + x[1] + '</option>').join('') + '</select>' +
  '<div class="row"><div style="flex:1"><label>موتور دیتاپلین</label><select id="l_engine">' +
  '<option value="python"' + ((l.engine || 'python') === 'python' ? ' selected' : '') + '>python (محدودیت کامل)</option>' +
  '<option value="xray"' + (l.engine === 'xray' ? ' selected' : '') + '>xray (سرعت بالاتر)</option></select></div>' +
  '<div style="flex:2"><label>ترابردها</label><div>' +
    '<label class="chk"><input type="checkbox" id="l_ws"' + (t.indexOf('ws') >= 0 ? ' checked' : '') + '> WS</label>' +
    '<label class="chk"><input type="checkbox" id="l_xhttp"' + (t.indexOf('xhttp') >= 0 ? ' checked' : '') + '> XHTTP</label>' +
    '<label class="chk"><input type="checkbox" id="l_tcp"' + (t.indexOf('tcp') >= 0 ? ' checked' : '') + '> TCP</label></div></div></div>' +
  '<div class="row"><div style="flex:1"><label>مسیر WS</label><input id="l_wsp" value="' + esc(l.ws_path || '/ws') + '"></div>' +
  '<div style="flex:1"><label>مسیر XHTTP</label><input id="l_xhp" value="' + esc(l.xhttp_path || '/xhttp') + '"></div>' +
  '<div style="flex:1"><label>پورت TCP</label><input id="l_tcpp" type="number" value="' + (l.tcp_port || 0) + '"></div></div>' +
  '<label>یادداشت</label><input id="l_note" value="' + esc(l.note || '') + '">' +
  egressForm(l) +
  '<div class="row"><button class="ok" onclick="locSave(' + (l.id || 0) + ')">ذخیره</button>' +
  '<button class="ghost" onclick="closeModal()">انصراف</button></div>';
}
function locEdit(id) { const l = id ? (S.locs || []).find(x => x.id === id) : null; openModal(locForm(l)); if (typeof egressToggle === 'function') egressToggle(); }
function egressConf(l) {
  const e = (l || {}).egress || {};
  const proxy = e.proxy || {}, chain = e.chain || {};
  let list = proxy.list || [];
  if (typeof list === 'string') list = list.split(/[\n,|]/).map(x => x.trim()).filter(Boolean);
  return { mode: ((l || {}).egress_mode || e.mode || 'direct').toLowerCase(),
    fallback: e.fallback !== false, test_target: e.test_target || '', type: proxy.type || 'socks5h',
    rotate: proxy.rotate || 'fastest', list: (list || []).join('\n'),
    ch_host: chain.host || '', ch_port: chain.port || 443, ch_path: chain.path || '/ws',
    ch_uuid: chain.uuid || '', ch_tls: chain.tls !== false, ch_sni: chain.sni || '', ch_insecure: !!chain.insecure };
}
function egressPill(l) {
  const c = egressConf(l);
  const names = { direct:'مستقیم', proxy:'پروکسی IP', chain:'تانل/چین', auto:'خودکار' };
  const cls = c.mode === 'direct' ? '' : 'ok';
  return '<span class="pill ' + cls + '">' + (names[c.mode] || c.mode) + '</span>';
}
function egressForm(l) {
  const c = egressConf(l);
  const sel = (v, label) => '<option value="' + v + '"' + (c.mode === v ? ' selected' : '') + '>' + label + '</option>';
  return '<div class="card" style="background:var(--card2);margin:10px 0">' +
    '<h3 style="font-size:13px">🌐 مسیر خروج این لوکیشن (از کجا به اینترنت وصل شود)</h3>' +
    '<div class="row"><div style="flex:1"><label>حالت</label><select id="e_mode" onchange="egressToggle()">' +
      sel('direct', 'مستقیم (خود نود)') + sel('proxy', 'پروکسی IP (SOCKS5/HTTP)') +
      sel('chain', 'تانل/چین به سرور دیگر') + sel('auto', 'خودکار (خروجی + fallback)') + '</select></div>' +
    '<div style="flex:2"><label>آدرس تست خروجی</label><input id="e_target" value="' + esc(c.test_target) + '" placeholder="1.1.1.1:443"></div></div>' +
    '<div id="e_proxy_box">' +
      '<label>فهرست پروکسی‌ها (هر خط یکی) — نمونه: 1.2.3.4:1080 یا user:pass@1.2.3.4:1080 یا http://1.2.3.4:8080</label>' +
      '<textarea id="e_list" style="direction:ltr;text-align:left;min-height:70px">' + esc(c.list) + '</textarea>' +
      '<div class="row"><div style="flex:1"><label>نوع پیش‌فرض</label><select id="e_type">' +
        ['socks5h:socks5h (DNS روی پروکسی)','socks5:socks5 (DNS محلی)','http:HTTP CONNECT']
          .map(x => { const p = x.split(':'); return '<option value="' + p[0] + '"' + (c.type === p[0] ? ' selected' : '') + '>' + p[1] + '</option>'; }).join('') +
      '</select></div><div style="flex:1"><label>انتخاب بین چند پروکسی</label><select id="e_rotate">' +
        ['fastest:سریع‌ترین','roundrobin:نوبتی','random:تصادفی']
          .map(x => { const p = x.split(':'); return '<option value="' + p[0] + '"' + (c.rotate === p[0] ? ' selected' : '') + '>' + p[1] + '</option>'; }).join('') +
      '</select></div></div></div>' +
    '<div id="e_chain_box">' +
      '<div class="row"><div style="flex:2"><label>هاست سرور بالادستی</label><input id="e_ch_host" value="' + esc(c.ch_host) + '" placeholder="node2.up.railway.app"></div>' +
      '<div style="flex:1"><label>پورت</label><input id="e_ch_port" value="' + (c.ch_port || 443) + '"></div>' +
      '<div style="flex:1"><label>مسیر</label><input id="e_ch_path" value="' + esc(c.ch_path) + '"></div></div>' +
      '<label>UUID کاربر روی سرور بالادستی (برای تانل، یک کاربر روی نود دیگر بساز)</label>' +
      '<input id="e_ch_uuid" style="direction:ltr;text-align:left" value="' + esc(c.ch_uuid) + '" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx">' +
      '<div class="row"><label class="chk"><input type="checkbox" id="e_ch_tls"' + (c.ch_tls ? ' checked' : '') + '> TLS (wss)</label>' +
      '<label class="chk"><input type="checkbox" id="e_ch_insecure"' + (c.ch_insecure ? ' checked' : '') + '> نادیده گرفتن خطای گواهی</label>' +
      '<label class="chk"><input type="checkbox" id="e_fallback"' + (c.fallback ? ' checked' : '') + '> در خرابی خروجی، خودِ نود وصل شود (fallback)</label></div>' +
      '<div style="flex:1"><label>SNI (اختیاری)</label><input id="e_ch_sni" style="direction:ltr;text-align:left" value="' + esc(c.ch_sni) + '"></div></div>' +
    '</div></div>';
}
function egressToggle() {
  const mode = $('e_mode').value;
  const showProxy = (mode === 'proxy' || mode === 'auto');
  const showChain = (mode === 'chain' || mode === 'auto');
  if ($('e_proxy_box')) $('e_proxy_box').style.display = showProxy ? 'block' : 'none';
  if ($('e_chain_box')) $('e_chain_box').style.display = showChain ? 'block' : 'none';
}
function egressPayload() {
  const mode = $('e_mode').value;
  const e = { mode: mode, fallback: $('e_fallback') ? $('e_fallback').checked : true };
  if ($('e_target') && $('e_target').value) e.test_target = $('e_target').value;
  if (mode === 'proxy' || mode === 'auto') {
    const list = ($('e_list').value || '').split(/[\n,]+/).map(x => x.trim()).filter(Boolean);
    if (list.length) e.proxy = { type: $('e_type').value, list: list, rotate: $('e_rotate').value };
  }
  if (mode === 'chain' || mode === 'auto') {
    if ($('e_ch_host').value) {
      e.chain = { host: $('e_ch_host').value.trim(), port: Number($('e_ch_port').value || 443),
        path: $('e_ch_path').value || '/ws', uuid: $('e_ch_uuid').value.trim(),
        tls: $('e_ch_tls').checked, sni: $('e_ch_sni').value.trim(), insecure: $('e_ch_insecure').checked };
    }
  }
  return e;
}
async function locEgressTest(id) {
  openModal('<h3>تست مسیر خروج…</h3><div class="mut">از خود نود می‌پرسیم مسیرها را امتحان کند؛ چند ثانیه صبر کن.</div>');
  try {
    const d = await api('/api/admin/locations/' + id + '/egress-test', 'POST', {});
    const t = d.test || {}, rows = (t.results || []).map(r =>
      '<tr><td>' + esc(r.label) + '</td><td>' + (r.ok ? '<span class="pill ok">سالم</span>' : '<span class="pill bad">خطا</span>') + '</td>' +
      '<td>' + (r.ok ? (r.latency_ms + ' ms') : esc((r.error || '').slice(0, 60))) + '</td></tr>').join('');
    openModal('<h3>نتیجه تست مسیر خروج</h3><div class="mut">مقصد: ' + esc(t.target || '') + ' · حالت: ' + esc(t.mode || '') + '</div>' +
      '<table style="margin-top:8px"><thead><tr><th>مسیر</th><th>وضعیت</th><th>جزئیات</th></tr></thead><tbody>' + rows + '</tbody></table>' +
      '<button class="ghost" onclick="closeModal()">بستن</button>');
  } catch (e) {
    const l = (S.locs || []).find(x => x.id === id) || {};
    const st = l.status || {};
    openModal('<h3>نتیجه تست</h3><div class="tip">' + esc(e.message) + '</div>' +
      '<div class="mut">آخرین وضعیت گزارش‌شده از نود: ' + esc(st.egress_mode || '—') + '</div>' +
      '<button class="ghost" onclick="closeModal()">بستن</button>');
  }
}
async function locSave(id) {
  const body = { id: id || null, name: $('l_name').value, flag: $('l_flag').value, region: $('l_region').value,
    host: $('l_host').value, cf_host: $('l_cf').value, ws_path: $('l_wsp').value, xhttp_path: $('l_xhp').value,
    engine: $('l_engine').value, tcp_port: Number($('l_tcpp').value || 0), note: $('l_note').value, enabled: true,
    decoy: $('l_decoy') ? $('l_decoy').value : '', egress_mode: $('e_mode').value, egress: egressPayload(),
    transports: [$('l_ws').checked ? 'ws' : null, $('l_xhttp').checked ? 'xhttp' : null, $('l_tcp').checked ? 'tcp' : null].filter(Boolean) };
  if (!body.name) { toast('نام لازم است', 1); return; }
  if (!body.transports.length) body.transports = ['ws'];
  const res = await api('/api/admin/locations', 'POST', body);
  closeModal();
  if (res.env) {
    openModal('<h3>متغیرهای سرویس نود</h3><div class="mut">این‌ها را در Railway → سرویس نود → Variables بگذار و Deploy کن.</div>' +
      '<pre style="margin-top:10px">' + esc(res.env) + '</pre>' +
      '<div class="row"><button onclick="copy(' + J(res.env) + ')">کپی همه</button>' +
      '<button class="ghost" onclick="closeModal();go(\'locations\')">فهمیدم</button></div>');
  }
  await go('locations');
}
async function locDel(id) { if (!confirm('لوکیشن حذف شود؟')) return; await api('/api/admin/locations/' + id, 'DELETE'); toast('حذف شد'); await go('locations'); }
async function locRotate(id) {
  const d = await api('/api/admin/locations/' + id + '/rotate', 'POST', {});
  openModal('<h3>توکن جدید</h3><pre>' + esc(d.env || d.token) + '</pre>' +
    '<div class="row"><button onclick="copy(' + J(d.env || d.token) + ')">کپی</button>' +
    '<button class="ghost" onclick="closeModal()">بستن</button></div>');
}
function locEnv(id) {
  const l = (S.locs || []).find(x => x.id === id);
  openModal('<h3>متغیرهای سرویس نود</h3><pre>' + esc(l.env || '') + '</pre>' +
    '<div class="mut">این‌ها را در Railway → سرویس نود → Variables بگذار و Deploy کن. برای موتور Xray، مقدار MLP_ENGINE را xray بگذار.</div>' +
    '<div class="row" style="margin-top:10px"><button onclick="copy(' + J(l.env || '') + ')">کپی همه</button>' +
    '<button class="ghost" onclick="closeModal()">بستن</button></div>');
}

// ═════════════════════ کاربران ═════════════════════
function userRow(u) {
  const limit = Number(u.limit_bytes) || 0, used = Number(u.used_bytes) || 0;
  const pct = limit ? Math.min(100, Math.round(used * 100 / limit)) : 0;
  const cls = u.status === 'active' ? 'ok' : (u.status === 'disabled' ? '' : 'bad');
  return '<tr><td><b>' + esc(u.name || 'بی‌نام') + '</b><div class="mut">#' + u.id +
    (u.telegram_id ? ' · tg:' + esc(u.telegram_id) : '') + (u.reseller_name ? ' · 🤝 ' + esc(u.reseller_name) : '') + '</div></td>' +
    '<td><span class="pill ' + cls + '">' + esc(u.status) + '</span></td>' +
    '<td style="min-width:130px">' + fmtBytes(used) + ' / ' + (limit ? fmtBytes(limit) : '∞') + '<div class="bar"><i style="width:' + pct + '%"></i></div></td>' +
    '<td>' + (u.days_left === null ? '∞' : u.days_left + ' روز') + '</td>' +
    '<td>' + (u.locations || []).length + '</td>' +
    '<td><div class="row"><button class="sm ghost" onclick="userLinks(' + u.id + ')">لینک‌ها</button>' +
    '<button class="sm ghost" onclick="userEdit(' + u.id + ')">ویرایش</button>' +
    '<button class="sm ghost" onclick="userToggle(' + u.id + ')">' + (u.enabled ? 'خاموش' : 'روشن') + '</button>' +
    '<button class="sm ghost" onclick="userReset(' + u.id + ')">صفر کردن</button>' +
    '<button class="sm bad" onclick="userDel(' + u.id + ')">حذف</button></div></td></tr>';
}
function pageUsers() {
  const rows = (S.users || []).map(userRow).join('') || '<tr><td colspan="6" class="mut">کاربری ساخته نشده است.</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>👥 کاربران</h3>' +
    '<div class="row"><input id="uSearch" placeholder="جستجو…" style="width:180px;margin:0" oninput="renderUsers()">' +
    '<button onclick="userEdit()">+ کاربر جدید</button></div></div>' +
    '<table><thead><tr><th>کاربر</th><th>وضعیت</th><th>مصرف</th><th>اعتبار</th><th>لوکیشن</th><th>عملیات</th></tr></thead>' +
    '<tbody id="usersBody">' + rows + '</tbody></table></div>' + modal();
}
function renderUsers() {
  const box = $('uSearch'); const q = (box ? box.value : '').trim().toLowerCase();
  const body = $('usersBody'); if (!body) return;
  const rows = (S.users || []).filter(u => !q || (u.name || '').toLowerCase().includes(q) || String(u.id) === q);
  body.innerHTML = rows.map(userRow).join('') || '<tr><td colspan="6" class="mut">موردی پیدا نشد</td></tr>';
}
function userForm(u) {
  u = u || {};
  const gb = u.limit_bytes ? (u.limit_bytes / 1073741824).toFixed(2) : '';
  const opts = (S.resellers || []).map(r => '<option value="' + r.id + '"' + (u.reseller_id === r.id ? ' selected' : '') + '>' + esc(r.name || r.username) + '</option>').join('');
  return '<h3>' + (u.id ? 'ویرایش کاربر' : 'کاربر جدید') + '</h3>' +
  '<label>نام</label><input id="u_name" value="' + esc(u.name || '') + '">' +
  '<div class="row"><div style="flex:1"><label>حجم (GB، 0=نامحدود)</label><input id="u_gb" value="' + gb + '"></div>' +
  '<div style="flex:1"><label>مدت (روز)</label><input id="u_days" value="' + (u.id ? 0 : 30) + '"></div></div>' +
  (u.id ? '<label class="chk"><input type="checkbox" id="u_extend" checked> افزودن به حجم/زمان فعلی</label>' : '') +
  '<div class="row"><div style="flex:1"><label>حداکثر IP (0=نامحدود)</label><input id="u_ips" value="' + (u.max_ips || 0) + '"></div>' +
  '<div style="flex:1"><label>سرعت (kbps، 0=نامحدود)</label><input id="u_speed" value="' + (u.speed_kbps || 0) + '"></div></div>' +
  '<label>آیدی عددی تلگرام (اختیاری)</label><input id="u_tg" value="' + esc(u.telegram_id || '') + '">' +
  '<label>رزیلر (اختیاری)</label><select id="u_reseller"><option value="0">— بدون رزیلر —</option>' + opts + '</select>' +
  '<label>یادداشت</label><input id="u_note" value="' + esc(u.note || '') + '">' +
  '<div class="row"><button class="ok" onclick="userSave(' + (u.id || 0) + ')">ذخیره</button>' +
  '<button class="ghost" onclick="closeModal()">انصراف</button></div>';
}
function userEdit(id) { const u = id ? (S.users || []).find(x => x.id === id) : null; openModal(userForm(u)); }
async function userSave(id) {
  const body = { id: id || null, name: $('u_name').value, limit_gb: Number($('u_gb').value || 0),
    days: Number($('u_days').value || 0), max_ips: Number($('u_ips').value || 0),
    speed_kbps: Number($('u_speed').value || 0), telegram_id: $('u_tg').value, note: $('u_note').value,
    reseller_id: Number($('u_reseller') ? $('u_reseller').value : 0),
    enabled: true, extend: $('u_extend') ? $('u_extend').checked : false };
  if (!body.name) { toast('نام لازم است', 1); return; }
  await api('/api/admin/users', 'POST', body); closeModal(); toast('ذخیره شد ✓'); await go('users');
}
async function userToggle(id) { await api('/api/admin/users/' + id + '/toggle', 'POST', {}); await go('users'); }
async function userReset(id) { if (!confirm('مصرف صفر شود؟')) return; await api('/api/admin/users/' + id + '/reset', 'POST', {}); toast('صفر شد'); await go('users'); }
async function userDel(id) { if (!confirm('کاربر حذف شود؟')) return; await api('/api/admin/users/' + id, 'DELETE'); toast('حذف شد'); await go('users'); }
async function userLinks(id) {
  const d = await api('/api/admin/users/' + id + '/links');
  const i = d.info;
  openModal('<h3>لینک‌های ' + esc(i.name) + '</h3>' +
    '<div class="row"><button onclick="copy(' + J(i.sub_url || '') + ')">کپی لینک ساب</button>' +
    '<a href="' + esc(i.sub_url) + '" target="_blank"><button class="ghost">باز کردن صفحه ساب</button></a></div>' +
    '<pre style="margin-top:10px">' + esc(i.sub_url) + '</pre><h3 style="margin-top:14px">کانفیگ‌ها</h3>' +
    (i.configs.map(c => '<div style="margin-bottom:8px"><div class="mut">' + esc(c.flag) + ' ' + esc(c.location) + ' · ' + esc(c.transport) + '</div>' +
      '<pre>' + esc(c.link) + '</pre></div>').join('') || '<div class="mut">کانفیگی نیست</div>') +
    '<button class="ghost" onclick="closeModal()">بستن</button>');
}

// ═════════════════════ پلن‌ها ═════════════════════
function pagePlans() {
  const rows = (S.plans || []).map(p => '<tr><td><b>' + esc(p.name) + '</b></td><td>' + p.traffic_gb + ' GB</td>' +
    '<td>' + p.days + ' روز</td><td>' + esc(p.price || '—') + '</td>' +
    '<td>' + (p.reseller_price ? money(p.reseller_price) : '—') + '</td>' +
    '<td>' + (p.max_ips || '∞') + '</td>' +
    '<td><span class="pill ' + (p.enabled ? 'ok' : 'bad') + '">' + (p.enabled ? 'فعال' : 'غیرفعال') + '</span></td>' +
    '<td><button class="sm ghost" onclick="planEdit(' + p.id + ')">ویرایش</button> ' +
    '<button class="sm bad" onclick="planDel(' + p.id + ')">حذف</button></td></tr>').join('')
    || '<tr><td colspan="8" class="mut">پلنی ثبت نشده است.</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>🛍 پلن‌های فروش</h3>' +
    '<button onclick="planEdit()">+ پلن جدید</button></div>' +
    '<table><thead><tr><th>نام</th><th>حجم</th><th>مدت</th><th>قیمت مشتری</th><th>قیمت رزیلر</th><th>IP</th><th>وضعیت</th><th></th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table></div>' + modal();
}
function planForm(p) {
  p = p || {};
  return '<h3>' + (p.id ? 'ویرایش پلن' : 'پلن جدید') + '</h3>' +
  '<label>نام</label><input id="p_name" value="' + esc(p.name || '') + '">' +
  '<div class="row"><div style="flex:1"><label>حجم (GB)</label><input id="p_gb" value="' + (p.traffic_gb || 0) + '"></div>' +
  '<div style="flex:1"><label>مدت (روز)</label><input id="p_days" value="' + (p.days || 30) + '"></div>' +
  '<div style="flex:1"><label>قیمت مشتری (متن)</label><input id="p_price" value="' + esc(p.price || '') + '"></div></div>' +
  '<div class="row"><div style="flex:1"><label>قیمت رزیلر (تومان)</label><input id="p_rprice" value="' + (p.reseller_price || 0) + '"></div>' +
  '<div style="flex:1"><label>حداکثر IP</label><input id="p_ips" value="' + (p.max_ips || 0) + '"></div>' +
  '<div style="flex:1"><label>سرعت kbps</label><input id="p_speed" value="' + (p.speed_kbps || 0) + '"></div></div>' +
  '<div class="row"><button class="ok" onclick="planSave(' + (p.id || 0) + ')">ذخیره</button>' +
  '<button class="ghost" onclick="closeModal()">انصراف</button></div>';
}
function planEdit(id) { const p = id ? (S.plans || []).find(x => x.id === id) : null; openModal(planForm(p)); }
async function planSave(id) {
  await api('/api/admin/plans', 'POST', { id: id || null, name: $('p_name').value, traffic_gb: Number($('p_gb').value || 0),
    days: Number($('p_days').value || 0), price: $('p_price').value, max_ips: Number($('p_ips').value || 0),
    speed_kbps: Number($('p_speed').value || 0), reseller_price: Number($('p_rprice').value || 0), enabled: true });
  closeModal(); toast('ذخیره شد ✓'); await go('plans');
}
async function planDel(id) { if (!confirm('پلن حذف شود؟')) return; await api('/api/admin/plans/' + id, 'DELETE'); await go('plans'); }

// ═════════════════════ سفارش‌ها ═════════════════════
function pageOrders() {
  const rows = (S.orders || []).map(o => '<tr><td>#' + o.id + '<div class="mut">' + esc(o.who || '') + '</div></td>' +
    '<td>' + esc((o.plan || {}).name || '—') + '</td><td>' + esc(o.telegram_id || '—') + '</td>' +
    '<td><span class="pill ' + (o.status === 'approved' ? 'ok' : (o.status === 'pending' ? 'warn' : 'bad')) + '">' + esc(o.status) + '</span></td>' +
    '<td>' + (o.receipt ? 'دارد' : '—') + '</td>' +
    '<td><div class="row">' + (o.status === 'pending' ?
      '<button class="sm ok" onclick="orderApprove(' + o.id + ')">تأیید</button>' +
      '<button class="sm bad" onclick="orderReject(' + o.id + ')">رد</button>' : '') +
      '<button class="sm ghost" onclick="orderReceipt(' + J(o.receipt) + ')">رسید</button></div></td></tr>').join('')
    || '<tr><td colspan="6" class="mut">سفارشی ثبت نشده است.</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>🧾 سفارش‌ها</h3>' +
    '<button class="ghost" onclick="loadOrders().then(draw)">به‌روزرسانی</button></div>' +
    '<table><thead><tr><th>سفارش</th><th>پلن</th><th>تلگرام</th><th>وضعیت</th><th>رسید</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>' + modal();
}
async function orderApprove(id) { await api('/api/admin/orders/' + id + '/approve', 'POST', {}); toast('تأیید شد و لینک ارسال شد'); await go('orders'); }
async function orderReject(id) {
  const r = prompt('دلیل رد:', 'پرداخت تأیید نشد') || 'رد شد';
  await api('/api/admin/orders/' + id + '/reject?reason=' + encodeURIComponent(r), 'POST', {});
  toast('رد شد'); await go('orders');
}
function orderReceipt(fileId) {
  if (!fileId) { toast('رسیدی ثبت نشده', 1); return; }
  openModal('<h3>رسید / یادداشت</h3><pre>' + esc(fileId) + '</pre>' +
    '<button class="ghost" onclick="closeModal()">بستن</button>');
}

// ═════════════════════ رزیلرها ═════════════════════
function pageResellers() {
  const rows = (S.resellers || []).map(r => '<tr>' +
    '<td><b>' + esc(r.name || r.username) + '</b><div class="mut">@' + esc(r.username) + '</div></td>' +
    '<td><b>' + money(r.balance) + '</b><div class="mut">کیف پول</div></td>' +
    '<td>' + (r.price_gb ? money(r.price_gb) + ' / GB' : '—') + '<div class="mut">' + (r.price_day ? money(r.price_day) + ' / روز' : '') + '</div></td>' +
    '<td>' + (r.summary ? r.summary.users + ' کاربر' : '—') + '<div class="mut">' + (r.summary ? fmtBytes(r.summary.used) : '') + '</div></td>' +
    '<td><span class="pill ' + (r.enabled ? 'ok' : 'bad') + '">' + (r.enabled ? 'فعال' : 'غیرفعال') + '</span></td>' +
    '<td><div class="row"><button class="sm ok" onclick="resellerTopup(' + r.id + ')">شارژ</button>' +
    '<button class="sm ghost" onclick="resellerEdit(' + r.id + ')">ویرایش</button>' +
    '<button class="sm bad" onclick="resellerDel(' + r.id + ')">حذف</button></div></td></tr>').join('')
    || '<tr><td colspan="6" class="mut">رزیلری ثبت نشده است.</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>🤝 رزیلرها</h3>' +
    '<button onclick="resellerEdit()">+ رزیلر جدید</button></div>' +
    '<table><thead><tr><th>رزیلر</th><th>موجودی</th><th>تعرفه فروش</th><th>کاربران</th><th>وضعیت</th><th>عملیات</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>' +
    '<div class="mut" style="margin-top:12px">رزیلر با <code style="display:inline;padding:2px 6px">/reseller</code> در ربات وارد می‌شود، از کیف پولش کاربر می‌سازد و قیمت‌ها بر اساس تعرفه‌ی همین جدول کسر می‌شود.</div></div>' + modal();
}
function resellerForm(r) {
  r = r || {};
  return '<h3>' + (r.id ? 'ویرایش رزیلر' : 'رزیلر جدید') + '</h3>' +
  '<label>نام</label><input id="r_name" value="' + esc(r.name || '') + '">' +
  '<div class="row"><div style="flex:1"><label>نام کاربری</label><input id="r_user" value="' + esc(r.username || '') + '"></div>' +
  '<div style="flex:1"><label>رمز (برای تغییر پر کن)</label><input id="r_pass" value=""></div></div>' +
  '<div class="row"><div style="flex:1"><label>قیمت هر GB (تومان)</label><input id="r_gb" value="' + (r.price_gb || 0) + '"></div>' +
  '<div style="flex:1"><label>قیمت هر روز (تومان)</label><input id="r_day" value="' + (r.price_day || 0) + '"></div>' +
  '<div style="flex:1"><label>حداقل خرید (GB)</label><input id="r_min" value="' + (r.min_gb || 1) + '"></div></div>' +
  '<label>آیدی تلگرام (برای اطلاع از شارژ — اختیاری)</label><input id="r_tg" value="' + esc(r.note || '') + '">' +
  '<div class="row"><button class="ok" onclick="resellerSave(' + (r.id || 0) + ')">ذخیره</button>' +
  '<button class="ghost" onclick="closeModal()">انصراف</button></div>';
}
function resellerEdit(id) { const r = id ? (S.resellers || []).find(x => x.id === id) : null; openModal(resellerForm(r)); }
async function resellerSave(id) {
  const body = { id: id || null, name: $('r_name').value, username: $('r_user').value, password: $('r_pass').value,
    price_gb: Number($('r_gb').value || 0), price_day: Number($('r_day').value || 0),
    min_gb: Number($('r_min').value || 1), note: $('r_tg').value, enabled: true };
  if (!body.name || !body.username) { toast('نام و نام کاربری لازم است', 1); return; }
  await api('/api/admin/resellers', 'POST', body); closeModal(); toast('ذخیره شد ✓'); await go('resellers');
}
async function resellerDel(id) { if (!confirm('رزیلر حذف شود؟')) return; await api('/api/admin/resellers/' + id, 'DELETE'); await go('resellers'); }
function resellerTopup(id) {
  const r = (S.resellers || []).find(x => x.id === id) || {};
  openModal('<h3>شارژ کیف پول — ' + esc(r.name || '') + '</h3>' +
    '<label>مبلغ (تومان)</label><input id="t_amount" value="100000">' +
    '<label>یادداشت</label><input id="t_note" value="شارژ دستی">' +
    '<div class="row"><button class="ok" onclick="topupSave(' + id + ')">انجام</button>' +
    '<button class="ghost" onclick="closeModal()">انصراف</button></div>');
}
async function topupSave(id) {
  const d = await api('/api/admin/resellers/topup', 'POST', { reseller_id: id, amount: Number($('t_amount').value || 0), note: $('t_note').value });
  closeModal(); toast('شارژ شد · موجودی: ' + money(d.balance)); await go('resellers');
}

// ═════════════════════ کیف پول / تراکنش‌ها ═════════════════════
function pageWallet() {
  const rows = (S.wallet || []).map(t => '<tr><td>#' + t.id + '</td>' +
    '<td>' + esc(t.reseller_name || '—') + '</td>' +
    '<td><b>' + money(t.amount) + '</b></td>' +
    '<td>' + esc(t.kind === 'topup' ? 'شارژ' : (t.kind === 'purchase' ? 'خرید' : t.kind)) + '</td>' +
    '<td><span class="pill ' + (t.status === 'approved' ? 'ok' : (t.status === 'pending' ? 'warn' : 'bad')) + '">' + esc(t.status) + '</span></td>' +
    '<td class="mut">' + esc((t.note || '').slice(0, 40)) + '</td>' +
    '<td><div class="row">' + (t.status === 'pending' ?
      '<button class="sm ok" onclick="txDecide(' + t.id + ',\'approve\')">تأیید</button>' +
      '<button class="sm bad" onclick="txDecide(' + t.id + ',\'reject\')">رد</button>' : '') + '</div></td></tr>').join('')
    || '<tr><td colspan="7" class="mut">تراکنشی ثبت نشده است.</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>💰 تراکنش‌های کیف پول</h3>' +
    '<button class="ghost" onclick="loadWallet().then(draw)">به‌روزرسانی</button></div>' +
    '<table><thead><tr><th>#</th><th>رزیلر</th><th>مبلغ</th><th>نوع</th><th>وضعیت</th><th>یادداشت</th><th></th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table></div>' + modal();
}
async function txDecide(id, action) {
  await api('/api/admin/wallet/' + id + '/' + action, 'POST', {});
  toast(action === 'approve' ? 'تأیید شد' : 'رد شد'); await go('wallet');
}

// ═════════════════════ اعلان‌ها ═════════════════════
function pageAnnouncements() {
  const rows = (S.announcements || []).map(a => '<tr>' +
    '<td><b>' + esc(a.title) + '</b><div class="mut">' + esc((a.body || '').slice(0, 90)) + '</div></td>' +
    '<td><span class="pill">' + esc(a.level) + '</span></td>' +
    '<td>' + (a.enabled ? '<span class="pill ok">فعال</span>' : '<span class="pill bad">غیرفعال</span>') + '</td>' +
    '<td><div class="row"><button class="sm ghost" onclick="annEdit(' + a.id + ')">ویرایش</button>' +
    '<button class="sm bad" onclick="annDel(' + a.id + ')">حذف</button></div></td></tr>').join('')
    || '<tr><td colspan="4" class="mut">اعلانی ثبت نشده است.</td></tr>';
  return '<div class="grid g2">' +
    '<div class="card"><h3>📣 نوار اعلان بالای سایت</h3>' +
    '<label>متن (خالی = مخفی)</label><input id="a_bar" value="' + esc(S.data.bar || '') + '">' +
    '<button onclick="saveBar()">ذخیره نوار</button>' +
    '<div class="mut" style="margin-top:10px">این متن بالای سایت عمومی و در کانال اطلاع‌رسانی نمایش داده می‌شود (مثلاً: «۱۰٪ تخفیف تا پایان هفته»).</div></div>' +
    '<div class="card"><h3>🆕 اعلان جدید</h3>' +
    '<label>عنوان</label><input id="an_title">' +
    '<label>متن</label><textarea id="an_body"></textarea>' +
    '<label>نوع</label><select id="an_level"><option value="info">اطلاعیه</option><option value="ok">خبر خوب</option>' +
    '<option value="warn">هشدار</option><option value="bad">قطعی</option></select>' +
    '<button onclick="annSave(0)">افزودن</button></div>' +
    '<div class="card" style="grid-column:1/-1"><h3>📋 اعلان‌ها</h3>' +
    '<table><tbody>' + rows + '</tbody></table>' +
    '<div class="mut" style="margin-top:10px">اعلان‌های فعال در صفحه‌ی اصلی سایت و در پاسخ <code style="display:inline;padding:2px 6px">/api/site</code> نمایش داده می‌شوند؛ برای ارسال به کاربران، از «پیام همگانی» در تنظیمات استفاده کن.</div></div>' +
    '</div>' + modal();
}
async function saveBar() { await api('/api/admin/settings', 'POST', { announce_bar: $('a_bar').value }); toast('ذخیره شد ✓'); }
function annEdit(id) {
  const a = (S.announcements || []).find(x => x.id === id) || {};
  openModal('<h3>ویرایش اعلان</h3><label>عنوان</label><input id="an_title" value="' + esc(a.title || '') + '">' +
    '<label>متن</label><textarea id="an_body">' + esc(a.body || '') + '</textarea>' +
    '<label>نوع</label><select id="an_level">' +
    ['info','ok','warn','bad'].map(l => '<option value="' + l + '"' + (a.level === l ? ' selected' : '') + '>' + l + '</option>').join('') +
    '</select><div class="row"><button class="ok" onclick="annSave(' + id + ')">ذخیره</button>' +
    '<button class="ghost" onclick="closeModal()">انصراف</button></div>');
}
async function annSave(id) {
  await api('/api/admin/announcements', 'POST', { id: id || null, title: $('an_title').value, body: $('an_body').value,
    level: $('an_level').value, enabled: true });
  closeModal(); toast('ذخیره شد ✓'); await go('announcements');
}
async function annDel(id) { if (!confirm('اعلان حذف شود؟')) return; await api('/api/admin/announcements/' + id, 'DELETE'); await go('announcements'); }

// ═════════════════════ برند و ظاهر ═════════════════════
function pageBrand() {
  const st = S.data.settings || {};
  const c1 = st.brand_color || '#5b6cff', c2 = st.brand_color2 || '#a855f7';
  return '<div class="grid g2">' +
    '<div class="card"><h3>🎨 هویت برند</h3>' +
      '<label>نام برند</label><input id="b_name" value="' + esc(st.brand_name || '') + '">' +
      '<label>شعار</label><input id="b_slogan" value="' + esc(st.brand_slogan || '') + '">' +
      '<label>لوگو (یک کاراکتر یا ایموجی)</label><input id="b_logo" value="' + esc(st.brand_logo || '◆') + '">' +
      '<label>تیتر اصلی صفحه‌ی اول</label><input id="b_hero" value="' + esc(st.brand_hero || '') + '">' +
      '<label>ویژگی‌ها (هر خط یک مورد)</label><textarea id="b_features">' + esc(st.brand_features || '') + '</textarea>' +
      '<div class="row"><div><label>رنگ اصلی</label><input id="b_c1" type="color" value="' + esc(c1) + '" style="height:44px"></div>' +
      '<div><label>رنگ دوم</label><input id="b_c2" type="color" value="' + esc(c2) + '" style="height:44px"></div>' +
      '<div style="flex:1"><label>پیش‌نمایش</label><span class="swatch" style="background:linear-gradient(135deg,' + esc(c1) + ',' + esc(c2) + ')"></span></div></div>' +
      '<label>عنوان پنل</label><input id="b_panel" value="' + esc(st.panel_title || '') + '">' +
      '<label>وضعیت سایت عمومی</label><select id="b_mode">' +
      ['marketing:سایت کامل','app:بدون سایت (فقط پنل)','countdown:صفحه‌ی «به‌زودی برمی‌گردیم»']
        .map(x => { const p = x.split(':'); return '<option value="' + p[0] + '"' + (st.site_mode === p[0] ? ' selected' : '') + '>' + p[1] + '</option>'; }).join('') +
      '</select>' +
      '<button onclick="saveBrand()">ذخیره</button></div>' +
    '<div class="card"><h3>🔗 دامنه و مسیرها</h3>' +
      '<label>دامنه‌ی عمومی (لینک ساب با این ساخته می‌شود)</label><input id="b_base" value="' + esc(st.public_base_url || '') + '">' +
      '<label>دامنه‌ی اختصاصی (اختیاری)</label><input id="b_domain" value="' + esc(st.custom_domain || '') + '" placeholder="sub.example.com">' +
      '<label>مسیر مخفی پنل</label><input id="b_secret" value="' + esc(st.secret_path || '') + '">' +
      '<div class="mut">پنل فعلاً روی <code style="display:inline;padding:2px 6px">' + esc(st.secret_path || '') + '</code> است. ' +
      'با تغییر آن، مسیر قبلی بسته می‌شود (صفحه‌ی ورود جدید را ذخیره کن).</div>' +
      '<label>لینک پشتیبانی</label><input id="b_contact" value="' + esc(st.support_url || '') + '">' +
      '<label>شماره کارت</label><input id="b_card" value="' + esc(st.brand_card_number || '') + '">' +
      '<label>نام دارنده کارت</label><input id="b_holder" value="' + esc(st.brand_card_holder || '') + '">' +
      '<label>نوار اعلان</label><input id="b_bar" value="' + esc(st.announce_bar || '') + '">' +
      '<div class="row"><button onclick="saveBrand()">ذخیره</button>' +
      '<a href="/" target="_blank"><button class="ghost">مشاهده‌ی سایت</button></a></div></div>' +
    '</div>' + modal();
}
async function saveBrand() {
  const body = { brand_name: $('b_name').value, brand_slogan: $('b_slogan').value, brand_logo: $('b_logo').value,
    brand_hero: $('b_hero').value, brand_features: $('b_features').value, brand_color: $('b_c1').value,
    brand_color2: $('b_c2').value, panel_title: $('b_panel').value, site_mode: $('b_mode').value,
    public_base_url: $('b_base').value, custom_domain: $('b_domain').value, secret_path: $('b_secret').value,
    support_url: $('b_contact').value, brand_card_number: $('b_card').value, brand_card_holder: $('b_holder').value,
    announce_bar: $('b_bar').value };
  await api('/api/admin/settings', 'POST', body);
  toast('ذخیره شد ✓');
  if ($('b_secret').value && $('b_secret').value !== ADMIN) {
    toast('مسیر پنل تغییر کرد؛ چند ثانیه دیگر به مسیر جدید می‌رویم…');
    setTimeout(() => { location.href = $('b_secret').value; }, 1600);
  }
}

// ═════════════════════ آموزش راه‌اندازی ═════════════════════
function stepsHtml() {
  return (S.steps || []).map(st => {
    const files = Object.keys(S.files || {});
    return '<div class="card" style="margin-bottom:12px"><div class="step">' +
      '<div class="num">' + esc(st.icon || '•') + '</div>' +
      '<h4>' + esc(st.title) + ' <span class="pill">' + esc(st.time || '') + '</span></h4>' +
      '<div>' + md(st.text || '') + '</div>' +
      (st.tip ? '<div class="tip">💡 ' + md(st.tip) + '</div>' : '') +
      (st.code ? '<pre>' + esc(st.code) + '</pre><div class="row"><button class="sm" onclick="copy(' + J(st.code) + ')">کپی</button>' +
        (st.key === 'step_repo' || st.key === 'step_panel' ? files.map(f => '<button class="sm ghost" onclick="dlFile(\'' + f + '\')">' + f + '</button>').join('') : '') +
        '<button class="sm ghost" onclick="editStep(\'' + st.key + '\')">ویرایش متن</button>' +
        '<button class="sm ghost" onclick="resetStep(\'' + st.key + '\')">بازگردانی پیش‌فرض</button></div>' : '') +
      '</div></div>';
  }).join('');
}
function pageSetup() {
  const files = Object.keys(S.files || {});
  return '<div class="card" style="margin-bottom:14px"><div class="row" style="justify-content:space-between">' +
    '<h3>🎓 آموزش راه‌اندازی (گام‌به‌گام)</h3>' +
    '<div class="row"><button class="ghost" onclick="loadSetup().then(draw)">به‌روزرسانی</button></div></div>' +
    '<div class="mut">این راهنما داخل خود پنل است و می‌توانی متن هر بخش را ویرایش کنی. فایل‌های لازم هم برای دانلود آماده‌اند.</div>' +
    '<div class="grid g2" style="margin-top:12px">' +
      '<div><b>محتوای سایت پوششی</b><div class="mut">نود و پنل هر بازدید ناشناس را به یک سایت معمولی می‌فرستند (فروشگاه/شرکت/وبلاگ). ' +
      'متغیر <code style="display:inline;padding:2px 6px">MLP_DECOY</code> روی سرویس نود: auto | shop | corp | blog | none</div></div>' +
      '<div><b>نصب روی VPS</b><div class="mut">دستور سریع:</div><pre>' + esc(S.data.installer || '') + '</pre>' +
      '<button class="sm" onclick="copy(' + J(S.data.installer || '') + ')">کپی دستور</button></div>' +
    '</div>' +
    (files.length ? '<div class="row" style="margin-top:10px">' + files.map(f => '<button class="sm ghost" onclick="dlFile(\'' + f + '\')">⬇ ' + f + '</button>').join('') + '</div>' : '') +
    '</div>' + stepsHtml() + modal();
}
function dlFile(name) { download(name, S.files[name] || ''); toast('فایل ' + name + ' دانلود شد'); }
function editStep(key) {
  const st = (S.steps || []).find(x => x.key === key) || {};
  openModal('<h3>ویرایش بخش آموزش</h3>' +
    '<label>عنوان</label><input id="s_title" value="' + esc(st.title || '') + '">' +
    '<label>زمان تخمینی</label><input id="s_time" value="' + esc(st.time || '') + '">' +
    '<label>متن (مارک‌داون ساده: **پرچم‌دار** و `کد`)</label><textarea id="s_text" style="min-height:170px">' + esc(st.text || '') + '</textarea>' +
    '<label>نکته</label><input id="s_tip" value="' + esc(st.tip || '') + '">' +
    '<label>بلوک کد</label><textarea id="s_code" style="direction:ltr;text-align:left">' + esc(st.code || '') + '</textarea>' +
    '<div class="row"><button class="ok" onclick="saveStep(\'' + key + '\')">ذخیره</button>' +
    '<button class="ghost" onclick="closeModal()">انصراف</button></div>');
}
async function saveStep(key) {
  await api('/api/admin/tutorial', 'POST', { key: key, title: $('s_title').value, time: $('s_time').value,
    text: $('s_text').value, tip: $('s_tip').value, code: $('s_code').value });
  closeModal(); toast('ذخیره شد ✓'); await go('setup');
}
async function resetStep(key) {
  await api('/api/admin/tutorial', 'POST', { key: key, reset: true });
  toast('به حالت پیش‌فرض برگشت'); await go('setup');
}
function openSetup() { go('setup'); }

// ═════════════════════ رویدادها ═════════════════════
function pageEvents() {
  const rows = (S.data.eventsFull || []).map(e => '<tr><td class="mut">' + new Date(e.ts * 1000).toLocaleString('fa-IR') + '</td>' +
    '<td><span class="pill ' + (e.level === 'error' ? 'bad' : (e.level === 'warn' ? 'warn' : 'ok')) + '">' + esc(e.kind) + '</span></td>' +
    '<td>' + esc(e.message) + '</td></tr>').join('') || '<tr><td colspan="3" class="mut">رویدادی نیست</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>📋 رویدادها</h3>' +
    '<div class="row"><button class="ghost" onclick="loadEvents().then(draw)">به‌روزرسانی</button>' +
    '<button class="bad" onclick="eventsClear()">پاک کردن</button></div></div>' +
    '<table><tbody>' + rows + '</tbody></table></div>' + modal();
}
async function eventsClear() { if (!confirm('همه رویدادها پاک شوند؟')) return; await api('/api/admin/events', 'DELETE'); await go('events'); }

// ═════════════════════ تنظیمات ═════════════════════
function pageSettings() {
  const st = S.data.settings || {};
  const f = (id, label, val, type) => '<label>' + label + '</label><input id="' + id + '" type="' + (type || 'text') + '" value="' + esc(val || '') + '">';
  const sel = (id, label, val) => '<label>' + label + '</label><select id="' + id + '">' +
    '<option value="0"' + (val !== '1' ? ' selected' : '') + '>خاموش</option>' +
    '<option value="1"' + (val === '1' ? ' selected' : '') + '>روشن</option></select>';
  return '<div class="grid g2">' +
    '<div class="card"><h3>🤖 ربات تلگرام</h3>' +
      f('s_bot_token', 'توکن ربات', st.bot_token) +
      f('s_bot_admin_ids', 'آیدی عددی ادمین‌ها (با کاما)', st.bot_admin_ids) +
      f('s_bot_force_channel', 'کانال اجباری (اختیاری)', st.bot_force_channel) +
      sel('s_bot_enabled', 'وضعیت ربات', st.bot_enabled) +
      sel('s_bot_sales_enabled', 'فروش خودکار', st.bot_sales_enabled) +
      '<label>متن خوش‌آمد (ربات)</label><textarea id="s_text">' + esc(st.bot_text_start || '') + '</textarea>' +
      '<div class="row"><button onclick="saveSettings()">ذخیره</button>' +
      '<button class="ghost" onclick="botTest()">تست ربات</button>' +
      '<button class="ghost" onclick="broadcast()">پیام همگانی</button></div>' +
      '<div id="botResult" class="mut" style="margin-top:8px"></div></div>' +
    '<div class="card"><h3>⚙️ عمومی</h3>' +
      f('s_sub_path', 'مسیر ساب', st.sub_path) +
      f('s_support_url', 'لینک پشتیبانی', st.support_url) +
      f('s_config_title', 'قالب نام کانفیگ', st.config_title || '{flag} {name} | {panel}') +
      sel('s_tutorial_enabled', 'نمایش تب آموزش', st.tutorial_enabled) +
      '<label>کانال اطلاع‌رسانی (شناسه یا لینک)</label><input id="s_channel" value="' + esc(st.bot_force_channel || '') + '">' +
      '<button onclick="saveSettings()">ذخیره</button>' +
      '<div class="mut" style="margin-top:10px">دامنه‌ی تشخیص‌داده‌شده: <code style="display:inline;padding:2px 6px">' + esc(st.detected_base || '—') + '</code></div></div>' +
    '<div class="card"><h3>🔐 رمز عبور و امنیت</h3>' +
      f('s_cur_pass', 'رمز فعلی', '', 'password') + f('s_new_pass', 'رمز جدید', '', 'password') +
      '<button onclick="changePass()">تغییر رمز</button>' +
      '<div class="mut" style="margin-top:10px">مسیر پنل: <code style="display:inline;padding:2px 6px">' + esc(st.secret_path || '') + '</code> ' +
      '— برای تغییر به تب «برند و ظاهر» برو.</div></div>' +
    '<div class="card"><h3>ℹ️ درباره</h3>' +
      '<div class="mut">نسخه ' + esc("__VERSION__") + ' · پایگاه‌داده: <code style="display:inline;padding:2px 6px">mlp.sqlite3</code></div>' +
      '<div class="mut" style="margin-top:8px">API نودها: <code style="display:inline;padding:2px 6px">/api/node/sync</code> و <code style="display:inline;padding:2px 6px">/api/node/report</code></div>' +
      '<div class="mut" style="margin-top:8px">سلامت: <a href="/healthz" target="_blank">/healthz</a> · ' +
      'API عمومی سایت: <a href="/api/site" target="_blank">/api/site</a></div>' +
      '<div class="row" style="margin-top:12px"><a href="/plans" target="_blank"><button class="ghost">تعرفه‌ها</button></a>' +
      '<a href="/status" target="_blank"><button class="ghost">وضعیت</button></a>' +
      '<a href="/download" target="_blank"><button class="ghost">راهنمای اتصال</button></a></div></div>' +
    '</div>' + modal();
}
async function saveSettings() {
  const body = { bot_token: $('s_bot_token').value, bot_admin_ids: $('s_bot_admin_ids').value,
    bot_force_channel: $('s_bot_force_channel').value, bot_enabled: $('s_bot_enabled').value,
    bot_sales_enabled: $('s_bot_sales_enabled').value, bot_text_start: $('s_text').value,
    sub_path: $('s_sub_path').value, support_url: $('s_support_url').value, config_title: $('s_config_title').value,
    tutorial_enabled: $('s_tutorial_enabled').value, announce_bar: $('s_channel').value };
  await api('/api/admin/settings', 'POST', body); toast('ذخیره شد ✓');
}
async function changePass() {
  try { await api('/api/admin/password', 'POST', { current: $('s_cur_pass').value, new: $('s_new_pass').value }); toast('رمز تغییر کرد ✓'); }
  catch (e) { toast(e.message, 1); }
}
async function botTest() {
  try { const d = await api('/api/admin/bot/test', 'POST', {});
    $('botResult').textContent = d.ok ? ('ربات: @' + d.username + ' · ادمین‌ها: ' + d.admins) : ('خطا: ' + d.error); }
  catch (e) { toast(e.message, 1); }
}
async function broadcast() { const t = prompt('متن پیام همگانی:'); if (!t) return; const d = await api('/api/admin/broadcast', 'POST', { text: t }); toast('ارسال شد: ' + d.sent); }

// ═════════════════════ روتر ═════════════════════
const PAGE_FNS = { dash: pageDash, locations: pageLocations, users: pageUsers, plans: pagePlans, orders: pageOrders,
  resellers: pageResellers, wallet: pageWallet, announcements: pageAnnouncements, brand: pageBrand, setup: pageSetup,
  events: pageEvents, settings: pageSettings };
const PAGE_LOADERS = { dash: loadDash, locations: loadLocations, users: loadUsers, plans: loadPlans, orders: loadOrders,
  resellers: loadResellers, wallet: loadWallet, announcements: loadAnnouncements, brand: loadSettings, setup: loadSetup,
  events: loadEvents, settings: loadSettings };
const PAGES = [['dash','داشبورد'],['locations','لوکیشن‌ها'],['users','کاربران'],['plans','پلن‌ها'],['orders','سفارش‌ها'],
  ['resellers','رزیلرها'],['wallet','کیف پول'],['announcements','اعلان‌ها'],['brand','برند و ظاهر'],['setup','آموزش راه‌اندازی'],
  ['events','رویدادها'],['settings','تنظیمات']];

function drawNav() {
  $('nav').innerHTML = PAGES.map(p => '<button class="' + (S.page === p[0] ? 'on' : '') + '" onclick="go(\'' + p[0] + '\')">' + p[1] + '</button>').join('');
}
function draw() { drawNav(); $('main').innerHTML = PAGE_FNS[S.page](); }
async function go(page) {
  S.page = page; draw();
  try { await PAGE_LOADERS[page](); } catch (e) { toast(e.message, 1); }
  draw();
}
async function refreshAll() { await go(S.page); toast('به‌روزرسانی شد'); }
async function doLogout() { await api('/api/admin/logout', 'POST', {}); location.href = ADMIN; }
async function loadDash() { S.data = Object.assign({}, S.data, await api('/api/admin/overview')); S.locs = S.data.locations || []; }
async function loadLocations() { const d = await api('/api/admin/locations'); S.locs = d.locations || []; }
async function loadUsers() { const d = await api('/api/admin/users'); S.users = d.users || []; S.locs = d.locations || [];
  try { const r = await api('/api/admin/resellers'); S.resellers = r.resellers || []; } catch (e) {} }
async function loadPlans() { const d = await api('/api/admin/plans'); S.plans = d.plans || []; }
async function loadOrders() { const d = await api('/api/admin/orders'); S.orders = d.orders || []; }
async function loadResellers() { const d = await api('/api/admin/resellers'); S.resellers = d.resellers || []; }
async function loadWallet() { const d = await api('/api/admin/wallet'); S.wallet = d.txs || []; }
async function loadAnnouncements() { const d = await api('/api/admin/announcements'); S.announcements = d.announcements || []; S.data.bar = d.bar || ''; }
async function loadEvents() { const d = await api('/api/admin/events?limit=200'); S.data.eventsFull = d.events || []; }
async function loadSettings() { const d = await api('/api/admin/settings'); S.data.settings = d.settings || {}; }
async function loadSetup() {
  const d = await api('/api/admin/tutorial');
  S.steps = d.steps || []; S.files = d.files || {}; S.data.installer = d.installer || '';
}

go('dash');
setInterval(() => { if (S.page === 'dash') go('dash'); }, 30000);
"""


def _vars() -> dict[str, str]:
    brand = store.brand()
    return {
        "__TITLE__": store.get_setting("panel_title") or brand.get("name") or APP_NAME,
        "__BRAND__": brand.get("name") or APP_NAME,
        "__LOGO__": brand.get("logo") or "◆",
        "__C1__": brand.get("color") or "#5b6cff",
        "__C2__": brand.get("color2") or "#a855f7",
        "__VERSION__": APP_VERSION,
        "__APP__": APP_NAME,
        "__CSS__": CSS,
        "__JS__": JS,
    }


def _fill(template: str, extra: dict[str, str] | None = None) -> str:
    data = _vars()
    if extra:
        data.update(extra)
    out = template
    for key, value in data.items():
        out = out.replace(key, value)
    return out


def login_html(title: str, admin_path: str = "") -> str:
    return _fill(
        """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<meta name="robots" content="noindex,nofollow">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css">
<style>__CSS__</style></head><body>
<div class="login-wrap"><div class="login">
  <h1><span class="mark">__LOGO__</span> __TITLE__</h1>
  <p>ورود مدیر · نسخه __VERSION__</p>
  <label>نام کاربری</label><input id="u" value="admin">
  <label>رمز عبور</label><input id="p" type="password" onkeydown="if(event.key==='Enter')doLogin()">
  <button style="width:100%" onclick="doLogin()">ورود به پنل</button>
  <div class="mut" id="err" style="margin-top:10px;color:var(--bad)"></div>
</div></div>
<script>
async function doLogin(){
  var res = await fetch('/api/admin/login',{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({username:document.getElementById('u').value,password:document.getElementById('p').value})});
  if(res.ok){ location.reload(); } else {
    var d = {}; try { d = await res.json(); } catch(e){}
    document.getElementById('err').textContent = d.detail || 'ورود ناموفق';
  }
}
</script></body></html>"""
    )


def app_html(title: str, admin_path: str = "") -> str:
    return _fill(
        """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<meta name="robots" content="noindex,nofollow">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css">
<style>__CSS__</style></head><body>
<header>
  <div class="hrow">
    <div class="brand"><span class="dot"></span>__LOGO__ __TITLE__</div>
    <span class="pill">__BRAND__</span>
    <div class="spacer"></div>
    <button class="ghost sm" onclick="go('setup')">🎓 آموزش</button>
    <button class="ghost sm" onclick="refreshAll()">به‌روزرسانی</button>
    <button class="ghost sm" onclick="doLogout()">خروج</button>
  </div>
  <nav id="nav"></nav>
</header>
<main id="main"><div class="card">در حال بارگذاری…</div></main>
<div class="toast" id="toast"></div>
<div class="modal" id="modal"><div class="box" id="modalBox"></div></div>
<script>
__JS__
</script></body></html>""",
        {"__ADMIN_PATH__": admin_path or "/"},
    )
