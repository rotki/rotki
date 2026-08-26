import type { MissingMapping } from '@/modules/user-data/schemas';
import { get, set } from '@vueuse/core';
import Dexie, { type EntityTable } from 'dexie';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, ref } from 'vue';
import { NewDetectedTokenKind } from '@/modules/assets/detection/types';

// `isReady` is only flipped to true after both migrations settle, so polling it is a
// stronger signal than a fixed sleep - and it returns as soon as the work is done.
const POLL_OPTIONS = { interval: 5, timeout: 2000 } as const;

async function waitUntilReady(isReady: Ref<boolean>): Promise<void> {
  await vi.waitUntil(() => get(isReady), POLL_OPTIONS);
}

async function waitUntilNotReady(isReady: Ref<boolean>): Promise<void> {
  await vi.waitUntil(() => !get(isReady), POLL_OPTIONS);
}

// Old database structure (before migration)
interface OldUserDB extends Dexie {
  missingMappings: EntityTable<MissingMapping, 'id'>;
}

function createOldUserDb(username: string): OldUserDB {
  const db = new Dexie(`${username}.data`);
  db.version(1).stores({
    missingMappings: '++id, [identifier], name, [location], &[identifier+location], details',
  });
  // @ts-expect-error Dexie adds table properties dynamically after version().stores()
  return db;
}

describe('useDatabase', () => {
  const testUsername = 'testuser';
  const testDataDirectory = '/test/data/dir';
  const localStorageKey = `rotki.newly_detected_tokens.${testUsername}`;

  let mockUserIdentifier: ReturnType<typeof ref<string | undefined>>;
  let mockDataDirectory: ReturnType<typeof ref<string | undefined>>;
  let scope: ReturnType<typeof effectScope>;

  beforeEach(async () => {
    scope = effectScope();
    vi.resetModules();

    mockUserIdentifier = ref<string>();
    mockDataDirectory = ref<string>();

    vi.doMock('@/modules/auth/use-logged-user-identifier', () => ({
      useLoggedUserIdentifier: vi.fn(() => mockUserIdentifier),
    }));

    vi.doMock('@/modules/core/common/use-main-store', () => ({
      useMainStore: vi.fn(() => ({
        dataDirectory: mockDataDirectory,
      })),
    }));

    vi.doMock('pinia', async () => {
      const actual = await vi.importActual('pinia');
      return {
        ...actual,
        storeToRefs: vi.fn(() => ({
          dataDirectory: mockDataDirectory,
        })),
      };
    });
  });

  afterEach(async () => {
    // Dispose the shared composable first so it closes its open Dexie connection
    // before we delete the databases; otherwise Dexie force-closes it and warns.
    scope.stop();

    const allDatabases = await Dexie.getDatabaseNames();
    for (const dbName of allDatabases) {
      if (dbName.startsWith('rotki.data.') || dbName.endsWith('.data')) {
        try {
          await Dexie.delete(dbName);
        }
        catch {
          // A leftover database another test still holds open cannot be deleted, and the next test
          // opens its own by name regardless, so failing here would fail a passing test.
        }
      }
    }

    localStorage.removeItem(localStorageKey);

    vi.clearAllMocks();
  });

  describe('database initialization', () => {
    it('should not be ready when user is not set', async () => {
      const { useDatabase } = await import('./use-database');
      const { isReady } = scope.run(() => useDatabase())!;

      await nextTick();

      expect(get(isReady)).toBe(false);
    });

    it('should not be ready when dataDirectory is not set', async () => {
      set(mockUserIdentifier, testUsername);

      const { useDatabase } = await import('./use-database');
      const { isReady } = scope.run(() => useDatabase())!;

      await nextTick();

      expect(get(isReady)).toBe(false);
    });

    it('should be ready when both user and dataDirectory are set', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
    });

    it('should create database with correct name format', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
      expect(db().name).toMatch(/^rotki\.data\.[\da-z]{6}\.testuser$/);
    });

    it('should have both tables available', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);

      expect(await db().missingMappings.count()).toBe(0);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
    });
  });

  describe('migration from old {username}.data database', () => {
    it('should handle non-existent old database gracefully', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(0);

      const allDatabases = await Dexie.getDatabaseNames();
      expect(allDatabases).not.toContain(`${testUsername}.data`);
    });

    it('should migrate missing mappings from old database', async () => {
      // The old database has to exist before `useDatabase` initialises, or there is nothing to
      // migrate from.
      const oldDb = createOldUserDb(testUsername);
      await oldDb.open();

      const testMappings: Omit<MissingMapping, 'id'>[] = [
        { identifier: 'asset-1', name: 'Asset One', location: 'ethereum', details: 'Details 1' },
        { identifier: 'asset-2', name: 'Asset Two', location: 'optimism', details: 'Details 2' },
      ];
      await oldDb.missingMappings.bulkAdd(testMappings);
      expect(await oldDb.missingMappings.count()).toBe(2);
      oldDb.close();

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);

      const migratedMappings = await db().missingMappings.toArray();
      expect(migratedMappings).toHaveLength(2);
      expect(migratedMappings.map(m => m.identifier).sort()).toEqual(['asset-1', 'asset-2']);

      const allDatabases = await Dexie.getDatabaseNames();
      expect(allDatabases).not.toContain(`${testUsername}.data`);
    });

    it('should handle empty old database gracefully', async () => {
      const oldDb = createOldUserDb(testUsername);
      await oldDb.open();
      oldDb.close();

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(0);
    });
  });

  describe('migration from localStorage for newly detected tokens', () => {
    it('should migrate tokens from localStorage', async () => {
      const oldTokens = [
        { tokenIdentifier: 'eip155:1/erc20:0xabc', tokenKind: NewDetectedTokenKind.EVM },
        { tokenIdentifier: 'solana:mainnet/spl:xyz', tokenKind: NewDetectedTokenKind.SOLANA },
      ];
      localStorage.setItem(localStorageKey, JSON.stringify(oldTokens));

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);

      const migratedTokens = await db().newlyDetectedTokens.toArray();
      expect(migratedTokens).toHaveLength(2);
      expect(migratedTokens.map(t => t.tokenIdentifier).sort()).toEqual([
        'eip155:1/erc20:0xabc',
        'solana:mainnet/spl:xyz',
      ]);
      expect(migratedTokens.every(t => typeof t.detectedAt === 'number')).toBe(true);

      expect(localStorage.getItem(localStorageKey)).toBeNull();
    });

    it('should handle missing localStorage gracefully', async () => {
      localStorage.removeItem(localStorageKey);

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
    });

    it('should handle invalid localStorage data gracefully', async () => {
      localStorage.setItem(localStorageKey, 'not-valid-json{');

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
      expect(localStorage.getItem(localStorageKey)).toBeNull();
    });
  });

  describe('combined migrations', () => {
    it('should handle clean start with no migration sources', async () => {
      localStorage.removeItem(localStorageKey);

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(0);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
    });

    it('should migrate only old database when localStorage is missing', async () => {
      const oldDb = createOldUserDb(testUsername);
      await oldDb.open();
      await oldDb.missingMappings.add({
        identifier: 'only-db-asset',
        name: 'Only DB Asset',
        location: 'ethereum',
        details: 'From old DB only',
      });
      oldDb.close();

      localStorage.removeItem(localStorageKey);

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(1);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
    });

    it('should migrate only localStorage when old database is missing', async () => {
      const oldTokens = [
        { tokenIdentifier: 'eip155:1/erc20:0xonlylocal', tokenKind: NewDetectedTokenKind.EVM },
      ];
      localStorage.setItem(localStorageKey, JSON.stringify(oldTokens));

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(0);
      expect(await db().newlyDetectedTokens.count()).toBe(1);

      expect(localStorage.getItem(localStorageKey)).toBeNull();
    });

    it('should migrate both old database and localStorage in single initialization', async () => {
      const oldDb = createOldUserDb(testUsername);
      await oldDb.open();
      const testMapping: Omit<MissingMapping, 'id'> = {
        identifier: 'migrated-asset',
        name: 'Migrated Asset',
        location: 'ethereum',
        details: 'From old DB',
      };
      await oldDb.missingMappings.add(testMapping);
      oldDb.close();

      const oldTokens = [
        { tokenIdentifier: 'eip155:1/erc20:0xmigrated', tokenKind: NewDetectedTokenKind.EVM },
      ];
      localStorage.setItem(localStorageKey, JSON.stringify(oldTokens));

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);

      expect(await db().missingMappings.count()).toBe(1);
      expect(await db().newlyDetectedTokens.count()).toBe(1);

      const mappings = await db().missingMappings.toArray();
      expect(mappings[0]?.identifier).toBe('migrated-asset');

      const tokens = await db().newlyDetectedTokens.toArray();
      expect(tokens[0]?.tokenIdentifier).toBe('eip155:1/erc20:0xmigrated');
    });
  });

  describe('user/directory change handling', () => {
    it('should close old database when user changes', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      // Held whole rather than destructured: `db` is a getter, and a destructured copy would keep
      // answering with the first user's database.
      const database = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(database.isReady);

      expect(get(database.isReady)).toBe(true);
      const firstDbName = database.db.name;

      await database.db().newlyDetectedTokens.add({
        tokenIdentifier: 'test-token',
        tokenKind: NewDetectedTokenKind.EVM,
        detectedAt: Date.now(),
      });

      set(mockUserIdentifier, 'differentuser');

      await nextTick();
      await waitUntilReady(database.isReady);

      expect(get(database.isReady)).toBe(true);
      expect(database.db().name).not.toBe(firstDbName);
      expect(database.db().name).toContain('differentuser');

      expect(await database.db().newlyDetectedTokens.count()).toBe(0);
    });

    it('should become not ready when user is cleared', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { isReady } = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(isReady);

      expect(get(isReady)).toBe(true);

      set(mockUserIdentifier, undefined);

      await nextTick();
      await waitUntilNotReady(isReady);

      expect(get(isReady)).toBe(false);
    });
  });

  describe('database identifier format', () => {
    it('should use different databases for different data directories', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, '/path/one');

      const { useDatabase } = await import('./use-database');
      // Held whole rather than destructured: `db` is a getter, and a destructured copy would keep
      // answering with the first user's database.
      const database = scope.run(() => useDatabase())!;

      await nextTick();
      await waitUntilReady(database.isReady);

      expect(get(database.isReady)).toBe(true);
      const firstDbName = database.db.name;

      set(mockDataDirectory, '/path/two');

      await nextTick();
      await waitUntilReady(database.isReady);

      expect(get(database.isReady)).toBe(true);
      expect(database.db().name).not.toBe(firstDbName);
    });
  });
});
