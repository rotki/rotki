import { type ItemFilter, getPage } from '@/modules/data/pagination';
import { useDatabase } from '@/modules/data/use-database';
import type { PaginationRequestPayload } from '@/types/common';
import type { Collection } from '@/types/collection';
import type { MaybeRef } from '@vueuse/core';
import type { MissingMapping } from '@/modules/data/schemas';

interface MissingMappingsFilterParams {
  identifier?: string;
  location?: string;
}

export interface MissingMappingsRequestPayload extends PaginationRequestPayload<MissingMapping>,
  MissingMappingsFilterParams {}

export type AddMissingMapping = Omit<MissingMapping, 'id'>;

interface UseMappingDBReturn {
  put: (mapping: AddMissingMapping) => Promise<number>;
  count: () => Promise<number>;
  getData: (payload: MaybeRef<PaginationRequestPayload<MissingMapping>>) => Promise<Collection<MissingMapping>>;
}

export function useMissingMappingsDB(): UseMappingDBReturn {
  const { db } = useDatabase();

  async function put(mapping: AddMissingMapping): Promise<number> {
    return db.missingMappings.put(mapping);
  }

  async function count(): Promise<number> {
    return db.missingMappings.count();
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

    const table = db.missingMappings;
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

  return {
    count,
    getData,
    put,
  };
}
