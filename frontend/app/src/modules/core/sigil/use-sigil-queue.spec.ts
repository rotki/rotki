import { IDBFactory } from 'fake-indexeddb';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import 'fake-indexeddb/auto';

/** Opens the queue's database and closes the handle, so a delete after this strands the module. */
async function openSigilDb(): Promise<void> {
  const openReq = indexedDB.open('sigil', 1);
  await new Promise<void>((resolve) => {
    openReq.onupgradeneeded = (): void => {
      openReq.result.createObjectStore('events', { keyPath: 'id', autoIncrement: true });
    };
    openReq.onsuccess = (): void => {
      openReq.result.close();
      resolve();
    };
  });
}

describe('use-sigil-queue', () => {
  beforeEach(() => {
    // eslint-disable-next-line no-global-assign
    indexedDB = new IDBFactory();
    vi.resetModules();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('startQueue and stopQueue', () => {
    it('should set up periodic flush timer on start', async () => {
      vi.useFakeTimers();
      const { startQueue, stopQueue } = await import('@/modules/core/sigil/use-sigil-queue');
      startQueue();
      expect(vi.getTimerCount()).toBeGreaterThan(0);
      stopQueue();
    });

    it('should clear timer and listener on stop', async () => {
      vi.useFakeTimers();
      const { startQueue, stopQueue } = await import('@/modules/core/sigil/use-sigil-queue');
      startQueue();
      stopQueue();
      expect(vi.getTimerCount()).toBe(0);
    });

    it('should flush leftover events from previous session on start', async () => {
      const fetchSpy = vi.fn().mockResolvedValue({ ok: true });
      vi.stubGlobal('fetch', fetchSpy);

      const { enqueue, startQueue, stopQueue } = await import('@/modules/core/sigil/use-sigil-queue');

      await enqueue({ url: '/leftover', timestamp: Date.now() });

      startQueue();
      // The initial flush is fire-and-forget: poll for it instead of sleeping
      await vi.waitUntil(() => fetchSpy.mock.calls.length > 0, { interval: 1, timeout: 2000 });

      expect(fetchSpy).toHaveBeenCalled();

      stopQueue();
      vi.unstubAllGlobals();
    });
  });

  describe('enqueue', () => {
    it('should store entries in IndexedDB without throwing', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      await enqueue({ url: '/page1', timestamp: 1000 });
      await enqueue({ url: '/page2', timestamp: 2000 });
      // No error means entries were stored successfully
    });

    it('should store entries with custom event data', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      await enqueue({
        url: '/dashboard',
        name: 'session_config',
        data: { premium: true, appVersion: '1.42.0' },
        timestamp: 1000,
      });
    });

    it('should discard an event, rather than throw, when the database is gone', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');

      await openSigilDb();
      indexedDB.deleteDatabase('sigil');

      await expect(enqueue({ url: '/test', timestamp: Date.now() })).resolves.not.toThrow();
    });
  });

  describe('identify', () => {
    interface FlushedEntry { type: string; payload: { id?: string; name?: string; data?: Record<string, unknown> } }

    async function flushed(): Promise<FlushedEntry[]> {
      const fetchSpy = vi.fn().mockResolvedValue({ ok: true });
      vi.stubGlobal('fetch', fetchSpy);

      const { flush } = await import('@/modules/core/sigil/use-sigil-queue');
      await flush();

      const [, init] = fetchSpy.mock.calls[0];
      return JSON.parse(init.body);
    }

    it('should send an identify entry with the value as the distinct id', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      await enqueue({ kind: 'identify', clientId: 'client-1', data: { instance_id: 'instance-1' }, url: '/page', timestamp: 1000 });

      const [entry] = await flushed();

      expect(entry.type).toBe('identify');
      expect(entry.payload.id).toBe('client-1');
      expect(entry.payload.data).toEqual({ instance_id: 'instance-1' });
      vi.unstubAllGlobals();
    });

    it('should keep its place ahead of the events queued after it', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      await enqueue({ kind: 'identify', clientId: 'client-1', url: '/page', timestamp: 1000 });
      await enqueue({ url: '/page', timestamp: 2000 });

      const entries = await flushed();

      expect(entries.map(entry => entry.type)).toEqual(['identify', 'event']);
      vi.unstubAllGlobals();
    });

    /**
     * Upstream classifies an entry by its name, so an identify must not carry one, and the
     * identity must not be smuggled into event data: data on a nameless entry is dropped.
     */
    it('should not name the identify entry', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      await enqueue({ kind: 'identify', clientId: 'client-1', url: '/page', timestamp: 1000 });

      const [entry] = await flushed();

      expect(entry.payload).not.toHaveProperty('name');
      vi.unstubAllGlobals();
    });

    it('should leave a page view without data of its own', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      await enqueue({ url: '/page', timestamp: 1000 });

      const [entry] = await flushed();

      expect(entry.type).toBe('event');
      expect(entry.payload).not.toHaveProperty('data');
      vi.unstubAllGlobals();
    });

    it('should leave a custom event data untouched', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      await enqueue({ url: '/page', name: 'session_config', data: { premium: true }, timestamp: 1000 });

      const [entry] = await flushed();

      expect(entry.payload.data).toEqual({ premium: true });
      vi.unstubAllGlobals();
    });
  });

  /**
   * Upstream stores it per row, and derives the session from ip, user agent and a daily salt, so
   * one session covers every account used on that machine that day. Stamping only the identify
   * would leave the events unattributed and the account switch invisible.
   */
  describe('per-entry distinct id', () => {
    interface FlushedEntry { payload: { id?: string } }

    async function flushed(): Promise<FlushedEntry[]> {
      const fetchSpy = vi.fn().mockResolvedValue({ ok: true });
      vi.stubGlobal('fetch', fetchSpy);

      const { flush } = await import('@/modules/core/sigil/use-sigil-queue');
      await flush();

      const [, init] = fetchSpy.mock.calls[0];
      return JSON.parse(init.body);
    }

    it('should stamp a page view', async () => {
      const { setCurrentClientId } = await import('@/modules/core/sigil/use-sigil-identity');
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      setCurrentClientId('client-1');
      await enqueue({ url: '/page', timestamp: 1000 });

      const [entry] = await flushed();

      expect(entry.payload.id).toBe('client-1');
      vi.unstubAllGlobals();
    });

    it('should stamp a custom event', async () => {
      const { setCurrentClientId } = await import('@/modules/core/sigil/use-sigil-identity');
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      setCurrentClientId('client-1');
      await enqueue({ url: '/page', name: 'session_config', timestamp: 1000 });

      const [entry] = await flushed();

      expect(entry.payload.id).toBe('client-1');
      vi.unstubAllGlobals();
    });

    it('should stamp nothing once cleared, so nothing is attributed to the account that left', async () => {
      const { clearCurrentClientId, setCurrentClientId } = await import('@/modules/core/sigil/use-sigil-identity');
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      setCurrentClientId('client-1');
      clearCurrentClientId();
      await enqueue({ url: '/page', timestamp: 1000 });

      const [entry] = await flushed();

      expect(entry.payload.id).toBeUndefined();
      vi.unstubAllGlobals();
    });

    it('should use the value current at flush, so a switch does not relabel the queue wrongly', async () => {
      const { setCurrentClientId } = await import('@/modules/core/sigil/use-sigil-identity');
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');
      setCurrentClientId('client-1');
      await enqueue({ url: '/page', timestamp: 1000 });
      setCurrentClientId('client-2');

      const [entry] = await flushed();

      expect(entry.payload.id).toBe('client-2');
      vi.unstubAllGlobals();
    });
  });

  describe('flush', () => {
    it('should not call fetch when queue is empty', async () => {
      const fetchSpy = vi.fn();
      vi.stubGlobal('fetch', fetchSpy);

      const { flush } = await import('@/modules/core/sigil/use-sigil-queue');
      await flush();

      expect(fetchSpy).not.toHaveBeenCalled();
      vi.unstubAllGlobals();
    });
  });

  describe('stopQueue clears DB', () => {
    it('should clear IndexedDB on stop for opt-out compliance', async () => {
      const { enqueue, stopQueue } = await import('@/modules/core/sigil/use-sigil-queue');

      // Verify the DB was cleared by opening it and counting the records
      async function countEvents(): Promise<number> {
        const db = await new Promise<IDBDatabase>((resolve) => {
          const req = indexedDB.open('sigil', 1);
          req.onupgradeneeded = (): void => {
            req.result.createObjectStore('events', { keyPath: 'id', autoIncrement: true });
          };
          req.onsuccess = (): void => resolve(req.result);
        });

        const count = await new Promise<number>((resolve) => {
          const tx = db.transaction('events', 'readonly');
          const req = tx.objectStore('events').count();
          req.onsuccess = (): void => resolve(req.result);
        });

        db.close();
        return count;
      }

      await enqueue({ url: '/data', timestamp: Date.now() });
      expect(await countEvents()).toBe(1);

      stopQueue();

      // clearAll is fire-and-forget: poll the store until it drains
      await vi.waitUntil(async () => await countEvents() === 0, { interval: 1, timeout: 2000 });

      expect(await countEvents()).toBe(0);
    });
  });

  describe('visibilitychange', () => {
    it('should register and unregister visibilitychange listener', async () => {
      const addSpy = vi.spyOn(document, 'addEventListener');
      const removeSpy = vi.spyOn(document, 'removeEventListener');
      vi.useFakeTimers();

      const { startQueue, stopQueue } = await import('@/modules/core/sigil/use-sigil-queue');

      startQueue();
      expect(addSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function));

      stopQueue();
      expect(removeSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function));

      addSpy.mockRestore();
      removeSpy.mockRestore();
    });
  });
});
