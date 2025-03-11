import type { MissingMapping } from '@/modules/data/schemas';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { assert } from '@rotki/common';
import Dexie, { type EntityTable } from 'dexie';

interface DexieDB extends Dexie {
  missingMappings: EntityTable<MissingMapping, 'id'>;
}

interface UseDatabaseReturn {
  readonly db: DexieDB;
}

export const useDatabase = createSharedComposable((): UseDatabaseReturn => {
  const dbInstance = ref<DexieDB>();
  const userIdentifier = useLoggedUserIdentifier();

  function initDb(): DexieDB {
    const db = new Dexie(`${get(userIdentifier)}.data`);
    db.version(1).stores({
      missingMappings: '++id, [identifier], name, [location], &[identifier+location], details',
    });
    return db as DexieDB;
  }

  watchImmediate(userIdentifier, (user) => {
    if (user) {
      set(dbInstance, initDb());
    }
    else {
      set(dbInstance, undefined);
    }
  });

  return {
    get db(): DexieDB {
      assert(isDefined(dbInstance), 'Database is not initialized');
      return get(dbInstance);
    },
  };
});
