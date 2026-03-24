import type { MaybeRef } from 'vue';
import type { InternalTxConflict, InternalTxConflictsCountPayload, InternalTxConflictsCountResponse, InternalTxConflictsRequestPayload } from './types';
import type { Collection, CollectionResponse } from '@/types/collection';
import { api } from '@/modules/api/rotki-api';
import { mapCollectionResponse } from '@/utils/collection';
import { nonEmptyProperties } from '@/utils/data';

interface UseInternalTxConflictsApiReturn {
  fetchInternalTxConflicts: (payload: MaybeRef<InternalTxConflictsRequestPayload>) => Promise<Collection<InternalTxConflict>>;
  fetchInternalTxConflictsCount: (payload: InternalTxConflictsCountPayload) => Promise<InternalTxConflictsCountResponse>;
}

export function useInternalTxConflictsApi(): UseInternalTxConflictsApiReturn {
  const fetchInternalTxConflicts = async (
    payload: MaybeRef<InternalTxConflictsRequestPayload>,
  ): Promise<Collection<InternalTxConflict>> => {
    const response = await api.get<CollectionResponse<InternalTxConflict>>(
      '/blockchains/transactions/internal/conflicts',
      { query: nonEmptyProperties(get(payload)) },
    );
    return mapCollectionResponse(response);
  };

  const fetchInternalTxConflictsCount = async (
    payload: InternalTxConflictsCountPayload,
  ): Promise<InternalTxConflictsCountResponse> => {
    const response = await api.post<InternalTxConflictsCountResponse>(
      '/blockchains/transactions/internal/conflicts',
      nonEmptyProperties(payload),
    );
    return response;
  };

  return { fetchInternalTxConflicts, fetchInternalTxConflictsCount };
}
