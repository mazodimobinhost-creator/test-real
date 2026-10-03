"""ساخت لینک‌های اشتراک، متن ساب و صفحه‌ی HTML مشتری."""

from __future__ import annotations

import base64
import html
import json
from urllib.parse import quote

from . import store
from .settings import APP_NAME, APP_VERSION

BROWSER_HINTS = ("mozilla", "chrome", "safari", "firefox", "edg")


def _fmt_bytes(n: int) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.2f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.2f} TB"


def _config_name(loc: dict, user: dict, settings: dict) -> str:
    template = settings.get("config_title") or "{flag} {name} | {panel}"
    name = template.format(
        flag=loc.get("flag") or "🌍",
        name=loc.get("name") or "location",
        panel=settings.get("panel_title") or APP_NAME,
        user=user.get("name") or "",
        region=loc.get("region") or "",
    )
    return name


def _build_link(uuid: str, loc: dict, transport: str, name: str, settings: dict) -> str | None:
    host = (loc.get("host") or "").strip().replace("https://", "").replace("http://", "").strip("/")
    cf_host = (loc.get("cf_host") or "").strip().replace("https://", "").replace("http://", "").strip("/")
    ws_path = loc.get("ws_path") or "/ws"
    xhttp_path = loc.get("xhttp_path") or "/xhttp"
    raw_host = cf_host or host
    raw_host = raw_host.split("/")[0].split(":")[0] if raw_host else ""
    if not raw_host:
        return None
    fragment = quote(name, safe="")
    if transport == "ws":
        if cf_host:
            host_header = cf_host.split("/")[0]
            path = quote(f"{ws_path}?ed=2560", safe="/")
            return (
                f"vless://{uuid}@{raw_host}:443?encryption=none&security=tls&sni={host_header}"
                f"&fp=chrome&type=ws&host={host_header}&path={path}#{fragment}"
            )
        return (
            f"vless://{uuid}@{raw_host}:443?encryption=none&security=tls&sni={host}"
            f"&fp=chrome&type=ws&host={host}&path={quote(ws_path, safe='/')}#{fragment}"
        )
    if transport == "xhttp":
        if cf_host:
            host_header = cf_host.split("/")[0]
            return (
                f"vless://{uuid}@{raw_host}:443?encryption=none&security=tls&sni={host_header}"
                f"&fp=chrome&type=xhttp&mode=stream-up&host={host_header}"
                f"&path={quote(xhttp_path, safe='/')}#{fragment}"
            )
        return (
            f"vless://{uuid}@{raw_host}:443?encryption=none&security=tls&sni={host}"
            f"&fp=chrome&type=xhttp&mode=stream-up&host={host}"
            f"&path={quote(xhttp_path, safe='/')}#{fragment}"
        )
    if transport == "tcp":
        port = int(loc.get("tcp_port") or 0)
        if not port:
            return None
        return (
            f"vless://{uuid}@{raw_host}:{port}?encryption=none&security=none"
            f"&fp=chrome&type=tcp&headerType=none#{fragment}"
        )
    return None


def build_links(user: dict, settings: dict | None = None) -> list[dict]:
    """برای هر لوکیشنِ فعالِ کاربر، یک لینک می‌سازد."""
    settings = settings or store.all_settings()
    out: list[dict] = []
    for loc in store.enabled_locations_for_user(int(user["id"])):
        transports = loc.get("transports") or ["ws"]
        for transport in transports:
            link = _build_link(user["uuid"], loc, str(transport), _config_name(loc, user, settings), settings)
            if not link:
                continue
            out.append({"location": loc, "transport": transport, "link": link})
    return out


def build_text(user: dict) -> str:
    settings = store.all_settings()
    links = build_links(user, settings)
    if not links:
        return ""
    return "\n".join(item["link"] for item in links)


def build_b64(user: dict) -> str:
    text = build_text(user)
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def is_browser(user_agent: str, accept: str = "") -> bool:
    ua = (user_agent or "").lower()
    if not ua:
        return "text/html" in (accept or "")
    if any(hint in ua for hint in BROWSER_HINTS) and "text/html" in (accept or "text/html"):
        return True
    return False


def page_json(user: dict) -> dict:
    settings = store.all_settings()
    base = store.public_base()
    sub_path = settings.get("sub_path") or "sub"
    links = build_links(user, settings)
    used = int(user.get("used_bytes") or 0)
    limit = int(user.get("limit_bytes") or 0)
    pct = round(used * 100 / limit, 1) if limit else 0
    status = store.user_status(user)
    return {
        "ok": True,
        "name": user.get("name") or "",
        "status": status,
        "status_fa": {
            "active": "فعال",
            "disabled": "غیرفعال",
            "expired": "منقضی",
            "limited": "اتمام حجم",
        }.get(status, status),
        "used": used,
        "used_h": _fmt_bytes(used),
        "limit": limit,
        "limit_h": _fmt_bytes(limit) if limit else "نامحدود",
        "remaining_h": _fmt_bytes(max(0, limit - used)) if limit else "نامحدود",
        "percent": pct,
        "expire_iso": store.ts_to_iso(int(user.get("expire_at") or 0)),
        "days_left": store.days_left(int(user.get("expire_at") or 0)),
        "sub_url": f"{base}/{sub_path}/{user['sub_token']}" if base else "",
        "configs": [
            {
                "location": item["location"].get("name"),
                "flag": item["location"].get("flag"),
                "region": item["location"].get("region"),
                "transport": item["transport"],
                "link": item["link"],
            }
            for item in links
        ],
    }


PAGE_CSS = """
:root{--bg:#0b1020;--card:#141a2f;--card2:#1b2340;--fg:#eef2ff;--mut:#93a0c4;
--acc:#6c7bff;--acc2:#a855f7;--ok:#22c55e;--warn:#f59e0b;--bad:#ef4444}
*{box-sizing:border-box;font-family:Vazirmatn,Tahoma,'Segoe UI',sans-serif}
body{margin:0;background:radial-gradient(1200px 600px at 20% -10%,#1b2350 0%,var(--bg) 55%);color:var(--fg);min-height:100vh;direction:rtl}
.wrap{max-width:760px;margin:0 auto;padding:22px}
.hero{background:linear-gradient(135deg,var(--acc),var(--acc2));border-radius:20px;padding:22px;box-shadow:0 18px 50px rgba(108,123,255,.25)}
.hero h1{margin:0 0 4px;font-size:20px}
.hero p{margin:0;opacity:.9;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:16px}
.card{background:var(--card);border:1px solid #222b4d;border-radius:16px;padding:14px}
.card b{display:block;font-size:20px;margin-top:4px}
.card small{color:var(--mut);font-size:12px}
.ring{display:flex;align-items:center;gap:16px}
.bar{height:8px;background:#232c4d;border-radius:99px;overflow:hidden;margin-top:10px}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--acc),var(--acc2))}
.loc{display:flex;align-items:center;justify-content:space-between;gap:10px;background:var(--card2);border-radius:14px;padding:12px;margin-top:10px;border:1px solid #26305a}
.loc .nm{font-weight:700;font-size:14px}
.loc .meta{color:var(--mut);font-size:11px;margin-top:2px}
button{cursor:pointer;border:0;border-radius:10px;padding:9px 12px;background:var(--acc);color:#fff;font-size:12px;font-weight:700}
button.ghost{background:#232c4d;color:var(--fg)}
button.ok{background:var(--ok)}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.tag{font-size:11px;padding:4px 8px;border-radius:99px;background:#232c4d;color:var(--mut)}
.tag.ok{background:rgba(34,197,94,.16);color:#7ee2a3}
.tag.bad{background:rgba(239,68,68,.16);color:#ff9b9b}
#qr{background:#fff;border-radius:12px;padding:8px;width:168px;height:168px;display:flex;align-items:center;justify-content:center;color:#333;font-size:11px}
.modal{position:fixed;inset:0;background:rgba(5,8,18,.75);display:none;align-items:center;justify-content:center;padding:16px;z-index:9}
.modal.on{display:flex}
.modal .box{background:var(--card);border-radius:18px;padding:18px;max-width:520px;width:100%;max-height:88vh;overflow:auto}
code{display:block;direction:ltr;text-align:left;background:#0d1225;border:1px solid #26305a;border-radius:10px;padding:10px;font-size:11px;word-break:break-all;color:#cfe0ff}
.toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#111a36;border:1px solid #2b3765;padding:10px 16px;border-radius:12px;opacity:0;transition:.25s;font-size:12px}
.toast.on{opacity:1}
footer{color:var(--mut);font-size:11px;text-align:center;margin:26px 0}
"""


def _page_shell(title: str, body: str, boot: dict) -> str:
    boot_json = json.dumps(boot, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css">
<style>{PAGE_CSS}</style></head><body>
<div class="wrap">{body}
<footer>{APP_NAME} v{APP_VERSION} · ساخته‌شده برای اتصال چندلوکیشنی</footer></div>
<div class="modal" id="cfgModal"><div class="box">
  <h3 style="margin:0 0 10px">کانفیگ‌ها</h3>
  <div id="cfgList"></div>
  <div style="margin-top:12px;text-align:center"><button class="ghost" onclick="document.getElementById('cfgModal').classList.remove('on')">بستن</button></div>
</div></div>
<div class="toast" id="toast"></div>
<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
<script>
const D = {boot_json};
function toast(m){{const t=document.getElementById('toast');t.textContent=m;t.classList.add('on');setTimeout(()=>t.classList.remove('on'),2200);}}
function copy(txt){{if(navigator.clipboard){{navigator.clipboard.writeText(txt).then(()=>toast('کپی شد ✓'),()=>fallback(txt));}}else fallback(txt);}}
function fallback(txt){{const ta=document.createElement('textarea');ta.value=txt;document.body.appendChild(ta);ta.select();try{{document.execCommand('copy');toast('کپی شد ✓');}}catch(e){{toast('کپی نشد');}}document.body.removeChild(ta);}}
function render(d){{
  document.getElementById('uName').textContent = d.name || 'کاربر';
  document.getElementById('uStatus').textContent = d.status_fa;
  document.getElementById('uUsed').textContent = d.used_h;
  document.getElementById('uLimit').textContent = d.limit_h;
  document.getElementById('uRemain').textContent = d.remaining_h;
  document.getElementById('uDays').textContent = d.days_left === null ? 'نامحدود' : (d.days_left + ' روز');
  document.getElementById('uPct').textContent = d.limit ? (d.percent + '%') : '—';
  document.getElementById('bar').style.width = (d.limit ? Math.min(100, d.percent) : 0) + '%';
  document.getElementById('sTag').className = 'tag ' + (d.status === 'active' ? 'ok' : 'bad');
  const sub = d.sub_url;
  document.getElementById('subUrl').textContent = sub || '—';
  const list = document.getElementById('cfgList');
  list.innerHTML = d.configs.map(c => `<div style="margin-bottom:8px"><div style="font-size:12px;margin-bottom:4px">{{c.flag}} {{c.location}} · {{c.transport}}</div><code>${{c.link}}</code></div>`).join('') || '<div>کانفیگی فعال نیست</div>';
  document.getElementById('locs').innerHTML = d.configs.map(c => `<div class="loc"><div><div class="nm">{{c.flag}} {{c.location}}</div><div class="meta">{{c.region}} · {{c.transport}}</div></div><button class="ghost" data-c="${{c.link}}">کپی</button></div>`).join('') || '<div class="card">هنوز لوکیشنی برای این اشتراک فعال نشده است.</div>';
  document.querySelectorAll('[data-c]').forEach(b => b.addEventListener('click', () => copy(b.getAttribute('data-c'))));
  const qr = document.getElementById('qr');
  try {{ qr.innerHTML=''; if(window.QRCode && sub) {{ new QRCode(qr, {{text: sub, width: 152, height: 152, colorDark:'#0b1020', colorLight:'#ffffff'}}); }} else {{ qr.textContent = sub || 'QR'; }} }} catch(e) {{ qr.textContent = sub || 'QR'; }}
  if (d.configs[0]) {{
    const q2 = document.getElementById('cfgQr'); q2.innerHTML='';
    try {{ if(window.QRCode) new QRCode(q2, {{text: d.configs[0].link, width: 152, height: 152, colorDark:'#0b1020', colorLight:'#ffffff'}}); }} catch(e) {{}}
  }}
}}
function poll(){{fetch('?stats=1&t=' + Date.now()).then(r=>r.json()).then(d=>{{if(d&&d.ok)render(d);}}).catch(()=>{{}});}}
render(D);
setInterval(poll, 60000);
</script></body></html>"""


def page_html(user: dict) -> str:
    data = page_json(user)
    settings = store.all_settings()
    support = settings.get("support_url") or "#"
    body = f"""
<div class="hero">
  <h1 id="uName">{html.escape(user.get('name') or 'کاربر')}</h1>
  <p>{html.escape(settings.get('panel_title') or APP_NAME)} · لینک اشتراک چندلوکیشنی</p>
  <div class="tags"><span class="tag" id="sTag">وضعیت</span><span class="tag" id="uStatus">—</span></div>
</div>
<div class="grid">
  <div class="card"><small>مصرف‌شده</small><b id="uUsed">—</b></div>
  <div class="card"><small>حجم کل</small><b id="uLimit">—</b></div>
  <div class="card"><small>باقی‌مانده</small><b id="uRemain">—</b></div>
  <div class="card"><small>اعتبار</small><b id="uDays">—</b></div>
</div>
<div class="card" style="margin-top:14px">
  <div class="ring">
    <div id="qr">QR</div>
    <div style="flex:1">
      <small style="color:var(--mut)">درصد مصرف</small>
      <b id="uPct" style="font-size:22px">—</b>
      <div class="bar"><i id="bar" style="width:0%"></i></div>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button onclick="copy(D.sub_url)">کپی لینک اشتراک</button>
        <button class="ghost" onclick="document.getElementById('cfgModal').classList.add('on')">کانفیگ‌ها</button>
        <button class="ghost" onclick="location.href=D.sub_url + (D.sub_url.indexOf('?')>-1?'&':'?') + 'format=plain'">متن ساب</button>
        <a href="{html.escape(support)}" target="_blank" rel="noopener"><button class="ok">پشتیبانی</button></a>
      </div>
      <code style="margin-top:10px" id="subUrl">—</code>
    </div>
  </div>
</div>
<h3 style="margin:18px 4px 6px;font-size:15px">لوکیشن‌ها</h3>
<div id="locs"></div>
<div class="card" style="margin-top:14px">
  <small style="color:var(--mut)">QR اولین کانفیگ</small>
  <div id="cfgQr" style="background:#fff;border-radius:12px;padding:8px;width:168px;height:168px;margin-top:8px"></div>
</div>
"""
    return _page_shell(f"اشتراک {user.get('name') or ''}", body, data)
