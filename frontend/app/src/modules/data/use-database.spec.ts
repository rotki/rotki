import type { MissingMapping } from '@/modules/data/schemas';
import { wait } from '@shared/utils';
import { get, set } from '@vueuse/core';
import Dexie, { type EntityTable } from 'dexie';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { NewDetectedTokenKind } from '@/modules/newly-detected-tokens/types';

// Old database structure (before migration)
interface OldUserDB extends Dexie {
  missingMappings: EntityTable<MissingMapping, 'id'>;
}

function createOldUserDb(username: string): OldUserDB {
  const db = new Dexie(`${username}.data`);
  db.version(1).stores({
    missingMappings: '++id, [identifier], name, [location], &[identifier+location], details',
  });
  return db as OldUserDB;
}

describe('useDatabase', () => {
  const testUsername = 'testuser';
  const testDataDirectory = '/test/data/dir';
  const localStorageKey = `rotki.newly_detected_tokens.${testUsername}`;

  let mockUserIdentifier: ReturnType<typeof ref<string | undefined>>;
  let mockDataDirectory: ReturnType<typeof ref<string | undefined>>;

  beforeEach(async () => {
    vi.resetModules();

    // Create fresh refs for each test
    mockUserIdentifier = ref<string>();
    mockDataDirectory = ref<string>();

    // Mock dependencies
    vi.doMock('@/composables/user/use-logged-user-identifier', () => ({
      useLoggedUserIdentifier: vi.fn(() => mockUserIdentifier),
    }));

    vi.doMock('@/store/main', () => ({
      useMainStore: vi.fn(() => ({
        dataDirectory: mockDataDirectory,
      })),
    }));

    // Mock storeToRefs to return dataDirectory ref directly
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
    // Clean up all test databases
    const allDatabases = await Dexie.getDatabaseNames();
    for (const dbName of allDatabases) {
      if (dbName.startsWith('rotki.data.') || dbName.endsWith('.data')) {
        try {
          await Dexie.delete(dbName);
        }
        catch {
          // Ignore
        }
      }
    }

    // Clean up localStorage
    localStorage.removeItem(localStorageKey);

    vi.clearAllMocks();
  });

  describe('database initialization', () => {
    it('should not be ready when user is not set', async () => {
      const { useDatabase } = await import('./use-database');
      const { isReady } = useDatabase();

      await nextTick();

      expect(get(isReady)).toBe(false);
    });

    it('should not be ready when dataDirectory is not set', async () => {
      set(mockUserIdentifier, testUsername);

      const { useDatabase } = await import('./use-database');
      const { isReady } = useDatabase();

      await nextTick();

      expect(get(isReady)).toBe(false);
    });

    it('should be ready when both user and dataDirectory are set', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { isReady } = useDatabase();

      // Wait for watch to execute
      await nextTick();
      await wait(50);

      expect(get(isReady)).toBe(true);
    });

    it('should create database with correct name format', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(50);

      expect(get(isReady)).toBe(true);
      expect(db().name).toMatch(/^rotki\.data\.[\da-z]{6}\.testuser$/);
    });

    it('should have both tables available', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(50);

      expect(get(isReady)).toBe(true);

      // Both tables should exist and be empty
      expect(await db().missingMappings.count()).toBe(0);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
    });
  });

  describe('migration from old {username}.data database', () => {
    it('should handle non-existent old database gracefully', async () => {
      // No old database created - test that migration handles this case
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(0);

      // Verify no old database exists
      const allDatabases = await Dexie.getDatabaseNames();
      expect(allDatabases).not.toContain(`${testUsername}.data`);
    });

    it('should migrate missing mappings from old database', async () => {
      // Step 1: Create old database with data BEFORE initializing useDatabase
      const oldDb = createOldUserDb(testUsername);
      await oldDb.open();

      const testMappings: Omit<MissingMapping, 'id'>[] = [
        { identifier: 'asset-1', name: 'Asset One', location: 'ethereum', details: 'Details 1' },
        { identifier: 'asset-2', name: 'Asset Two', location: 'optimism', details: 'Details 2' },
      ];
      await oldDb.missingMappings.bulkAdd(testMappings);
      expect(await oldDb.missingMappings.count()).toBe(2);
      oldDb.close();

      // Step 2: Initialize useDatabase - this should trigger migration
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);

      // Step 3: Verify data was migrated
      const migratedMappings = await db().missingMappings.toArray();
      expect(migratedMappings).toHaveLength(2);
      expect(migratedMappings.map(m => m.identifier).sort()).toEqual(['asset-1', 'asset-2']);

      // Step 4: Verify old database was deleted
      const allDatabases = await Dexie.getDatabaseNames();
      expect(allDatabases).not.toContain(`${testUsername}.data`);
    });

    it('should handle empty old database gracefully', async () => {
      // Create empty old database
      const oldDb = createOldUserDb(testUsername);
      await oldDb.open();
      oldDb.close();

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(0);
    });
  });

  describe('migration from localStorage for newly detected tokens', () => {
    it('should migrate tokens from localStorage', async () => {
      // Step 1: Set up localStorage with token data
      const oldTokens = [
        { tokenIdentifier: 'eip155:1/erc20:0xabc', tokenKind: NewDetectedTokenKind.EVM },
        { tokenIdentifier: 'solana:mainnet/spl:xyz', tokenKind: NewDetectedTokenKind.SOLANA },
      ];
      localStorage.setItem(localStorageKey, JSON.stringify(oldTokens));

      // Step 2: Initialize useDatabase - this should trigger migration
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);

      // Step 3: Verify tokens were migrated
      const migratedTokens = await db().newlyDetectedTokens.toArray();
      expect(migratedTokens).toHaveLength(2);
      expect(migratedTokens.map(t => t.tokenIdentifier).sort()).toEqual([
        'eip155:1/erc20:0xabc',
        'solana:mainnet/spl:xyz',
      ]);

      // All tokens should have detectedAt set
      expect(migratedTokens.every(t => typeof t.detectedAt === 'number')).toBe(true);

      // Step 4: Verify localStorage was cleaned up
      expect(localStorage.getItem(localStorageKey)).toBeNull();
    });

    it('should handle missing localStorage gracefully', async () => {
      // Ensure no localStorage data
      localStorage.removeItem(localStorageKey);

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
    });

    it('should handle invalid localStorage data gracefully', async () => {
      // Set up invalid JSON
      localStorage.setItem(localStorageKey, 'not-valid-json{');

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      // Should still be ready (migration failure is caught)
      expect(get(isReady)).toBe(true);
      expect(await db().newlyDetectedTokens.count()).toBe(0);

      // localStorage should be cleaned up even on error
      expect(localStorage.getItem(localStorageKey)).toBeNull();
    });
  });

  describe('combined migrations', () => {
    it('should handle clean start with no migration sources', async () => {
      // Neither old database nor localStorage exists - this is normal for new users
      localStorage.removeItem(localStorageKey);
      // Ensure no old database exists (none created in this test)

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(0);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
    });

    it('should migrate only old database when localStorage is missing', async () => {
      // Set up old IndexedDB only
      const oldDb = createOldUserDb(testUsername);
      await oldDb.open();
      await oldDb.missingMappings.add({
        identifier: 'only-db-asset',
        name: 'Only DB Asset',
        location: 'ethereum',
        details: 'From old DB only',
      });
      oldDb.close();

      // Ensure no localStorage
      localStorage.removeItem(localStorageKey);

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(1);
      expect(await db().newlyDetectedTokens.count()).toBe(0);
    });

    it('should migrate only localStorage when old database is missing', async () => {
      // No old database created
      // Set up localStorage only
      const oldTokens = [
        { tokenIdentifier: 'eip155:1/erc20:0xonlylocal', tokenKind: NewDetectedTokenKind.EVM },
      ];
      localStorage.setItem(localStorageKey, JSON.stringify(oldTokens));

      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);
      expect(await db().missingMappings.count()).toBe(0);
      expect(await db().newlyDetectedTokens.count()).toBe(1);

      // Verify localStorage was cleaned up
      expect(localStorage.getItem(localStorageKey)).toBeNull();
    });

    it('should migrate both old database and localStorage in single initialization', async () => {
      // Set up old IndexedDB
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

      // Set up localStorage
      const oldTokens = [
        { tokenIdentifier: 'eip155:1/erc20:0xmigrated', tokenKind: NewDetectedTokenKind.EVM },
      ];
      localStorage.setItem(localStorageKey, JSON.stringify(oldTokens));

      // Initialize useDatabase
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { db, isReady } = useDatabase();

      await nextTick();
      await wait(100);

      expect(get(isReady)).toBe(true);

      // Verify both migrations completed
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
      // Don't destructure db - we need to access the getter each time to get updated value
      const database = useDatabase();

      await nextTick();
      await wait(50);

      expect(get(database.isReady)).toBe(true);
      const firstDbName = database.db.name;

      // Add some data
      await database.db().newlyDetectedTokens.add({
        tokenIdentifier: 'test-token',
        tokenKind: NewDetectedTokenKind.EVM,
        detectedAt: Date.now(),
      });

      // Change user
      set(mockUserIdentifier, 'differentuser');

      await nextTick();
      await wait(50);

      expect(get(database.isReady)).toBe(true);
      // Access database.db to re-evaluate the getter
      expect(database.db().name).not.toBe(firstDbName);
      expect(database.db().name).toContain('differentuser');

      // New database should be empty (different user's data)
      expect(await database.db().newlyDetectedTokens.count()).toBe(0);
    });

    it('should become not ready when user is cleared', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, testDataDirectory);

      const { useDatabase } = await import('./use-database');
      const { isReady } = useDatabase();

      await nextTick();
      await wait(50);

      expect(get(isReady)).toBe(true);

      // Clear user
      set(mockUserIdentifier, undefined);

      await nextTick();
      await wait(50);

      expect(get(isReady)).toBe(false);
    });
  });

  describe('database identifier format', () => {
    it('should use different databases for different data directories', async () => {
      set(mockUserIdentifier, testUsername);
      set(mockDataDirectory, '/path/one');

      const { useDatabase } = await import('./use-database');
      // Don't destructure db - we need to access the getter each time to get updated value
      const database = useDatabase();

      await nextTick();
      await wait(50);

      expect(get(database.isReady)).toBe(true);
      const firstDbName = database.db.name;

      // Change data directory
      set(mockDataDirectory, '/path/two');

      await nextTick();
      await wait(50);

      expect(get(database.isReady)).toBe(true);
      // Access database.db to re-evaluate the getter
      expect(database.db().name).not.toBe(firstDbName);
    });
  });
});
