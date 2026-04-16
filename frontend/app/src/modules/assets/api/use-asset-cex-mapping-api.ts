import type { MaybeRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import { omit } from 'es-toolkit';
import {
  type CexMapping,
  CexMappingCollectionResponse,
  type CexMappingDeletePayload,
  type CexMappingRequestPayload,
} from '@/modules/assets/types';
import { api } from '@/modules/core/api/rotki-api';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';

interface UseAssetCexMappingApiReturn {
  fetchAllCexMapping: (payload: MaybeRef<CexMappingRequestPayload>) => Promise<Collection<CexMapping>>;
  addCexMapping: (payload: CexMapping) => Promise<boolean>;
  editCexMapping: (payload: CexMapping) => Promise<boolean>;
  deleteCexMapping: (payload: CexMappingDeletePayload) => Promise<boolean>;
}

export function useAssetCexMappingApi(): UseAssetCexMappingApiReturn {
  const fetchAllCexMapping = async (payload: MaybeRef<CexMappingRequestPayload>): Promise<Collection<CexMapping>> => {
    const response = await api.post<Collection<CexMapping>>(
      '/assets/locationmappings',
      omit(get(payload), ['orderByAttributes', 'ascending']),
    );

    return mapCollectionResponse(CexMappingCollectionResponse.parse(response));
  };

  const addCexMapping = async (payload: CexMapping): Promise<boolean> => api.put<boolean>(
    '/assets/locationmappings',
    {
      entries: [payload],
    },
  );

  const editCexMapping = async (payload: CexMapping): Promise<boolean> => api.patch<boolean>(
    '/assets/locationmappings',
    {
      entries: [payload],
    },
  );

  const deleteCexMapping = async (payload: CexMappingDeletePayload): Promise<boolean> => api.delete<boolean>('/assets/locationmappings', {
    body: {
      entries: [payload],
    },
  });

  return {
    addCexMapping,
    deleteCexMapping,
    editCexMapping,
    fetchAllCexMapping,
  };
}
