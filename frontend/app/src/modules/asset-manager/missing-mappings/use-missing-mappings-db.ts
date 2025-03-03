import Dexie, { type EntityTable } from 'dexie';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { type ItemFilter, getPage } from '@/modules/data/pagination';
import type { PaginationRequestPayload } from '@/types/common';
import type { Collection } from '@/types/collection';
import type { MaybeRef } from '@vueuse/core';

export interface MissingMapping {
  id: number;
  identifier: string;
  name: string;
  location: string;
  details: string;
}

interface MissingMappingsFilterParams {
  identifier?: string;
  location?: string;
}

export interface MissingMappingsRequestPayload extends PaginationRequestPayload<MissingMapping>,
  MissingMappingsFilterParams {}

type AddMissingMapping = Omit<MissingMapping, 'id'>;

interface UseMissingMappingsDb extends Dexie {
  missingMappings: EntityTable<MissingMapping, 'id'>;
}

interface UseMappingDBReturn {
  put: (mapping: AddMissingMapping) => Promise<number>;
  count: () => Promise<number>;
  getData: (payload: MaybeRef<PaginationRequestPayload<MissingMapping>>) => Promise<Collection<MissingMapping>>;
}

export function useMissingMappingsDB(): UseMappingDBReturn {
  const userIdentifier = useLoggedUserIdentifier();
  let dbInstance: UseMissingMappingsDb | undefined;

  function instance(): UseMissingMappingsDb {
    assert(dbInstance, 'Mappings DB not initialized');
    return dbInstance;
  }

  function createMappingsDB(): UseMissingMappingsDb {
    const db = new Dexie(`${get(userIdentifier)}.mappings`);
    db.version(1).stores({
      missingMappings: '++id, [identifier], name, [location], &[identifier+location], details',
    });
    return db as UseMissingMappingsDb;
  }

  async function put(mapping: AddMissingMapping): Promise<number> {
    return instance().missingMappings.put(mapping);
  }

  async function count(): Promise<number> {
    return instance().missingMappings.count();
  }

  async function getData(payload: MaybeRef<MissingMappingsRequestPayload>): Promise<Collection<MissingMapping>> {
    const {
      ascending = [],
      identifier,
      limit,
      location,
      offset,
      orderByAttributes = [],
    } = get(payload);

    let filter: ItemFilter<MissingMapping> | undefined;
    if (identifier || location) {
      filter = (m): boolean => {
        if (identifier && !m.identifier.toLowerCase().startsWith(identifier.toLowerCase()))
          return false;
        if (location && m.location !== location)
          return false;
        return true;
      };
    }

    const table = instance().missingMappings;
    const { data, total } = await getPage<MissingMapping, 'id'>(table, {
      limit,
      offset,
      order: ascending.length > 0 ? (ascending[0] ? 'asc' : 'desc') : 'asc',
      orderBy: orderByAttributes.length > 0 ? orderByAttributes[0] : 'location',
    }, filter);

    return {
      data,
      found: total,
      limit: -1,
      total,
    };
  }

  watchImmediate(userIdentifier, (user) => {
    if (user) {
      dbInstance = createMappingsDB();
    }
    else {
      dbInstance = undefined;
    }
  });

  return {
    count,
    getData,
    put,
  };
}
