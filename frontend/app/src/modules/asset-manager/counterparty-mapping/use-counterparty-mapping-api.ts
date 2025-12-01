import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import { omit } from 'es-toolkit';
import { api } from '@/modules/api/rotki-api';
import {
  type CounterpartyMapping,
  CounterpartyMappingCollectionResponse,
  type CounterpartyMappingDeletePayload,
  type CounterpartyMappingRequestPayload,
} from '@/modules/asset-manager/counterparty-mapping/schema';
import { mapCollectionResponse } from '@/utils/collection';

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
