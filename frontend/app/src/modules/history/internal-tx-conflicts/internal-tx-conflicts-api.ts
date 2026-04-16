import type { MaybeRef } from 'vue';
import type { InternalTxConflict, InternalTxConflictsCountResponse, InternalTxConflictsRequestPayload } from './types';
import type { Collection, CollectionResponse } from '@/modules/core/common/collection';
import { api } from '@/modules/core/api/rotki-api';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { nonEmptyProperties } from '@/modules/core/common/data/data';

interface UseInternalTxConflictsApiReturn {
  fetchInternalTxConflicts: (payload: MaybeRef<InternalTxConflictsRequestPayload>) => Promise<Collection<InternalTxConflict>>;
  fetchInternalTxConflictsCount: () => Promise<InternalTxConflictsCountResponse>;
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

  const fetchInternalTxConflictsCount = async (): Promise<InternalTxConflictsCountResponse> =>
    api.post<InternalTxConflictsCountResponse>('/blockchains/transactions/internal/conflicts');

  return { fetchInternalTxConflicts, fetchInternalTxConflictsCount };
}
