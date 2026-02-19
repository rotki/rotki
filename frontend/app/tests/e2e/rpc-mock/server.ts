import { Buffer } from 'node:buffer';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import path from 'node:path';
import process from 'node:process';
import { createConsola } from 'consola';
import { type BalanceMaps, buildBalanceMaps, tryResolveBalanceCall } from './balance-scanner';

const logger = createConsola({ defaults: { tag: 'mock-rpc' } });

const PORT = Number(process.env.MOCK_RPC_PORT) || 30304;
const MODE = (process.env.MOCK_RPC_MODE || 'replay') as 'record' | 'replay';
const TARGET_URL = process.env.MOCK_RPC_TARGET || '';
const CASSETTE_DIR = path.resolve(import.meta.dirname, '..', 'cassettes', 'rpc');

interface JsonRpcRequest {
  jsonrpc: string;
  method: string;
  params?: unknown[];
  id: number | string;
}

interface CassetteEntry {
  method: string;
  params?: unknown[];
  result?: unknown;
  error?: unknown;
}

type CassetteData = Record<string, CassetteEntry>;

let cassetteName = 'default';
let cassette: CassetteData = {};
let balanceMaps: BalanceMaps | null = null;
let dirty = false;
let saveTimer: ReturnType<typeof setTimeout> | null = null;

function getCassettePath(): string {
  return path.join(CASSETTE_DIR, `${cassetteName}.json`);
}

function hashRequest(method: string, params?: unknown[]): string {
  const key = JSON.stringify({ method, params: params ?? [] });
  return createHash('sha256').update(key).digest('hex').slice(0, 16);
}

function loadCassette(name: string): { data: CassetteData; maps: BalanceMaps | null } {
  const filePath = path.join(CASSETTE_DIR, `${name}.json`);
  if (existsSync(filePath)) {
    const data: CassetteData = JSON.parse(readFileSync(filePath, 'utf-8'));
    const maps = buildBalanceMaps(data);
    return { data, maps };
  }
  return { data: {}, maps: null };
}

function saveCassette(): void {
  if (!existsSync(CASSETTE_DIR)) {
    mkdirSync(CASSETTE_DIR, { recursive: true });
  }
  const filePath = getCassettePath();
  writeFileSync(filePath, JSON.stringify(cassette, null, 2));
  logger.info(`Saved cassette "${cassetteName}" (${Object.keys(cassette).length} entries)`);
}

/**
 * Switches to a different cassette. Saves the current one first if dirty.
 */
function switchCassette(name: string): void {
  if (dirty) {
    saveCassette();
    dirty = false;
  }
  if (saveTimer) {
    clearTimeout(saveTimer);
    saveTimer = null;
  }

  cassetteName = name;
  const loaded = loadCassette(name);
  cassette = loaded.data;
  balanceMaps = loaded.maps;
  logger.info(`Loaded cassette "${name}" (${Object.keys(cassette).length} entries)`);
}

/**
 * Debounced save: writes cassette to disk 2s after the last recorded entry.
 * Ensures data is persisted even if the process is killed without SIGTERM.
 */
function scheduleSave(): void {
  if (saveTimer)
    clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    if (dirty) {
      saveCassette();
      dirty = false;
    }
  }, 2000);
}

async function forwardRequest(rpcRequest: JsonRpcRequest): Promise<{ result?: unknown; error?: unknown }> {
  if (!TARGET_URL) {
    throw new Error('MOCK_RPC_TARGET must be set in record mode');
  }

  const response = await fetch(TARGET_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rpcRequest),
  });

  const text = await response.text();

  if (!response.ok) {
    logger.warn(`Target returned HTTP ${response.status} for ${rpcRequest.method}`);
    return { error: { code: -32603, message: `Target RPC returned HTTP ${response.status}` } };
  }

  try {
    const body = JSON.parse(text) as { result?: unknown; error?: unknown };
    return { result: body.result, error: body.error };
  }
  catch {
    const preview = text.slice(0, 120);
    logger.warn(`Target returned non-JSON for ${rpcRequest.method}: ${preview}`);
    return { error: { code: -32603, message: `Target RPC returned non-JSON response` } };
  }
}

async function handleSingleRequest(req: JsonRpcRequest): Promise<Record<string, unknown>> {
  const hash = hashRequest(req.method, req.params);

  if (MODE === 'replay') {
    // Try semantic balance scanner resolution first (order-independent)
    if (balanceMaps) {
      const resolved = tryResolveBalanceCall(req.method, req.params, balanceMaps);
      if (resolved !== null) {
        logger.debug(`BALANCE HIT: ${req.method}`);
        return {
          jsonrpc: '2.0',
          id: req.id,
          result: resolved,
        };
      }
    }

    const entry = cassette[hash];
    if (entry) {
      logger.debug(`HIT: ${req.method} (hash: ${hash})`);
      return {
        jsonrpc: '2.0',
        id: req.id,
        ...(entry.result !== undefined && { result: entry.result }),
        ...(entry.error !== undefined && { error: entry.error }),
      };
    }

    logger.warn(`MISS: ${req.method} (hash: ${hash}) params: ${JSON.stringify(req.params).slice(0, 200)}`);
    return {
      jsonrpc: '2.0',
      id: req.id,
      error: {
        code: -32603,
        message: `No recorded response for ${req.method} (hash: ${hash})`,
      },
    };
  }

  // Record mode
  logger.info(`RECORD: ${req.method} (hash: ${hash})`);
  const { result, error } = await forwardRequest(req);

  cassette[hash] = {
    method: req.method,
    params: req.params,
    ...(result !== undefined && { result }),
    ...(error !== undefined && { error }),
  };
  dirty = true;
  scheduleSave();

  return {
    jsonrpc: '2.0',
    id: req.id,
    ...(result !== undefined && { result }),
    ...(error !== undefined && { error }),
  };
}

async function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on('data', (chunk: Buffer) => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks).toString()));
    req.on('error', reject);
  });
}

function sendJson(res: ServerResponse, status: number, data: unknown): void {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

const server = createServer((req: IncomingMessage, res: ServerResponse) => {
  handleRequest(req, res).catch((error: unknown) => {
    logger.error('Unhandled error:', error);
    sendJson(res, 500, { jsonrpc: '2.0', id: null, error: { code: -32603, message: 'Server error' } });
  });
});

async function handleRequest(req: IncomingMessage, res: ServerResponse): Promise<void> {
  // Health check endpoint for Playwright
  if (req.url === '/health') {
    sendJson(res, 200, { status: 'ok', mode: MODE, cassette: cassetteName, entries: Object.keys(cassette).length });
    return;
  }

  // Switch cassette: POST /cassette { name: "blockchain-balances" }
  if (req.url === '/cassette' && req.method === 'POST') {
    const body = JSON.parse(await readBody(req)) as { name?: string };
    const name = body.name;
    if (!name) {
      sendJson(res, 400, { error: 'Missing "name" in request body' });
      return;
    }
    switchCassette(name);
    sendJson(res, 200, { cassette: cassetteName, entries: Object.keys(cassette).length });
    return;
  }

  // Save current cassette: POST /save
  if (req.url === '/save' && req.method === 'POST') {
    if (dirty) {
      saveCassette();
      dirty = false;
    }
    sendJson(res, 200, { saved: true, cassette: cassetteName, entries: Object.keys(cassette).length });
    return;
  }

  // Stats endpoint
  if (req.url === '/stats') {
    sendJson(res, 200, {
      mode: MODE,
      cassette: cassetteName,
      entries: Object.keys(cassette).length,
      dirty,
      cassetteFile: getCassettePath(),
    });
    return;
  }

  // Handle JSON-RPC requests
  if (req.method !== 'POST') {
    logger.debug(`Non-POST request: ${req.method} ${req.url}`);
    sendJson(res, 405, { error: 'Method not allowed' });
    return;
  }

  logger.debug(`Incoming POST ${req.url}`);

  try {
    const body = await readBody(req);
    const parsed = JSON.parse(body);

    // Handle batch requests
    if (Array.isArray(parsed)) {
      const results = await Promise.all(
        parsed.map(async (rpcReq: JsonRpcRequest) => handleSingleRequest(rpcReq)),
      );
      sendJson(res, 200, results);
    }
    else {
      const result = await handleSingleRequest(parsed as JsonRpcRequest);
      sendJson(res, 200, result);
    }
  }
  catch (error) {
    logger.error('Request handling error:', error);
    sendJson(res, 500, {
      jsonrpc: '2.0',
      id: null,
      error: { code: -32603, message: `Internal error: ${String(error)}` },
    });
  }
}

// Save cassette on shutdown
function shutdown(): void {
  if (dirty) {
    saveCassette();
  }
  process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

server.listen(PORT, '127.0.0.1', () => {
  logger.info(`Server running on http://127.0.0.1:${PORT}`);
  logger.info(`Mode: ${MODE}`);
  if (MODE === 'record') {
    logger.info(`Target: ${TARGET_URL}`);
  }
});
