import type { SigilBatchEntry, SigilQueueEntry } from '@/modules/core/sigil/types';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';

const DB_NAME = 'sigil';
const STORE_NAME = 'events';
const DB_VERSION = 1;
const FLUSH_INTERVAL_MS = 30_000;
const FLUSH_THRESHOLD = 10;

const SIGIL_DEBUG = !!import.meta.env.VITE_SIGIL_DEBUG;
const HOST_URL = 'https://sigil.rotki.com';
const BATCH_ENDPOINT = `${HOST_URL}/api/batch`;
const WEBSITE_ID = SIGIL_DEBUG
  ? (import.meta.env.VITE_SIGIL_DEBUG_WEBSITE_ID ?? '')
  : (import.meta.env.VITE_SIGIL_WEBSITE_ID ?? '');

const MAX_FLUSH_RETRIES = 3;

let db: IDBDatabase | undefined;
let flushTimer: ReturnType<typeof setInterval> | undefined;
let consecutiveFailures = 0;
let flushing = false;

async function openDb(): Promise<IDBDatabase> {
  if (db)
    return Promise.resolve(db);

  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (): void => {
      request.result.createObjectStore(STORE_NAME, {
        keyPath: 'id',
        autoIncrement: true,
      });
    };

    request.onsuccess = (): void => {
      db = request.result;
      resolve(db);
    };

    request.onerror = (): void => {
      logger.warn('[sigil] failed to open IndexedDB');
      reject(request.error);
    };
  });
}

async function promisifyTransaction(tx: IDBTransaction): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    tx.oncomplete = (): void => resolve();
    tx.onerror = (): void => reject(tx.error);
  });
}

async function enqueue(entry: Omit<SigilQueueEntry, 'id'>): Promise<void> {
  try {
    const database = await openDb();
    const tx = database.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).add(entry);
    await promisifyTransaction(tx);

    const count = await getCount();
    if (count >= FLUSH_THRESHOLD) {
      await flush();
    }
  }
  catch {
    logger.debug('[sigil] failed to enqueue, discarding event');
  }
}

async function getCount(): Promise<number> {
  if (!db)
    return 0;

  return new Promise<number>((resolve) => {
    const tx = db!.transaction(STORE_NAME, 'readonly');
    const request = tx.objectStore(STORE_NAME).count();
    request.onsuccess = (): void => resolve(request.result);
    request.onerror = (): void => resolve(0);
  });
}

async function readAll(): Promise<SigilQueueEntry[]> {
  if (!db)
    return [];

  return new Promise<SigilQueueEntry[]>((resolve) => {
    const tx = db!.transaction(STORE_NAME, 'readonly');
    const request = tx.objectStore(STORE_NAME).getAll();
    request.onsuccess = (): void => resolve(request.result);
    request.onerror = (): void => resolve([]);
  });
}

async function clearAll(): Promise<void> {
  if (!db)
    return;

  return new Promise<void>((resolve) => {
    const tx = db!.transaction(STORE_NAME, 'readwrite');
    tx.objectStore(STORE_NAME).clear();
    tx.oncomplete = (): void => resolve();
    tx.onerror = (): void => resolve();
  });
}

function toBatchEntry(entry: SigilQueueEntry): SigilBatchEntry {
  const payload: SigilBatchEntry['payload'] = {
    website: WEBSITE_ID,
    hostname: '',
    screen: `${window.screen.width}x${window.screen.height}`,
    language: navigator.language,
    title: '',
    url: entry.url,
    referrer: '',
  };

  if (entry.name)
    payload.name = entry.name;

  if (entry.data)
    payload.data = entry.data;

  return { type: 'event', payload };
}

async function flush(): Promise<void> {
  if (!WEBSITE_ID || flushing)
    return;

  flushing = true;
  try {
    const entries = await readAll();
    if (entries.length === 0)
      return;

    const batch = entries.map(toBatchEntry);

    if (SIGIL_DEBUG)
      logger.debug('[sigil] flushing batch', batch);

    try {
      const response = await fetch(BATCH_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batch),
        keepalive: true,
      });

      if (response.ok) {
        consecutiveFailures = 0;
        await clearAll();
        logger.debug(`[sigil] flushed ${entries.length} events`);
      }
      else {
        consecutiveFailures++;
        logger.warn(`[sigil] batch flush failed: ${response.status} (attempt ${consecutiveFailures}/${MAX_FLUSH_RETRIES})`);
      }
    }
    catch {
      consecutiveFailures++;
      logger.debug(`[sigil] batch flush network error (attempt ${consecutiveFailures}/${MAX_FLUSH_RETRIES})`);
    }

    if (consecutiveFailures >= MAX_FLUSH_RETRIES) {
      logger.warn(`[sigil] ${MAX_FLUSH_RETRIES} consecutive flush failures, dropping queued events`);
      consecutiveFailures = 0;
      await clearAll();
    }
  }
  finally {
    flushing = false;
  }
}

function handleVisibilityChange(): void {
  if (document.visibilityState === 'hidden') {
    startPromise(flush());
  }
}

function startQueue(): void {
  // Guard against double-invocation leaking the previous interval.
  if (flushTimer)
    clearInterval(flushTimer);

  flushTimer = setInterval(() => {
    startPromise(flush());
  }, FLUSH_INTERVAL_MS);

  document.addEventListener('visibilitychange', handleVisibilityChange);

  // Flush any leftover events from a previous session
  startPromise(flush());
}

function stopQueue(): void {
  if (flushTimer) {
    clearInterval(flushTimer);
    flushTimer = undefined;
  }

  document.removeEventListener('visibilitychange', handleVisibilityChange);
  consecutiveFailures = 0;

  // Clear any remaining events — user opted out or logged out
  startPromise(clearAll());
}

export { enqueue, flush, startQueue, stopQueue, WEBSITE_ID };
