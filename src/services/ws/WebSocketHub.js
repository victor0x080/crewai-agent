/**
 * WebSocketHub
 * Serves WebSocket clients at /ws/rep/:repId and broadcasts:
 *  - transcript.turn.received (live transcript)
 *  - coaching.message.created (from Redis stream: stream:coaching:messages)
 *
 * Expects:
 *  - An HTTP server (noServer setup)
 *  - An EventBus instance for in-process events
 *  - Redis (ioredis) to consume coaching messages stream
 */

import { WebSocketServer } from 'ws';
import Redis from 'ioredis';
import { parse } from 'url';

const COACHING_STREAM = 'stream:coaching:messages';

export class WebSocketHub {
  constructor(server, eventBus, redisUrl) {
    this.server = server;
    this.eventBus = eventBus;
    this.redis = new Redis(redisUrl || process.env.REDIS_URL || 'redis://localhost:6379');
    this.wss = new WebSocketServer({ noServer: true });
    this.repClients = new Map(); // repId -> Set<WebSocket>
    this.running = false;

    this._wireUpgrade();
    this._wireEventBus();
  }

  start() {
    if (this.running) return;
    this.running = true;
    // eslint-disable-next-line no-console
    console.log('[WebSocketHub] 🌐 WebSocket hub started at /ws/rep/:repId');
    this._consumeCoachingStream().catch((e) => {
      // eslint-disable-next-line no-console
      console.error('[WebSocketHub] Coaching stream error:', e);
      this.running = false;
    });
  }

  stop() {
    this.running = false;
    try {
      this.wss.close();
    } catch (_) {}
    try {
      this.redis.quit();
    } catch (_) {}
  }

  _wireUpgrade() {
    this.server.on('upgrade', (req, socket, head) => {
      try {
        const { pathname } = parse(req.url, true);
        // eslint-disable-next-line no-console
        console.log(`[WebSocketHub] 🔄 Upgrade request: ${pathname}`);
        // Expect /ws/rep/:repId
        const parts = pathname.split('/').filter(Boolean);
        if (parts.length === 3 && parts[0] === 'ws' && parts[1] === 'rep' && parts[2]) {
          const repId = parts[2];
          // eslint-disable-next-line no-console
          console.log(`[WebSocketHub] ✅ Accepting upgrade for rep: ${repId}`);
          this.wss.handleUpgrade(req, socket, head, (ws) => {
            this._onConnection(ws, repId);
          });
        } else {
          // eslint-disable-next-line no-console
          console.log(`[WebSocketHub] ❌ Rejecting upgrade - invalid path: ${pathname}`);
          socket.destroy();
        }
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('[WebSocketHub] ❌ Upgrade error:', e);
        socket.destroy();
      }
    });
  }

  _onConnection(ws, repId) {
    let set = this.repClients.get(repId);
    if (!set) {
      set = new Set();
      this.repClients.set(repId, set);
    }
    set.add(ws);

    // eslint-disable-next-line no-console
    console.log(`[WebSocketHub] ✅ Client connected for rep "${repId}" (total: ${set.size})`);

    ws.on('close', () => {
      set.delete(ws);
      if (set.size === 0) {
        this.repClients.delete(repId);
      }
      // eslint-disable-next-line no-console
      console.log(`[WebSocketHub] ❎ Client disconnected for rep "${repId}"`);
    });

    ws.on('error', () => {
      try { ws.close(); } catch (_) {}
    });

    // Greet
    try {
      ws.send(JSON.stringify({ event: 'system', data: { message: 'Connected to coaching system' } }));
    } catch (_) {}
  }

  _wireEventBus() {
    if (!this.eventBus) return;
    // Broadcast transcript turns as they are received
    this.eventBus.on('transcript.turn.received', async (turn) => {
      let repId = turn?.rep_id || turn?.repId;
      if (!repId) {
        // Try to resolve via call metadata
        const callId = turn?.call_id || turn?.callId;
        if (callId) {
          try {
            const metaStr = await this.redis.get(`call:${callId}`);
            if (metaStr) {
              const meta = JSON.parse(metaStr);
              repId = meta.rep_id;
            }
          } catch (_) {}
        }
      }
      if (!repId) return;
      this._broadcast(repId, { event: 'transcript_turn', data: turn });
    });

    // Broadcast issue detection events
    this.eventBus.on('issue.detected', (issue) => {
      const repId = issue?.rep_id;
      if (!repId) {
        console.warn('[WebSocketHub] Issue detected but no rep_id found:', issue);
        return;
      }
      this._broadcast(repId, { event: 'issue_detected', data: issue });
    });
  }

  async _consumeCoachingStream() {
    let lastId = '$';
    while (this.running) {
      try {
        const res = await this.redis.xread('BLOCK', 2000, 'STREAMS', COACHING_STREAM, lastId);
        if (!res) continue;

        for (const [, entries] of res) {
          for (const [id, fields] of entries) {
            lastId = id;
            const obj = {};
            for (let i = 0; i < fields.length; i += 2) {
              obj[fields[i]] = fields[i + 1];
            }
            // Data payload is JSON string
            let data = {};
            try { data = JSON.parse(obj.data || '{}'); } catch (_) {}
            const repId = data.rep_id || (obj.subject?.startsWith('rep_') ? obj.subject.slice(4) : null);
            if (!repId) continue;
            this._broadcast(repId, { event: 'coaching_message', data });
          }
        }
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('[WebSocketHub] Stream consume error:', e.message || e);
        await new Promise((r) => setTimeout(r, 500));
      }
    }
  }

  _broadcast(repId, payload) {
    const set = this.repClients.get(repId);
    if (!set || set.size === 0) return;
    const msg = JSON.stringify(payload);
    for (const ws of set) {
      try { ws.send(msg); } catch (_) {}
    }
  }
}

export default WebSocketHub;


