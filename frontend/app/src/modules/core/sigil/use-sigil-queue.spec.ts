import { IDBFactory } from 'fake-indexeddb';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import 'fake-indexeddb/auto';

describe('use-sigil-queue', () => {
  beforeEach(() => {
    // Fresh IndexedDB for each test
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
      // Allow the initial flush to settle
      await new Promise<void>(resolve => setTimeout(resolve, 50));

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

    it('should handle IndexedDB failures gracefully', async () => {
      const { enqueue } = await import('@/modules/core/sigil/use-sigil-queue');

      // Close and break the DB
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

      // Delete the database to invalidate cached reference
      indexedDB.deleteDatabase('sigil');

      // Should not throw, just log and discard
      await enqueue({ url: '/test', timestamp: Date.now() });
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

      await enqueue({ url: '/data', timestamp: Date.now() });
      stopQueue();

      // Allow the fire-and-forget clearAll to settle
      await new Promise<void>(resolve => setTimeout(resolve, 50));

      // Verify DB was cleared by checking we can open and count 0 records
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
      expect(count).toBe(0);
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
