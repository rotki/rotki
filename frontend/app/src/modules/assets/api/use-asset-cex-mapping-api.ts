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

interface CexMappingWireKey {
  connector: string | null;
  connectorSymbol: string;
}

/**
 * The backend calls the exchange of a mapping its connector, while this module still calls it the
 * location.
 */
function toWireKey({ location, locationSymbol }: CexMappingDeletePayload): CexMappingWireKey {
  return { connector: location, connectorSymbol: locationSymbol };
}

/** The table filter in the backend's names. */
function toWireFilter(payload: CexMappingRequestPayload): Record<string, unknown> {
  const { location, locationSymbol, ...rest } = omit(payload, ['orderByAttributes', 'ascending']);
  return { ...rest, connector: location, connectorSymbol: locationSymbol };
}

export function useAssetCexMappingApi(): UseAssetCexMappingApiReturn {
  const fetchAllCexMapping = async (payload: MaybeRef<CexMappingRequestPayload>): Promise<Collection<CexMapping>> => {
    const response = await api.post<unknown>('/assets/connectormappings', toWireFilter(get(payload)));

    return mapCollectionResponse(CexMappingCollectionResponse.parse(response));
  };

  const addCexMapping = async ({ asset, ...key }: CexMapping): Promise<boolean> => api.put<boolean>(
    '/assets/connectormappings',
    {
      entries: [{ asset, ...toWireKey(key) }],
    },
  );

  const editCexMapping = async ({ asset, ...key }: CexMapping): Promise<boolean> => api.patch<boolean>(
    '/assets/connectormappings',
    {
      entries: [{ asset, ...toWireKey(key) }],
    },
  );

  const deleteCexMapping = async (payload: CexMappingDeletePayload): Promise<boolean> => api.delete<boolean>('/assets/connectormappings', {
    body: {
      entries: [toWireKey(payload)],
    },
  });

  return {
    addCexMapping,
    deleteCexMapping,
    editCexMapping,
    fetchAllCexMapping,
  };
}
