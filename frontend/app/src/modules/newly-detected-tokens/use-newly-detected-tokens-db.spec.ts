import { wait } from '@shared/utils';
import { flushPromises } from '@vue/test-utils';
import { get, set } from '@vueuse/core';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useDatabase } from '@/modules/data/use-database';
import { useNewlyDetectedTokensDb } from '@/modules/newly-detected-tokens/use-newly-detected-tokens-db';
import { useMainStore } from '@/store/main';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { NewDetectedTokenKind, type NewDetectedTokensRequestPayload } from './types';

const TEST_USER = 'test-user-tokens';
const TEST_DATA_DIR = '/test/data/dir';

describe('useNewlyDetectedTokensDb', () => {
  beforeAll(() => {
    // Set a global pinia for tests, it's needed otherwise the shared composable
    // will access the wrong store. and make tests to fail.
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(async () => {
    vi.resetModules();

    // Wait for database to become ready
    const { isReady, db } = useDatabase();

    const user = useLoggedUserIdentifier();
    set(user, TEST_USER);

    // Set up data directory
    const mainStore = useMainStore();
    const { dataDirectory } = storeToRefs(mainStore);
    set(dataDirectory, TEST_DATA_DIR);

    await until(isReady).toBe(true);

    if (!get(isReady)) {
      throw new Error('Database did not become ready in time');
    }

    await db().newlyDetectedTokens.clear();
  });

  afterEach(async () => {
    const user = useLoggedUserIdentifier();
    const { isReady } = useDatabase();
    set(user, undefined);
    await flushPromises();
    await until(isReady).toBe(false);
    vi.clearAllMocks();
  });

  describe('addToken', () => {
    it('should add a new token and return true', async () => {
      const { addToken, count } = useNewlyDetectedTokensDb();

      const result = await addToken({
        tokenIdentifier: 'eip155:1/erc20:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
      });

      expect(result).toBe(true);
      expect(await count()).toBe(1);
    });

    it('should update existing token and return false', async () => {
      const { addToken, count } = useNewlyDetectedTokensDb();
      const { db } = useDatabase();

      // Add initial token
      await addToken({
        tokenIdentifier: 'eip155:1/erc20:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
        seenDescription: 'First description',
      });

      // Add same token again with different description
      const result = await addToken({
        tokenIdentifier: 'eip155:1/erc20:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
        seenDescription: 'Updated description',
      });

      expect(result).toBe(false);
      expect(await count()).toBe(1);

      // Verify description was updated
      const token = await db().newlyDetectedTokens.where('tokenIdentifier').equals('eip155:1/erc20:0x1234').first();
      expect(token?.seenDescription).toBe('Updated description');
    });

    it('should preserve original detectedAt when updating', async () => {
      const { addToken } = useNewlyDetectedTokensDb();
      const { db } = useDatabase();

      // Add initial token
      await addToken({
        tokenIdentifier: 'eip155:1/erc20:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
      });

      const originalToken = await db().newlyDetectedTokens.where('tokenIdentifier').equals('eip155:1/erc20:0x1234').first();
      const originalDetectedAt = originalToken?.detectedAt;

      // Wait a bit and update
      await wait(10);

      await addToken({
        tokenIdentifier: 'eip155:1/erc20:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
        seenDescription: 'Updated',
      });

      const updatedToken = await db().newlyDetectedTokens.where('tokenIdentifier').equals('eip155:1/erc20:0x1234').first();
      expect(updatedToken?.detectedAt).toBe(originalDetectedAt);
    });

    it('should return false when database is not ready', async () => {
      // Clear the user to make database not ready
      const user = useLoggedUserIdentifier();
      const { isReady } = useDatabase();

      set(user, undefined);

      await until(isReady).toBe(false);

      const { addToken } = useNewlyDetectedTokensDb();

      const result = await addToken({
        tokenIdentifier: 'eip155:1/erc20:0x1234',
        tokenKind: NewDetectedTokenKind.EVM,
      });

      expect(result).toBe(false);
    });
  });

  describe('removeTokens', () => {
    it('should remove tokens by identifiers', async () => {
      const { db } = useDatabase();
      const { addToken, removeTokens, count } = useNewlyDetectedTokensDb();

      await addToken({ tokenIdentifier: 'token-1', tokenKind: NewDetectedTokenKind.EVM });
      await addToken({ tokenIdentifier: 'token-2', tokenKind: NewDetectedTokenKind.EVM });
      await addToken({ tokenIdentifier: 'token-3', tokenKind: NewDetectedTokenKind.EVM });

      expect(await count()).toBe(3);

      await removeTokens(['token-1', 'token-3']);

      expect(await count()).toBe(1);
      const remaining = await db().newlyDetectedTokens.toArray();
      expect(remaining[0].tokenIdentifier).toBe('token-2');
    });

    it('should handle empty identifiers array', async () => {
      const { addToken, removeTokens, count } = useNewlyDetectedTokensDb();

      await addToken({ tokenIdentifier: 'token-1', tokenKind: NewDetectedTokenKind.EVM });
      await removeTokens([]);

      expect(await count()).toBe(1);
    });
  });

  describe('clearAll', () => {
    it('should remove all tokens', async () => {
      const { addToken, clearAll, count } = useNewlyDetectedTokensDb();

      await addToken({ tokenIdentifier: 'token-1', tokenKind: NewDetectedTokenKind.EVM });
      await addToken({ tokenIdentifier: 'token-2', tokenKind: NewDetectedTokenKind.EVM });

      expect(await count()).toBe(2);

      await clearAll();

      expect(await count()).toBe(0);
    });
  });

  describe('count', () => {
    it('should return correct count', async () => {
      const { addToken, count } = useNewlyDetectedTokensDb();

      expect(await count()).toBe(0);

      await addToken({ tokenIdentifier: 'token-1', tokenKind: NewDetectedTokenKind.EVM });
      expect(await count()).toBe(1);

      await addToken({ tokenIdentifier: 'token-2', tokenKind: NewDetectedTokenKind.EVM });
      expect(await count()).toBe(2);
    });

    it('should return 0 when database is not ready', async () => {
      // Clear the user to make database not ready
      const { isReady } = useDatabase();
      const user = useLoggedUserIdentifier();
      set(user, undefined);

      await until(isReady).toBe(false);

      const { count } = useNewlyDetectedTokensDb();

      expect(await count()).toBe(0);
    });
  });

  describe('getAllIdentifiers', () => {
    it('should return all token identifiers', async () => {
      const { addToken, getAllIdentifiers } = useNewlyDetectedTokensDb();

      await addToken({ tokenIdentifier: 'token-1', tokenKind: NewDetectedTokenKind.EVM });
      await addToken({ tokenIdentifier: 'token-2', tokenKind: NewDetectedTokenKind.SOLANA });

      const identifiers = await getAllIdentifiers();

      expect(identifiers.sort()).toEqual(['token-1', 'token-2']);
    });

    it('should filter by tokenKind when provided', async () => {
      const { addToken, getAllIdentifiers } = useNewlyDetectedTokensDb();

      await addToken({ tokenIdentifier: 'evm-1', tokenKind: NewDetectedTokenKind.EVM });
      await addToken({ tokenIdentifier: 'solana-1', tokenKind: NewDetectedTokenKind.SOLANA });
      await addToken({ tokenIdentifier: 'evm-2', tokenKind: NewDetectedTokenKind.EVM });

      const evmIdentifiers = await getAllIdentifiers(NewDetectedTokenKind.EVM);
      const solanaIdentifiers = await getAllIdentifiers(NewDetectedTokenKind.SOLANA);

      expect(evmIdentifiers.sort()).toEqual(['evm-1', 'evm-2']);
      expect(solanaIdentifiers).toEqual(['solana-1']);
    });

    it('should return empty array when database is not ready', async () => {
      // Clear the user to make database not ready
      const { isReady } = useDatabase();
      const user = useLoggedUserIdentifier();
      set(user, undefined);

      await until(isReady).toBe(false);
      const { getAllIdentifiers } = useNewlyDetectedTokensDb();

      const identifiers = await getAllIdentifiers();

      expect(identifiers).toEqual([]);
    });
  });

  describe('getData', () => {
    it('should return paginated data', async () => {
      const { getData } = useNewlyDetectedTokensDb();
      const { db } = useDatabase();
      const now = Date.now();

      // Add tokens with different timestamps directly to DB
      for (let i = 0; i < 5; i++) {
        await db().newlyDetectedTokens.add({
          tokenIdentifier: `token-${i}`,
          tokenKind: NewDetectedTokenKind.EVM,
          detectedAt: now - i * 1000,
        });
      }

      const payload: NewDetectedTokensRequestPayload = {
        limit: 2,
        offset: 0,
        orderByAttributes: ['detectedAt'],
        ascending: [false],
      };

      const result = await getData(payload);

      expect(result.total).toBe(5);
      expect(result.found).toBe(5);
      expect(result.data).toHaveLength(2);
      expect(result.data[0].tokenIdentifier).toBe('token-0'); // newest first
    });

    it('should filter by tokenKind', async () => {
      const { addToken, getData } = useNewlyDetectedTokensDb();

      await addToken({ tokenIdentifier: 'evm-1', tokenKind: NewDetectedTokenKind.EVM });
      await addToken({ tokenIdentifier: 'solana-1', tokenKind: NewDetectedTokenKind.SOLANA });
      await addToken({ tokenIdentifier: 'evm-2', tokenKind: NewDetectedTokenKind.EVM });

      const payload: NewDetectedTokensRequestPayload = {
        limit: 10,
        offset: 0,
        tokenKind: NewDetectedTokenKind.EVM,
      };

      const result = await getData(payload);

      expect(result.total).toBe(3);
      expect(result.found).toBe(2);
      expect(result.data).toHaveLength(2);
      expect(result.data.every(t => t.tokenKind === NewDetectedTokenKind.EVM)).toBe(true);
    });

    it('should return empty result when database is not ready', async () => {
      // Clear the user to make database not ready
      const { isReady } = useDatabase();
      const user = useLoggedUserIdentifier();
      set(user, undefined);

      await until(isReady).toBe(false);

      const { getData } = useNewlyDetectedTokensDb();

      const payload: NewDetectedTokensRequestPayload = { limit: 10, offset: 0 };
      const result = await getData(payload);

      expect(result).toEqual({ data: [], found: 0, limit: -1, total: 0 });
    });
  });

  describe('prune', () => {
    const SECONDS_PER_DAY = 86400;

    beforeEach(() => {
      const settingsStore = useFrontendSettingsStore();
      settingsStore.update({
        newlyDetectedTokensMaxCount: 10000,
        newlyDetectedTokensTtlDays: 365,
      });
    });

    it('should prune expired tokens based on TTL setting', async () => {
      const ttlDays = 30;

      // Set TTL in frontend settings store
      const settingsStore = useFrontendSettingsStore();
      settingsStore.update({ newlyDetectedTokensTtlDays: ttlDays });

      const { db } = useDatabase();
      const { prune, count } = useNewlyDetectedTokensDb();

      const now = Date.now();
      const cutoffTime = now - (ttlDays * SECONDS_PER_DAY * 1000);

      // Add expired and valid tokens directly to DB
      await db().newlyDetectedTokens.bulkAdd([
        { tokenIdentifier: 'expired-1', tokenKind: NewDetectedTokenKind.EVM, detectedAt: cutoffTime - 1000 },
        { tokenIdentifier: 'expired-2', tokenKind: NewDetectedTokenKind.EVM, detectedAt: cutoffTime - 2000 },
        { tokenIdentifier: 'valid-1', tokenKind: NewDetectedTokenKind.EVM, detectedAt: cutoffTime + 1000 },
        { tokenIdentifier: 'valid-2', tokenKind: NewDetectedTokenKind.EVM, detectedAt: now },
      ]);

      expect(await count()).toBe(4);

      await prune();

      expect(await count()).toBe(2);
      const remaining = await db().newlyDetectedTokens.toArray();
      expect(remaining.map(t => t.tokenIdentifier).sort()).toEqual(['valid-1', 'valid-2']);
    });

    it('should prune excess tokens based on max count setting', async () => {
      // Set max count in frontend settings store
      const settingsStore = useFrontendSettingsStore();
      settingsStore.update({ newlyDetectedTokensMaxCount: 3 });

      const { db } = useDatabase();
      const { prune, count } = useNewlyDetectedTokensDb();

      const now = Date.now();

      // Add more tokens than max count
      await db().newlyDetectedTokens.bulkAdd([
        { tokenIdentifier: 'oldest', tokenKind: NewDetectedTokenKind.EVM, detectedAt: now - 5000 },
        { tokenIdentifier: 'old', tokenKind: NewDetectedTokenKind.EVM, detectedAt: now - 4000 },
        { tokenIdentifier: 'middle', tokenKind: NewDetectedTokenKind.EVM, detectedAt: now - 3000 },
        { tokenIdentifier: 'recent', tokenKind: NewDetectedTokenKind.EVM, detectedAt: now - 2000 },
        { tokenIdentifier: 'newest', tokenKind: NewDetectedTokenKind.EVM, detectedAt: now - 1000 },
      ]);

      expect(await count()).toBe(5);
      await prune();

      expect(await count()).toBe(3);
      const remaining = await db().newlyDetectedTokens.toArray();
      expect(remaining.map(t => t.tokenIdentifier).sort()).toEqual(['middle', 'newest', 'recent']);
    });

    it('should handle combined TTL and max count pruning', async () => {
      const ttlDays = 30;

      // Set both TTL and max count
      const settingsStore = useFrontendSettingsStore();
      settingsStore.update({
        newlyDetectedTokensTtlDays: ttlDays,
        newlyDetectedTokensMaxCount: 2,
      });

      const { db } = useDatabase();
      const { prune, count } = useNewlyDetectedTokensDb();

      const now = Date.now();
      const cutoffTime = now - (ttlDays * SECONDS_PER_DAY * 1000);

      await db().newlyDetectedTokens.bulkAdd([
        { tokenIdentifier: 'expired-1', tokenKind: NewDetectedTokenKind.EVM, detectedAt: cutoffTime - 1000 },
        { tokenIdentifier: 'valid-oldest', tokenKind: NewDetectedTokenKind.EVM, detectedAt: cutoffTime + 1000 },
        { tokenIdentifier: 'valid-middle', tokenKind: NewDetectedTokenKind.EVM, detectedAt: now - 2000 },
        { tokenIdentifier: 'valid-newest', tokenKind: NewDetectedTokenKind.EVM, detectedAt: now - 1000 },
      ]);

      expect(await count()).toBe(4);

      await prune();

      // First prunes expired (1), then prunes excess (1 more to get to max 2)
      expect(await count()).toBe(2);
      const remaining = await db().newlyDetectedTokens.toArray();
      expect(remaining.map(t => t.tokenIdentifier).sort()).toEqual(['valid-middle', 'valid-newest']);
    });

    it('should not fail when no tokens need pruning', async () => {
      // Set high values so no pruning happens
      const settingsStore = useFrontendSettingsStore();

      settingsStore.update({
        newlyDetectedTokensMaxCount: 100,
        newlyDetectedTokensTtlDays: 30,
      });

      const { addToken, prune, count } = useNewlyDetectedTokensDb();

      await addToken({ tokenIdentifier: 'token-1', tokenKind: NewDetectedTokenKind.EVM });
      await addToken({ tokenIdentifier: 'token-2', tokenKind: NewDetectedTokenKind.EVM });

      await prune();

      expect(await count()).toBe(2);
    });

    it('should handle empty database gracefully', async () => {
      const { prune, count } = useNewlyDetectedTokensDb();

      await prune();

      expect(await count()).toBe(0);
    });
  });

  describe('isReady', () => {
    it('should reflect database ready state', async () => {
      const { isReady } = useNewlyDetectedTokensDb();
      const user = useLoggedUserIdentifier();

      expect(get(isReady)).toBe(true);
      // Clear user to make database not ready
      set(user, undefined);

      await until(isReady).toBe(false);
      expect(get(isReady)).toBe(false);
    });
  });
});
