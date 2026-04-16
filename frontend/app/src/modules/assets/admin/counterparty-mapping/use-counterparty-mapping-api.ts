import type { MaybeRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import { omit } from 'es-toolkit';
import {
  type CounterpartyMapping,
  CounterpartyMappingCollectionResponse,
  type CounterpartyMappingDeletePayload,
  type CounterpartyMappingRequestPayload,
} from '@/modules/assets/admin/counterparty-mapping/schema';
import { api } from '@/modules/core/api/rotki-api';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';

interface UseCounterpartyMappingApiReturn {
  fetchAllCounterpartyMapping: (payload: MaybeRef<CounterpartyMappingRequestPayload>) => Promise<Collection<CounterpartyMapping>>;
  addCounterpartyMapping: (payload: CounterpartyMapping) => Promise<boolean>;
  editCounterpartyMapping: (payload: CounterpartyMapping) => Promise<boolean>;
  deleteCounterpartyMapping: (payload: CounterpartyMappingDeletePayload) => Promise<boolean>;
}

export function useCounterpartyMappingApi(): UseCounterpartyMappingApiReturn {
  const fetchAllCounterpartyMapping = async (payload: MaybeRef<CounterpartyMappingRequestPayload>): Promise<Collection<CounterpartyMapping>> => {
    const response = await api.post<Collection<CounterpartyMapping>>(
      '/assets/counterpartymappings',
      omit(get(payload), ['orderByAttributes', 'ascending']),
    );

    return mapCollectionResponse(CounterpartyMappingCollectionResponse.parse(response));
  };

  const addCounterpartyMapping = async (payload: CounterpartyMapping): Promise<boolean> => api.put<boolean>(
    '/assets/counterpartymappings',
    { entries: [payload] },
  );

  const editCounterpartyMapping = async (payload: CounterpartyMapping): Promise<boolean> => api.patch<boolean>(
    '/assets/counterpartymappings',
    { entries: [payload] },
  );

  const deleteCounterpartyMapping = async (payload: CounterpartyMappingDeletePayload): Promise<boolean> => api.delete<boolean>('/assets/counterpartymappings', {
    body: { entries: [payload] },
  });

  return {
    addCounterpartyMapping,
    deleteCounterpartyMapping,
    editCounterpartyMapping,
    fetchAllCounterpartyMapping,
  };
}
