import type { Ref } from 'vue';
import type { MissingMapping } from '@/modules/user-data/schemas';
import { assert } from '@rotki/common';
import Dexie, { type EntityTable } from 'dexie';
import { type NewDetectedTokenRecord, NewDetectedTokens } from '@/modules/assets/detection/types';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { logger } from '@/modules/core/common/logging/logging';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { createDatabaseIdentifier } from '@/modules/user-data/utils/hash';

const NEWLY_DETECTED_TOKENS_MIGRATION_KEY_PREFIX = 'rotki.newly_detected_tokens.';

/**
 * Dexie attaches the stores declared below at runtime, so they are declared with definite
 * assignment. This is Dexie's own subclass pattern; the alternative is asserting a plain
 * Dexie instance into the table-bearing shape.
 */
export class RotkiDB extends Dexie {
  missingMappings!: EntityTable<MissingMapping, 'id'>;
  newlyDetectedTokens!: EntityTable<NewDetectedTokenRecord, 'id'>;

  constructor(identifier: string) {
    super(`rotki.data.${identifier}`);
    this.version(1).stores({
      missingMappings: '++id, [identifier], name, [location], &[identifier+location], details',
      newlyDetectedTokens: '++id, tokenIdentifier, tokenKind, detectedAt',
    });
  }
}

interface UseDatabaseReturn {
  readonly db: () => RotkiDB;
  readonly isReady: Ref<boolean>;
}

async function migrateFromOldMissingMappingsDb(newDb: RotkiDB, username: string): Promise<void> {
  try {
    const allDatabases = await Dexie.getDatabaseNames();
    const oldDbName = `${username}.data`;

    if (!allDatabases.includes(oldDbName)) {
      return;
    }

    const oldDb = new Dexie(oldDbName);
    oldDb.version(1).stores({
      missingMappings: '++id, [identifier], name, [location], &[identifier+location], details',
    });

    await oldDb.open();

    const oldMappings = await oldDb.table('missingMappings').toArray();

    if (oldMappings.length > 0) {
      // Remove old IDs so new ones are assigned, preserve other fields
      const mappingsWithoutIds = oldMappings.map(({ id: _, ...rest }) => rest);
      await newDb.missingMappings.bulkAdd(mappingsWithoutIds);
      logger.info(`Migrated ${oldMappings.length} missing mappings to unified database`);
    }

    oldDb.close();
    await Dexie.delete(oldDbName);
  }
  catch (error) {
    logger.error('Failed to migrate missing mappings:', error);
  }
}

async function migrateNewlyDetectedTokensFromLocalStorage(newDb: RotkiDB, username: string): Promise<void> {
  const oldKey = `${NEWLY_DETECTED_TOKENS_MIGRATION_KEY_PREFIX}${username}`;
  const oldData = localStorage.getItem(oldKey);

  if (oldData === null) {
    return;
  }

  try {
    const parsed = JSON.parse(oldData);
    const oldTokens = NewDetectedTokens.parse(parsed);
    const now = Date.now();

    const existingIdentifiers = new Set(
      (await newDb.newlyDetectedTokens.toArray()).map(t => t.tokenIdentifier),
    );

    const newRecords: Omit<NewDetectedTokenRecord, 'id'>[] = oldTokens
      .filter(token => !existingIdentifiers.has(token.tokenIdentifier))
      .map(token => ({
        ...token,
        detectedAt: token.detectedAt ?? now,
      }));

    if (newRecords.length > 0) {
      await newDb.newlyDetectedTokens.bulkAdd(newRecords);
      logger.info(`Migrated ${newRecords.length} newly detected tokens from localStorage`);
    }
  }
  catch (error) {
    logger.error('Failed to migrate newly detected tokens from localStorage:', error);
  }
  finally {
    localStorage.removeItem(oldKey);
  }
}

export const useDatabase = createSharedComposable((): UseDatabaseReturn => {
  const dbInstance = ref<RotkiDB>();
  const isReady = ref<boolean>(false);

  const userIdentifier = useLoggedUserIdentifier();
  const mainStore = useMainStore();
  const { dataDirectory } = storeToRefs(mainStore);

  watch([userIdentifier, dataDirectory], async ([user, directory], [oldUser, oldDirectory]) => {
    if (user === oldUser && directory === oldDirectory) {
      return;
    }
    // Close existing database
    const existingDb = get(dbInstance);
    if (existingDb) {
      existingDb.close();
      set(dbInstance, undefined);
      set(isReady, false);
    }

    if (!user || !directory) {
      return;
    }

    try {
      const identifier = createDatabaseIdentifier(directory, user);
      const database = new RotkiDB(identifier);
      set(dbInstance, database);

      // Run migrations
      await migrateFromOldMissingMappingsDb(database, user);
      await migrateNewlyDetectedTokensFromLocalStorage(database, user);

      set(isReady, true);
    }
    catch (error) {
      logger.error('Failed to initialize database:', error);
      set(dbInstance, undefined);
      set(isReady, false);
    }
  }, { immediate: true });

  // Close the open connection when the shared composable is disposed, so it does
  // not linger and force Dexie to auto-close it on a later deleteDatabase.
  onScopeDispose(() => {
    get(dbInstance)?.close();
  });

  return {
    db(): RotkiDB {
      assert(isDefined(dbInstance), 'Database is not initialized');
      return get(dbInstance);
    },
    isReady,
  };
});
