import { beforeEach, describe, expect, it, vi } from 'vitest';

const INSTANCE_KEY = 'rotki.sigil.instance_id';

describe('use-sigil-identity', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  describe('instance id', () => {
    it('should mint and persist one on first use', async () => {
      const { getInstanceId } = await import('@/modules/core/sigil/use-sigil-identity');

      const id = getInstanceId();

      expect(id).toEqual(expect.any(String));
      expect(id).not.toBe('');
      expect(localStorage.getItem(INSTANCE_KEY)).toBe(id);
    });

    it('should return the same value on a second call', async () => {
      const { getInstanceId } = await import('@/modules/core/sigil/use-sigil-identity');

      expect(getInstanceId()).toBe(getInstanceId());
    });

    it('should reuse a stored value rather than minting a new one', async () => {
      localStorage.setItem(INSTANCE_KEY, 'stored-instance');
      const { getInstanceId } = await import('@/modules/core/sigil/use-sigil-identity');

      expect(getInstanceId()).toBe('stored-instance');
    });

    it('should keep one value for the session when storage throws', async () => {
      const { getInstanceId } = await import('@/modules/core/sigil/use-sigil-identity');
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('storage unavailable');
      });

      const first = getInstanceId();

      expect(first).not.toBe('');
      expect(getInstanceId()).toBe(first);
    });
  });

  describe('client id cache', () => {
    it('should return nothing for an account it has never seen', async () => {
      const { readCachedClientId } = await import('@/modules/core/sigil/use-sigil-identity');

      expect(readCachedClientId('bob')).toBeUndefined();
    });

    it('should return what was cached for that account', async () => {
      const { cacheClientId, readCachedClientId } = await import('@/modules/core/sigil/use-sigil-identity');

      cacheClientId('bob', 'bob-id');

      expect(readCachedClientId('bob')).toBe('bob-id');
    });

    it('should keep accounts apart', async () => {
      const { cacheClientId, readCachedClientId } = await import('@/modules/core/sigil/use-sigil-identity');

      cacheClientId('bob', 'bob-id');
      cacheClientId('alice', 'alice-id');

      expect(readCachedClientId('bob')).toBe('bob-id');
      expect(readCachedClientId('alice')).toBe('alice-id');
    });

    it('should overwrite an earlier value for the same account', async () => {
      const { cacheClientId, readCachedClientId } = await import('@/modules/core/sigil/use-sigil-identity');
      cacheClientId('bob', 'old-id');

      cacheClientId('bob', 'new-id');

      expect(readCachedClientId('bob')).toBe('new-id');
    });

    it('should ignore a corrupt store rather than throw', async () => {
      localStorage.setItem('rotki.sigil.client_ids', '{not json');
      const { readCachedClientId } = await import('@/modules/core/sigil/use-sigil-identity');

      expect(readCachedClientId('bob')).toBeUndefined();
    });

    it('should ignore entries of the wrong shape', async () => {
      localStorage.setItem('rotki.sigil.client_ids', JSON.stringify({ bob: { nested: true } }));
      const { readCachedClientId } = await import('@/modules/core/sigil/use-sigil-identity');

      expect(readCachedClientId('bob')).toBeUndefined();
    });

    it('should do nothing without a username, so entries cannot collide under an empty key', async () => {
      const { cacheClientId, readCachedClientId } = await import('@/modules/core/sigil/use-sigil-identity');

      cacheClientId('', 'orphan-id');

      expect(localStorage.getItem('rotki.sigil.client_ids')).toBeNull();
      expect(readCachedClientId('')).toBeUndefined();
    });
  });

  describe('createClientId', () => {
    it('should return a distinct value each call', async () => {
      const { createClientId } = await import('@/modules/core/sigil/use-sigil-identity');

      expect(createClientId()).not.toBe(createClientId());
    });

    /**
     * `crypto.randomUUID` is only defined in a secure context, so it is missing exactly where this
     * matters most: a Docker instance reached over plain http on a LAN IP.
     */
    it('should still mint without crypto.randomUUID', async () => {
      const { createClientId } = await import('@/modules/core/sigil/use-sigil-identity');
      vi.stubGlobal('crypto', { getRandomValues: globalThis.crypto.getRandomValues.bind(globalThis.crypto) });

      const id = createClientId();

      expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
      expect(createClientId()).not.toBe(id);
    });

    it('should still mint with no crypto at all', async () => {
      const { createClientId } = await import('@/modules/core/sigil/use-sigil-identity');
      vi.stubGlobal('crypto', undefined);

      const id = createClientId();

      expect(id).not.toBe('');
      expect(createClientId()).not.toBe(id);
    });
  });

  describe('resetSigilIdentity', () => {
    it('should drop everything stored, so the next call starts over', async () => {
      const { cacheClientId, getInstanceId, readCachedClientId, resetSigilIdentity } = await import('@/modules/core/sigil/use-sigil-identity');
      const first = getInstanceId();
      cacheClientId('bob', 'bob-id');

      resetSigilIdentity();

      expect(localStorage.getItem(INSTANCE_KEY)).toBeNull();
      expect(readCachedClientId('bob')).toBeUndefined();
      expect(getInstanceId()).not.toBe(first);
    });
  });
});
