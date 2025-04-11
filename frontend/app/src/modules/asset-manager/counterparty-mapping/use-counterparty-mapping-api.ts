import type { Collection } from '@/types/collection';
import type { ActionResult } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import {
  type CounterpartyMapping,
  CounterpartyMappingCollectionResponse,
  type CounterpartyMappingDeletePayload,
  type CounterpartyMappingRequestPayload,
} from '@/modules/asset-manager/counterparty-mapping/schema';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { mapCollectionResponse } from '@/utils/collection';
import { omit } from 'es-toolkit';

interface UseCounterpartyMappingApiReturn {
  fetchAllCounterpartyMapping: (payload: MaybeRef<CounterpartyMappingRequestPayload>) => Promise<Collection<CounterpartyMapping>>;
  addCounterpartyMapping: (payload: CounterpartyMapping) => Promise<boolean>;
  editCounterpartyMapping: (payload: CounterpartyMapping) => Promise<boolean>;
  deleteCounterpartyMapping: (payload: CounterpartyMappingDeletePayload) => Promise<boolean>;
}

export function useCounterpartyMappingApi(): UseCounterpartyMappingApiReturn {
  const fetchAllCounterpartyMapping = async (payload: MaybeRef<CounterpartyMappingRequestPayload>): Promise<Collection<CounterpartyMapping>> => {
    const response = await api.instance.post<ActionResult<Collection<CounterpartyMapping>>>(
      '/assets/counterpartymappings',
      snakeCaseTransformer(omit(get(payload), ['orderByAttributes', 'ascending'])),
      {
        validateStatus: validStatus,
      },
    );

    return mapCollectionResponse(CounterpartyMappingCollectionResponse.parse(handleResponse(response)));
  };

  const addCounterpartyMapping = async (payload: CounterpartyMapping): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/assets/counterpartymappings',
      snakeCaseTransformer({
        entries: [payload],
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const editCounterpartyMapping = async (payload: CounterpartyMapping): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/assets/counterpartymappings',
      snakeCaseTransformer({
        entries: [payload],
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const deleteCounterpartyMapping = async (payload: CounterpartyMappingDeletePayload): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/assets/counterpartymappings', {
      data: snakeCaseTransformer({
        entries: [payload],
      }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    addCounterpartyMapping,
    deleteCounterpartyMapping,
    editCounterpartyMapping,
    fetchAllCounterpartyMapping,
  };
}
