import type { Collection } from '@/types/collection';
import type { ActionResult } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import {
  type CexMapping,
  CexMappingCollectionResponse,
  type CexMappingDeletePayload,
  type CexMappingRequestPayload,
} from '@/types/asset';
import { mapCollectionResponse } from '@/utils/collection';
import { omit } from 'es-toolkit';

interface UseAssetCexMappingApiReturn {
  fetchAllCexMapping: (payload: MaybeRef<CexMappingRequestPayload>) => Promise<Collection<CexMapping>>;
  addCexMapping: (payload: CexMapping) => Promise<boolean>;
  editCexMapping: (payload: CexMapping) => Promise<boolean>;
  deleteCexMapping: (payload: CexMappingDeletePayload) => Promise<boolean>;
}

export function useAssetCexMappingApi(): UseAssetCexMappingApiReturn {
  const fetchAllCexMapping = async (payload: MaybeRef<CexMappingRequestPayload>): Promise<Collection<CexMapping>> => {
    const response = await api.instance.post<ActionResult<Collection<CexMapping>>>(
      '/assets/locationmappings',
      snakeCaseTransformer(omit(get(payload), ['orderByAttributes', 'ascending'])),
      {
        validateStatus: validStatus,
      },
    );

    return mapCollectionResponse(CexMappingCollectionResponse.parse(handleResponse(response)));
  };

  const addCexMapping = async (payload: CexMapping): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/assets/locationmappings',
      snakeCaseTransformer({
        entries: [payload],
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const editCexMapping = async (payload: CexMapping): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/assets/locationmappings',
      snakeCaseTransformer({
        entries: [payload],
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const deleteCexMapping = async (payload: CexMappingDeletePayload): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/assets/locationmappings', {
      data: snakeCaseTransformer({
        entries: [payload],
      }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    addCexMapping,
    deleteCexMapping,
    editCexMapping,
    fetchAllCexMapping,
  };
}
