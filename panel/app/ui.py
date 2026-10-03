"""رابط کاربری وب پنل (HTML/CSS/JS تک‌فایلی، RTL فارسی)."""

from __future__ import annotations

from .settings import APP_NAME, APP_VERSION

CSS = """
:root{--bg:#080d1c;--bg2:#0d1428;--card:#111a33;--card2:#16203f;--line:#233056;--fg:#eaf0ff;--mut:#8ea0c9;
--acc:#5b6cff;--acc2:#a855f7;--ok:#22c55e;--warn:#f59e0b;--bad:#ef4444;--radius:14px}
*{box-sizing:border-box;font-family:Vazirmatn,Tahoma,'Segoe UI',sans-serif}
body{margin:0;background:var(--bg);color:var(--fg);direction:rtl;font-size:14px}
a{color:var(--acc)}
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;
background:radial-gradient(900px 500px at 70% -10%,#1a2260 0%,var(--bg) 60%)}
.login{width:100%;max-width:380px;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:26px}
.login h1{margin:0 0 6px;font-size:20px}
.login p{margin:0 0 18px;color:var(--mut);font-size:12px}
input,select,textarea{width:100%;background:#0c142b;border:1px solid var(--line);color:var(--fg);
border-radius:10px;padding:10px;font-size:13px;margin-bottom:10px;font-family:inherit}
label{font-size:12px;color:var(--mut);display:block;margin-bottom:4px}
button{cursor:pointer;border:0;border-radius:10px;padding:10px 14px;background:var(--acc);color:#fff;font-weight:700;font-size:13px}
button:hover{filter:brightness(1.08)}
button.ghost{background:var(--card2);color:var(--fg)}
button.ok{background:var(--ok)}button.bad{background:var(--bad)}button.warn{background:var(--warn)}
button.sm{padding:6px 10px;font-size:12px}
header{position:sticky;top:0;z-index:5;background:rgba(8,13,28,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.hrow{max-width:1180px;margin:0 auto;padding:12px 16px;display:flex;align-items:center;gap:12px}
.brand{font-weight:800;font-size:16px;display:flex;align-items:center;gap:8px}
.dot{width:9px;height:9px;border-radius:99px;background:var(--ok);box-shadow:0 0 12px var(--ok)}
.spacer{flex:1}
nav{max-width:1180px;margin:0 auto;padding:0 12px 8px;display:flex;gap:6px;overflow-x:auto}
nav button{background:transparent;color:var(--mut);border-radius:10px;padding:8px 12px;font-weight:600;white-space:nowrap}
nav button.on{background:var(--card2);color:var(--fg)}
main{max-width:1180px;margin:0 auto;padding:18px 16px 60px}
.grid{display:grid;gap:12px}
.g4{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}
.g2{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px}
.card h3{margin:0 0 12px;font-size:15px;display:flex;align-items:center;gap:8px}
.stat small{color:var(--mut);font-size:12px}
.stat b{display:block;font-size:22px;margin-top:6px}
.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.pill{font-size:11px;padding:4px 9px;border-radius:99px;background:var(--card2);color:var(--mut);display:inline-block}
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
code,pre{direction:ltr;text-align:left;background:#0a1024;border:1px solid var(--line);border-radius:10px;padding:10px;
font-size:11.5px;overflow:auto;display:block;color:#cfe0ff;white-space:pre-wrap;word-break:break-all}
.modal{position:fixed;inset:0;background:rgba(3,6,14,.78);display:none;align-items:flex-start;justify-content:center;padding:24px 14px;z-index:20;overflow:auto}
.modal.on{display:flex}
.modal .box{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;width:100%;max-width:660px}
.toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#111a36;border:1px solid var(--line);
padding:11px 18px;border-radius:12px;opacity:0;transition:.25s;z-index:40;font-size:13px}
.toast.on{opacity:1}
.chk{display:inline-flex;align-items:center;gap:6px;background:#0c142b;border:1px solid var(--line);padding:7px 10px;border-radius:10px;font-size:12px;margin:0 0 8px 8px}
.chk input{width:auto;margin:0}
"""

JS = r"""
const S = { page: 'dash', data: {}, locs: [], users: [], plans: [], orders: [] };
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const J = (x) => JSON.stringify(x == null ? '' : x);

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
function fmtBytes(b) {
  b = Number(b) || 0; const u = ['B','KB','MB','GB','TB']; let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return (b >= 100 ? Math.round(b) : b.toFixed(2)) + ' ' + u[i];
}
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

function pageDash() {
  const s = S.data.stats || {}, locs = S.data.locations || [], tr = S.data.traffic || [], ev = S.data.events || [];
  const max = Math.max(1, ...tr.map(x => x.bytes));
  const bars = tr.length ? tr.map(x => '<div title="' + x.hour + ' · ' + fmtBytes(x.bytes) + '" style="flex:1;display:flex;align-items:flex-end;height:100%">' +
      '<div style="width:100%;height:' + Math.max(3, Math.round(x.bytes / max * 100)) + '%;background:linear-gradient(180deg,#5b6cff,#a855f7);border-radius:4px 4px 0 0"></div></div>').join('')
    : '<div class="mut">هنوز ترافیکی ثبت نشده است.</div>';
  const locCards = locs.map(l => {
    const st = l.status || {};
    return '<div class="card stat" style="border-color:' + (l.online ? 'rgba(34,197,94,.35)' : 'var(--line)') + '">' +
      '<div class="row" style="justify-content:space-between"><div><div style="font-weight:700">' + esc(l.flag) + ' ' + esc(l.name) + '</div>' +
      '<small class="mut">' + esc(l.host || 'بدون دامنه') + '</small></div>' +
      '<span class="pill ' + (l.online ? 'ok' : 'bad') + '">' + (l.online ? 'آنلاین' : 'آفلاین') + '</span></div>' +
      '<div class="grid gridstat" style="margin-top:10px;grid-template-columns:1fr 1fr">' +
      '<div><small class="mut">کاربران آنلاین</small><b>' + (st.users_online || 0) + '</b></div>' +
      '<div><small class="mut">کل کاربران</small><b>' + (st.clients || 0) + '</b></div>' +
      '<div><small class="mut">CPU</small><b>' + (st.cpu ? st.cpu + '%' : '—') + '</b></div>' +
      '<div><small class="mut">RAM</small><b>' + (st.mem ? st.mem + '%' : '—') + '</b></div></div>' +
      '<div class="mut" style="margin-top:8px">آخرین خبر: ' + ago(l.seen_ago) + '</div></div>';
  }).join('') || '<div class="card mut">هنوز لوکیشنی نساخته‌ای. از تب «لوکیشن‌ها» شروع کن.</div>';
  return '<div class="grid g4">' +
    '<div class="card stat"><small>کاربران</small><b>' + (s.users || 0) + '</b><div class="mut">فعال ' + (s.active_users || 0) + ' · محدود ' + (s.limited_users || 0) + ' · منقضی ' + (s.expired_users || 0) + '</div></div>' +
    '<div class="card stat"><small>لوکیشن‌های آنلاین</small><b>' + (s.online_locations || 0) + '/' + (s.locations || 0) + '</b><div class="mut">وضعیت لحظه‌ای</div></div>' +
    '<div class="card stat"><small>ترافیک ۲۴ ساعت</small><b>' + fmtBytes(s.total_traffic || 0) + '</b><div class="mut">مجموع ثبت‌شده</div></div>' +
    '<div class="card stat"><small>سفارش در انتظار</small><b>' + (s.pending_orders || 0) + '</b><div class="mut">برای تأیید</div></div></div>' +
    '<div class="card" style="margin-top:14px"><h3>📈 ترافیک ساعتی</h3><div style="display:flex;gap:3px;align-items:flex-end;height:120px">' + bars + '</div></div>' +
    '<h3 style="margin:18px 4px 8px">🛰 لوکیشن‌ها</h3><div class="grid g4">' + locCards + '</div>' +
    '<div class="card" style="margin-top:16px"><h3>🧾 آخرین رویدادها</h3>' +
    (ev.map(e => '<div class="row" style="border-bottom:1px solid var(--line);padding:7px 0">' +
      '<span class="pill ' + (e.level === 'error' ? 'bad' : (e.level === 'warn' ? 'warn' : 'ok')) + '">' + esc(e.kind) + '</span>' +
      '<span style="flex:1">' + esc(e.message) + '</span></div>').join('') || '<div class="mut">رویدادی نیست</div>') + '</div>' + modal();
}

function pageLocations() {
  const rows = (S.locs || []).map(l => '<tr>' +
    '<td><b>' + esc(l.flag) + ' ' + esc(l.name) + '</b><div class="mut">' + esc(l.region || '') + '</div></td>' +
    '<td><code style="padding:4px 6px">' + esc(l.host || '—') + '</code>' +
    (l.cf_host ? '<div class="mut">CF: ' + esc(l.cf_host) + '</div>' : '') + '</td>' +
    '<td>' + (l.transports || []).map(t => '<span class="pill">' + esc(t) + '</span>').join(' ') + '</td>' +
    '<td><span class="pill ' + (l.online ? 'ok' : 'bad') + '">' + (l.online ? 'آنلاین' : 'آفلاین') + '</span><div class="mut">' + ago(l.seen_ago) + '</div></td>' +
    '<td><div class="row"><button class="sm ghost" onclick="locEdit(' + l.id + ')">ویرایش</button>' +
    '<button class="sm ghost" onclick="locEnv(' + l.id + ')">متغیرهای نود</button>' +
    '<button class="sm ghost" onclick="locRotate(' + l.id + ')">توکن جدید</button>' +
    '<button class="sm bad" onclick="locDel(' + l.id + ')">حذف</button></div></td></tr>').join('')
    || '<tr><td colspan="5" class="mut">لوکیشنی ثبت نشده است.</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>🛰 لوکیشن‌ها</h3>' +
    '<button onclick="locEdit()">+ لوکیشن جدید</button></div>' +
    '<table><thead><tr><th>نام</th><th>دامنه</th><th>ترابرد</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>' + rows + '</tbody></table>' +
    '<div class="mut" style="margin-top:12px">هر لوکیشن = یک سرویس جدا روی Railway (ریجن دلخواه) که همین ریپو را با <code style="display:inline;padding:2px 6px">MLP_ROLE=node</code> اجرا می‌کند؛ یا یک ورکر Cloudflare.</div></div>' + modal();
}

function userRow(u) {
  const limit = Number(u.limit_bytes) || 0, used = Number(u.used_bytes) || 0;
  const pct = limit ? Math.min(100, Math.round(used * 100 / limit)) : 0;
  const cls = u.status === 'active' ? 'ok' : (u.status === 'disabled' ? '' : 'bad');
  const locs = (u.locations || []).length;
  return '<tr><td><b>' + esc(u.name || 'بی‌نام') + '</b><div class="mut">#' + u.id + (u.telegram_id ? ' · tg:' + esc(u.telegram_id) : '') + '</div></td>' +
    '<td><span class="pill ' + cls + '">' + esc(u.status) + '</span></td>' +
    '<td style="min-width:130px">' + fmtBytes(used) + ' / ' + (limit ? fmtBytes(limit) : '∞') + '<div class="bar"><i style="width:' + pct + '%"></i></div></td>' +
    '<td>' + (u.days_left === null ? '∞' : u.days_left + ' روز') + '</td>' +
    '<td>' + locs + '</td>' +
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

function pagePlans() {
  const rows = (S.plans || []).map(p => '<tr><td><b>' + esc(p.name) + '</b></td><td>' + p.traffic_gb + ' GB</td>' +
    '<td>' + p.days + ' روز</td><td>' + esc(p.price || '—') + '</td><td>' + (p.max_ips || '∞') + '</td>' +
    '<td>' + (p.speed_kbps ? p.speed_kbps + ' kbps' : '∞') + '</td>' +
    '<td><span class="pill ' + (p.enabled ? 'ok' : 'bad') + '">' + (p.enabled ? 'فعال' : 'غیرفعال') + '</span></td>' +
    '<td><button class="sm ghost" onclick="planEdit(' + p.id + ')">ویرایش</button> ' +
    '<button class="sm bad" onclick="planDel(' + p.id + ')">حذف</button></td></tr>').join('')
    || '<tr><td colspan="8" class="mut">پلنی ثبت نشده است.</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>🛍 پلن‌های فروش</h3>' +
    '<button onclick="planEdit()">+ پلن جدید</button></div>' +
    '<table><thead><tr><th>نام</th><th>حجم</th><th>مدت</th><th>قیمت</th><th>IP</th><th>سرعت</th><th>وضعیت</th><th></th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table></div>' + modal();
}

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

function pageEvents() {
  const rows = (S.data.eventsFull || []).map(e => '<tr><td class="mut">' + new Date(e.ts * 1000).toLocaleString('fa-IR') + '</td>' +
    '<td><span class="pill ' + (e.level === 'error' ? 'bad' : (e.level === 'warn' ? 'warn' : 'ok')) + '">' + esc(e.kind) + '</span></td>' +
    '<td>' + esc(e.message) + '</td></tr>').join('') || '<tr><td colspan="3" class="mut">رویدادی نیست</td></tr>';
  return '<div class="card"><div class="row" style="justify-content:space-between"><h3>📋 رویدادها</h3>' +
    '<div class="row"><button class="ghost" onclick="loadEvents().then(draw)">به‌روزرسانی</button>' +
    '<button class="bad" onclick="eventsClear()">پاک کردن</button></div></div>' +
    '<table><tbody>' + rows + '</tbody></table></div>' + modal();
}

function pageSettings() {
  const st = S.data.settings || {};
  const f = (id, label, val, type) => '<label>' + label + '</label><input id="' + id + '" type="' + (type || 'text') + '" value="' + esc(val || '') + '">';
  const sel = (id, label, val) => '<label>' + label + '</label><select id="' + id + '">' +
    '<option value="0"' + (val !== '1' ? ' selected' : '') + '>خاموش</option>' +
    '<option value="1"' + (val === '1' ? ' selected' : '') + '>روشن</option></select>';
  return '<div class="grid g2">' +
    '<div class="card"><h3>⚙️ تنظیمات عمومی</h3>' +
      f('s_panel_title', 'عنوان پنل', st.panel_title) +
      f('s_config_title', 'قالب نام کانفیگ', st.config_title || '{flag} {name} | {panel}') +
      f('s_support_url', 'لینک پشتیبانی', st.support_url) +
      f('s_public_base_url', 'دامنه‌ی عمومی پنل (خالی = خودکار)', st.public_base_url) +
      f('s_sub_path', 'مسیر ساب', st.sub_path) +
      '<div class="mut" style="margin-bottom:10px">دامنه‌ی تشخیص‌داده‌شده: <code style="display:inline;padding:2px 6px">' + esc(st.detected_base || '—') + '</code></div>' +
      '<button onclick="saveSettings()">ذخیره تنظیمات</button></div>' +
    '<div class="card"><h3>🤖 ربات تلگرام</h3>' +
      f('s_bot_token', 'توکن ربات', st.bot_token) +
      f('s_bot_admin_ids', 'آیدی عددی ادمین‌ها (با کاما)', st.bot_admin_ids) +
      f('s_bot_force_channel', 'کانال اجباری (اختیاری)', st.bot_force_channel) +
      sel('s_bot_enabled', 'وضعیت ربات', st.bot_enabled) +
      sel('s_bot_sales_enabled', 'فروش خودکار', st.bot_sales_enabled) +
      '<div class="row"><button onclick="saveSettings()">ذخیره</button>' +
      '<button class="ghost" onclick="botTest()">تست ربات</button>' +
      '<button class="ghost" onclick="broadcast()">پیام همگانی</button></div>' +
      '<div id="botResult" class="mut" style="margin-top:8px"></div></div>' +
    '<div class="card"><h3>🔐 رمز عبور</h3>' +
      f('s_cur_pass', 'رمز فعلی', '', 'password') + f('s_new_pass', 'رمز جدید', '', 'password') +
      '<button onclick="changePass()">تغییر رمز</button></div>' +
    '<div class="card"><h3>ℹ️ درباره</h3>' +
      '<div class="mut">نسخه __VERSION__ · پایگاه‌داده: <code style="display:inline;padding:2px 6px">mlp.sqlite3</code></div>' +
      '<div class="mut" style="margin-top:8px">API نودها: <code style="display:inline;padding:2px 6px">/api/node/sync</code> و <code style="display:inline;padding:2px 6px">/api/node/report</code></div>' +
      '<div class="mut" style="margin-top:8px">سلامت سرویس: <a href="/healthz" target="_blank">/healthz</a></div></div></div>' + modal();
}

const PAGE_FNS = { dash: pageDash, locations: pageLocations, users: pageUsers, plans: pagePlans, orders: pageOrders, events: pageEvents, settings: pageSettings };
const PAGE_LOADERS = { dash: loadDash, locations: loadLocations, users: loadUsers, plans: loadPlans, orders: loadOrders, events: loadEvents, settings: loadSettings };
const PAGES = [['dash','داشبورد'], ['locations','لوکیشن‌ها'], ['users','کاربران'], ['plans','پلن‌ها'], ['orders','سفارش‌ها'], ['events','رویدادها'], ['settings','تنظیمات']];

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
async function doLogout() { await api('/api/admin/logout', 'POST', {}); location.reload(); }

async function loadDash() { S.data = Object.assign({}, S.data, await api('/api/admin/overview')); S.locs = S.data.locations || []; }
async function loadLocations() { const d = await api('/api/admin/locations'); S.locs = d.locations || []; }
async function loadUsers() { const d = await api('/api/admin/users'); S.users = d.users || []; S.locs = d.locations || []; }
async function loadPlans() { const d = await api('/api/admin/plans'); S.plans = d.plans || []; }
async function loadOrders() { const d = await api('/api/admin/orders'); S.orders = d.orders || []; }
async function loadEvents() { const d = await api('/api/admin/events?limit=200'); S.data.eventsFull = d.events || []; }
async function loadSettings() { const d = await api('/api/admin/settings'); S.data.settings = d.settings || {}; }

// ── لوکیشن‌ها ──
function locForm(l) {
  l = l || {};
  const t = l.transports || ['ws'];
  return '<h3>' + (l.id ? 'ویرایش لوکیشن' : 'لوکیشن جدید') + '</h3>' +
  '<label>نام</label><input id="l_name" value="' + esc(l.name || '') + '" placeholder="Germany">' +
  '<div class="row"><div style="flex:1"><label>فلگ</label><input id="l_flag" value="' + esc(l.flag || '🌍') + '"></div>' +
  '<div style="flex:2"><label>ریجن</label><input id="l_region" value="' + esc(l.region || '') + '" placeholder="europe-west4"></div></div>' +
  '<label>دامنه‌ی عمومی نود</label><input id="l_host" value="' + esc(l.host || '') + '" placeholder="node-eu.up.railway.app">' +
  '<label>لوکیشن Cloudflare (اختیاری)</label><input id="l_cf" value="' + esc(l.cf_host || '') + '" placeholder="mlp-cf.example.workers.dev">' +
  '<label>ترابردها</label><div>' +
    '<label class="chk"><input type="checkbox" id="l_ws"' + (t.indexOf('ws') >= 0 ? ' checked' : '') + '> WS</label>' +
    '<label class="chk"><input type="checkbox" id="l_xhttp"' + (t.indexOf('xhttp') >= 0 ? ' checked' : '') + '> XHTTP</label>' +
    '<label class="chk"><input type="checkbox" id="l_tcp"' + (t.indexOf('tcp') >= 0 ? ' checked' : '') + '> TCP</label></div>' +
  '<div class="row"><div style="flex:1"><label>مسیر WS</label><input id="l_wsp" value="' + esc(l.ws_path || '/ws') + '"></div>' +
  '<div style="flex:1"><label>مسیر XHTTP</label><input id="l_xhp" value="' + esc(l.xhttp_path || '/xhttp') + '"></div>' +
  '<div style="flex:1"><label>پورت TCP</label><input id="l_tcpp" type="number" value="' + (l.tcp_port || 0) + '"></div></div>' +
  '<label>یادداشت</label><input id="l_note" value="' + esc(l.note || '') + '">' +
  '<div class="row"><button class="ok" onclick="locSave(' + (l.id || 0) + ')">ذخیره</button>' +
  '<button class="ghost" onclick="closeModal()">انصراف</button></div>';
}
function locEdit(id) { const l = id ? (S.locs || []).find(x => x.id === id) : null; openModal(locForm(l)); }
async function locSave(id) {
  const body = { id: id || null, name: $('l_name').value, flag: $('l_flag').value, region: $('l_region').value,
    host: $('l_host').value, cf_host: $('l_cf').value, ws_path: $('l_wsp').value, xhttp_path: $('l_xhp').value,
    tcp_port: Number($('l_tcpp').value || 0), note: $('l_note').value, enabled: true,
    transports: [$('l_ws').checked ? 'ws' : null, $('l_xhttp').checked ? 'xhttp' : null, $('l_tcp').checked ? 'tcp' : null].filter(Boolean) };
  if (!body.name) { toast('نام لازم است', 1); return; }
  if (!body.transports.length) body.transports = ['ws'];
  const res = await api('/api/admin/locations', 'POST', body);
  closeModal();
  if (res.env) { openModal('<h3>متغیرهای سرویس نود</h3><pre>' + esc(res.env) + '</pre>' +
    '<div class="row" style="margin-top:10px"><button onclick="copy(' + J(res.env) + ')">کپی</button>' +
    '<a href="/" ><button class="ghost" onclick="closeModal()">فهمیدم</button></a></div>'); }
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
    '<div class="mut">این‌ها را در Railway → سرویس نود → Variables بگذار و Deploy کن.</div>' +
    '<div class="row" style="margin-top:10px"><button onclick="copy(' + J(l.env || '') + ')">کپی همه</button>' +
    '<button class="ghost" onclick="closeModal()">بستن</button></div>');
}

// ── کاربران ──
function userForm(u) {
  u = u || {};
  const gb = u.limit_bytes ? (u.limit_bytes / 1073741824).toFixed(2) : '';
  return '<h3>' + (u.id ? 'ویرایش کاربر' : 'کاربر جدید') + '</h3>' +
  '<label>نام</label><input id="u_name" value="' + esc(u.name || '') + '">' +
  '<div class="row"><div style="flex:1"><label>حجم (GB، 0=نامحدود)</label><input id="u_gb" value="' + gb + '"></div>' +
  '<div style="flex:1"><label>مدت (روز)</label><input id="u_days" value="' + (u.id ? 0 : 30) + '"></div></div>' +
  (u.id ? '<label class="chk"><input type="checkbox" id="u_extend" checked> افزودن به حجم/زمان فعلی</label>' : '') +
  '<div class="row"><div style="flex:1"><label>حداکثر IP (0=نامحدود)</label><input id="u_ips" value="' + (u.max_ips || 0) + '"></div>' +
  '<div style="flex:1"><label>سرعت (kbps، 0=نامحدود)</label><input id="u_speed" value="' + (u.speed_kbps || 0) + '"></div></div>' +
  '<label>آیدی عددی تلگرام (اختیاری)</label><input id="u_tg" value="' + esc(u.telegram_id || '') + '">' +
  '<label>یادداشت</label><input id="u_note" value="' + esc(u.note || '') + '">' +
  '<div class="row"><button class="ok" onclick="userSave(' + (u.id || 0) + ')">ذخیره</button>' +
  '<button class="ghost" onclick="closeModal()">انصراف</button></div>';
}
function userEdit(id) { const u = id ? (S.users || []).find(x => x.id === id) : null; openModal(userForm(u)); }
async function userSave(id) {
  const body = { id: id || null, name: $('u_name').value, limit_gb: Number($('u_gb').value || 0),
    days: Number($('u_days').value || 0), max_ips: Number($('u_ips').value || 0),
    speed_kbps: Number($('u_speed').value || 0), telegram_id: $('u_tg').value, note: $('u_note').value,
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

// ── پلن‌ها ──
function planForm(p) {
  p = p || {};
  return '<h3>' + (p.id ? 'ویرایش پلن' : 'پلن جدید') + '</h3>' +
  '<label>نام</label><input id="p_name" value="' + esc(p.name || '') + '">' +
  '<div class="row"><div style="flex:1"><label>حجم (GB)</label><input id="p_gb" value="' + (p.traffic_gb || 0) + '"></div>' +
  '<div style="flex:1"><label>مدت (روز)</label><input id="p_days" value="' + (p.days || 30) + '"></div>' +
  '<div style="flex:1"><label>قیمت (متن)</label><input id="p_price" value="' + esc(p.price || '') + '"></div></div>' +
  '<div class="row"><div style="flex:1"><label>حداکثر IP</label><input id="p_ips" value="' + (p.max_ips || 0) + '"></div>' +
  '<div style="flex:1"><label>سرعت kbps</label><input id="p_speed" value="' + (p.speed_kbps || 0) + '"></div></div>' +
  '<div class="row"><button class="ok" onclick="planSave(' + (p.id || 0) + ')">ذخیره</button>' +
  '<button class="ghost" onclick="closeModal()">انصراف</button></div>';
}
function planEdit(id) { const p = id ? (S.plans || []).find(x => x.id === id) : null; openModal(planForm(p)); }
async function planSave(id) {
  await api('/api/admin/plans', 'POST', { id: id || null, name: $('p_name').value, traffic_gb: Number($('p_gb').value || 0),
    days: Number($('p_days').value || 0), price: $('p_price').value, max_ips: Number($('p_ips').value || 0),
    speed_kbps: Number($('p_speed').value || 0), enabled: true });
  closeModal(); toast('ذخیره شد ✓'); await go('plans');
}
async function planDel(id) { if (!confirm('پلن حذف شود؟')) return; await api('/api/admin/plans/' + id, 'DELETE'); await go('plans'); }

// ── سفارش‌ها ──
async function orderApprove(id) { await api('/api/admin/orders/' + id + '/approve', 'POST', {}); toast('تأیید شد'); await go('orders'); }
async function orderReject(id) {
  const r = prompt('دلیل رد:', 'پرداخت تأیید نشد') || 'رد شد';
  await api('/api/admin/orders/' + id + '/reject?reason=' + encodeURIComponent(r), 'POST', {});
  toast('رد شد'); await go('orders');
}
function orderReceipt(fileId) {
  if (!fileId) { toast('رسیدی ثبت نشده', 1); return; }
  openModal('<h3>رسید</h3><div class="mut">این تصویر داخل تلگرام ادمین است؛ برای دیدن از ربات استفاده کن.</div>' +
    '<pre>' + esc(fileId) + '</pre><button class="ghost" onclick="closeModal()">بستن</button>');
}

// ── رویدادها و تنظیمات ──
async function eventsClear() { if (!confirm('همه رویدادها پاک شوند؟')) return; await api('/api/admin/events', 'DELETE'); await go('events'); }
async function saveSettings() {
  const body = { panel_title: $('s_panel_title').value, config_title: $('s_config_title').value,
    support_url: $('s_support_url').value, public_base_url: $('s_public_base_url').value, sub_path: $('s_sub_path').value,
    bot_token: $('s_bot_token').value, bot_admin_ids: $('s_bot_admin_ids').value,
    bot_force_channel: $('s_bot_force_channel').value, bot_enabled: $('s_bot_enabled').value,
    bot_sales_enabled: $('s_bot_sales_enabled').value };
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

go('dash');
setInterval(() => { if (S.page === 'dash') go('dash'); }, 30000);
"""


def login_html(title: str) -> str:
    return (
        """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css">
<style>__CSS__</style></head><body>
<div class="login-wrap"><div class="login">
  <h1>__TITLE__</h1><p>نسخه __VERSION__ · ورود مدیر</p>
  <label>نام کاربری</label><input id="u" value="admin">
  <label>رمز عبور</label><input id="p" type="password" onkeydown="if(event.key==='Enter')doLogin()">
  <button style="width:100%" onclick="doLogin()">ورود</button>
  <div class="mut" id="err" style="margin-top:10px;color:var(--bad)"></div>
</div></div>
<script>
async function doLogin(){
  var res = await fetch('/api/admin/login',{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('u').value,password:document.getElementById('p').value})});
  if(res.ok){ location.reload(); } else {
    var d = {}; try { d = await res.json(); } catch(e){}
    document.getElementById('err').textContent = d.detail || 'ورود ناموفق';
  }
}
</script></body></html>"""
        .replace("__TITLE__", title)
        .replace("__CSS__", CSS)
        .replace("__VERSION__", APP_VERSION)
    )


def app_html(title: str) -> str:
    return (
        """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css">
<style>__CSS__</style></head><body>
<header>
  <div class="hrow">
    <div class="brand"><span class="dot"></span>__TITLE__</div>
    <span class="pill">__APP__ __VERSION__</span>
    <div class="spacer"></div>
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
</script></body></html>"""
        .replace("__TITLE__", title)
        .replace("__CSS__", CSS)
        .replace("__JS__", JS.replace("__VERSION__", APP_VERSION))
        .replace("__APP__", APP_NAME)
        .replace("__VERSION__", APP_VERSION)
    )
