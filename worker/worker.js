/**
 * MLP Cloudflare Worker — یک «لوکیشن» روی لبه‌ی Cloudflare
 *
 * این ورکر نقش نود را بازی می‌کند: همان API نودهای Railway را صدا می‌زند
 * (`/api/node/sync` برای گرفتن کاربران و `/api/node/report` برای گزارش مصرف).
 * بنابراین در پنل با فلگ و نام مخصوص خودش ثبت می‌شود و کوتا/انقضا/محدودیت‌ها
 * روی آن هم اعمال می‌شود.
 *
 * متغیرهای محیطی (Workers → Settings → Variables):
 *   PANEL_URL   مثال: https://panel.up.railway.app
 *   NODE_TOKEN  توکن همین لوکیشن از پنل (بخش لوکیشن‌ها)
 *   WS_PATH     پیش‌فرض /ws
 *   PROXYIP     (اختیاری) آدرس پروکسی برای مقاصدی که CF مستقیم نمی‌تواند باز کند
 *   SUB_HOST    (اختیاری) دامنه‌ای که در کانفیگ ساب نوشته می‌شود (پیش‌فرض: دامنه ورکر)
 *   DEAD        (اختیاری) آدرس سایتی که در صورت درخواست غیرمجاز نمایش داده می‌شود
 */

import { connect } from 'cloudflare:sockets';

const VERSION = '1.0.0';
const WS_PATH = (typeof MLP_WS_PATH !== 'undefined' ? MLP_WS_PATH : '') || '/ws';
const SYNC_TTL_MS = 30_000;
const REPORT_INTERVAL_MS = 30_000;

let bundle = { users: new Map(), at: 0, node: null, panel: null };
let usage = new Map();       // uuid -> bytes
let lastReport = 0;
let reporting = false;

function b64ToBytes(b64) {
  const bin = atob(b64.replace(/-/g, '+').replace(/_/g, '/'));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function toUuid(bytes) {
  const h = [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20, 32)}`;
}

async function panelFetch(env, path, body) {
  if (!env.PANEL_URL || !env.NODE_TOKEN) return null;
  const url = `${String(env.PANEL_URL).replace(/\/$/, '')}${path}`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${env.NODE_TOKEN}` },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function ensureBundle(env) {
  const now = Date.now();
  if (bundle.users.size && now - bundle.at < SYNC_TTL_MS) return bundle;
  const data = await panelFetch(env, '/api/node/sync', { status: statusPayload(env) });
  if (data && data.ok) {
    const map = new Map();
    for (const u of data.users || []) map.set(String(u.uuid).toLowerCase(), u);
    bundle = { users: map, at: now, node: data.node || null, panel: data.panel || null };
  }
  return bundle;
}

function statusPayload(env) {
  return {
    version: VERSION,
    node: env.NODE_NAME || 'cloudflare',
    flag: '☁️',
    uptime_seconds: Math.round((Date.now() - STARTED_AT) / 1000),
    connections: 0,
    users_online: 0,
    clients: bundle.users.size,
    total_bytes: [...usage.values()].reduce((a, b) => a + b, 0),
    requests: 0,
    errors: 0,
    runtime: 'cloudflare-worker',
  };
}

const STARTED_AT = Date.now();

function userAllowed(user, uuid) {
  if (!user) return false;
  if (!Number(user.enabled)) return false;
  if (user.expire_at && user.expire_at * 1000 <= Date.now()) return false;
  const limit = Number(user.limit_bytes || 0);
  if (limit && Number(user.used_bytes || 0) + (usage.get(uuid) || 0) >= limit) return false;
  return true;
}

async function flushUsage(env, force) {
  const now = Date.now();
  if (reporting) return;
  if (!force && now - lastReport < REPORT_INTERVAL_MS) return;
  const snapshot = [...usage.entries()].map(([uuid, total]) => ({ uuid, total }));
  if (!snapshot.length) return;
  reporting = true;
  lastReport = now;
  try {
    await panelFetch(env, '/api/node/report', { usage: snapshot, status: statusPayload(env) });
  } finally {
    reporting = false;
  }
}

// ─────────────────────────── پارس هدر VLESS ───────────────────────────
function parseVlessHeader(buffer) {
  if (buffer.byteLength < 24) return null;
  const version = new Uint8Array(buffer.slice(0, 1));
  const uuid = toUuid(new Uint8Array(buffer.slice(1, 17)));
  const addonLen = new Uint8Array(buffer.slice(17, 18))[0];
  const command = new Uint8Array(buffer.slice(18 + addonLen, 19 + addonLen))[0];
  const port = new DataView(buffer.slice(19 + addonLen, 21 + addonLen)).getUint16(0);
  const addrType = new Uint8Array(buffer.slice(21 + addonLen, 22 + addonLen))[0];
  let addrLen = 0;
  let address = '';
  let addrIdx = 22 + addonLen;
  if (addrType === 1) {
    address = new Uint8Array(buffer.slice(addrIdx, addrIdx + 4)).join('.');
    addrLen = 4;
  } else if (addrType === 2) {
    addrLen = new Uint8Array(buffer.slice(addrIdx, addrIdx + 1))[0];
    address = new TextDecoder().decode(buffer.slice(addrIdx + 1, addrIdx + 1 + addrLen));
    addrLen += 1;
  } else if (addrType === 3) {
    const bytes = new Uint8Array(buffer.slice(addrIdx, addrIdx + 16));
    const parts = [];
    for (let i = 0; i < 16; i += 2) parts.push(((bytes[i] << 8) | bytes[i + 1]).toString(16));
    address = parts.join(':');
    addrLen = 16;
  } else {
    return null;
  }
  const headerLen = addrIdx + addrLen;
  return {
    version,
    uuid,
    command,
    port,
    address,
    headerLen,
    payload: buffer.slice(headerLen),
    hasPayload: buffer.byteLength > headerLen,
  };
}

async function makeReadable(ws) {
  let cancelled = false;
  return {
    readable: new ReadableStream({
      start(controller) {
        ws.addEventListener('message', (event) => {
          if (!cancelled) controller.enqueue(event.data);
        });
        ws.addEventListener('close', () => {
          if (!cancelled) {
            controller.close();
            cancelled = true;
          }
        });
        ws.addEventListener('error', () => {
          if (!cancelled) {
            controller.close();
            cancelled = true;
          }
        });
      },
      cancel() {
        cancelled = true;
      },
    }),
    cancel: () => { cancelled = true; },
  };
}

async function handleVless(ws, request, env) {
  await ensureBundle(env);
  const { readable } = await makeReadable(ws);
  const remote = { writable: null, readable: null, socket: null, headerSent: false, uuid: '' };

  const closeAll = () => {
    try { remote.socket?.close?.(); } catch (e) {}
    try { ws.close(); } catch (e) {}
  };

  const pumpRemoteToWs = async () => {
    if (!remote.readable) return;
    const reader = remote.readable.getReader();
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        if (ws.readyState !== WebSocket.OPEN) break;
        if (remote.headerSent) {
          ws.send(value);
        } else {
          const merged = new Uint8Array(value.byteLength + 2);
          merged[0] = 0; merged[1] = 0;
          merged.set(value, 2);
          ws.send(merged);
          remote.headerSent = true;
        }
      }
    } catch (e) {}
    closeAll();
  };

  const reader = readable.getReader();
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      if (!remote.writable) {
        const parsed = parseVlessHeader(value);
        if (!parsed) { closeAll(); break; }
        const user = bundle.users.get(parsed.uuid.toLowerCase());
        if (!userAllowed(user, parsed.uuid.toLowerCase())) {
          closeAll();
          break;
        }
        remote.uuid = parsed.uuid.toLowerCase();
        try {
          const socket = connect(
            { hostname: env.PROXYIP ? env.PROXYIP : parsed.address, port: env.PROXYIP ? 443 : parsed.port },
            { allowHalfOpen: false }
          );
          remote.socket = socket;
          remote.writable = socket.writable;
          remote.readable = socket.readable;
        } catch (e) {
          closeAll();
          break;
        }
        const writer = remote.writable.getWriter();
        if (parsed.hasPayload) {
          await writer.write(parsed.payload);
          usage.set(remote.uuid, (usage.get(remote.uuid) || 0) + parsed.payload.byteLength);
        }
        pumpRemoteToWs();
        remote.writer = writer;
        continue;
      }
      await remote.writer.write(value);
      usage.set(remote.uuid, (usage.get(remote.uuid) || 0) + value.byteLength);
    }
  } catch (e) {
  } finally {
    try { remote.writer?.releaseLock?.(); } catch (e) {}
    closeAll();
    flushUsage(env, false);
  }
}

// ─────────────────────────── ساب و صفحه ───────────────────────────
function subUrl(env, request) {
  const host = env.SUB_HOST || new URL(request.url).host;
  return `https://${host}${WS_PATH}`;
}

function userConfig(env, request, user) {
  const host = env.SUB_HOST || new URL(request.url).host;
  const name = encodeURIComponent(`${user.name || 'user'} | ☁️ Cloudflare`);
  return `vless://${user.uuid}@${host}:443?encryption=none&security=tls&sni=${host}&fp=chrome&type=ws&host=${host}&path=${encodeURIComponent(WS_PATH + '?ed=2560')}#${name}`;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/healthz') {
      return new Response(JSON.stringify(statusPayload(env)), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // ساب را پنل می‌دهد؛ اینجا فقط راهنما برمی‌گردانیم
    if (url.pathname.startsWith('/sub/')) {
      return new Response('از دامنه‌ی پنل استفاده کنید: ' + (env.PANEL_URL || '') + '/sub/<token>', { status: 200 });
    }

    const upgrade = request.headers.get('Upgrade') || '';
    if (upgrade.toLowerCase() === 'websocket') {
      if (url.pathname !== WS_PATH && !url.pathname.startsWith(WS_PATH)) {
        return new Response('not found', { status: 404 });
      }
      const pair = new WebSocketPair();
      const [client, server] = Object.values(pair);
      server.accept();
      ctx.waitUntil(ensureBundle(env));
      ctx.waitUntil(handleVless(server, request, env));
      return new Response(null, { status: 101, webSocket: client });
    }

    return new Response(
      `MLP Cloudflare location\nversion: ${VERSION}\nws path: ${WS_PATH}\npanel: ${env.PANEL_URL || '-'}\n`,
      { headers: { 'Content-Type': 'text/plain; charset=utf-8' } }
    );
  },
};
