import type { Ref } from 'vue';
import type { MissingMapping } from '@/modules/data/schemas';
import { assert } from '@rotki/common';
import Dexie, { type EntityTable } from 'dexie';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { createDatabaseIdentifier } from '@/modules/data/utils/hash';
import { type NewDetectedTokenRecord, NewDetectedTokens } from '@/modules/newly-detected-tokens/types';
import { useMainStore } from '@/store/main';
import { logger } from '@/utils/logging';

const NEWLY_DETECTED_TOKENS_MIGRATION_KEY_PREFIX = 'rotki.newly_detected_tokens.';

export interface RotkiDB extends Dexie {
  missingMappings: EntityTable<MissingMapping, 'id'>;
  newlyDetectedTokens: EntityTable<NewDetectedTokenRecord, 'id'>;
}

interface UseDatabaseReturn {
  readonly db: () => RotkiDB;
  readonly isReady: Ref<boolean>;
}

function createRotkiDb(identifier: string): RotkiDB {
  const db = new Dexie(`rotki.data.${identifier}`);

  db.version(1).stores({
    missingMappings: '++id, [identifier], name, [location], &[identifier+location], details',
    newlyDetectedTokens: '++id, tokenIdentifier, tokenKind, detectedAt',
  });

  return db as RotkiDB;
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
      const database = createRotkiDb(identifier);
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

  return {
    db(): RotkiDB {
      assert(isDefined(dbInstance), 'Database is not initialized');
      return get(dbInstance);
    },
    isReady,
  };
});
