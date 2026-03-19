import type { MaybeRef } from 'vue';
import type { InternalTxConflict, InternalTxConflictsRequestPayload } from './types';
import type { Collection, CollectionResponse } from '@/types/collection';
import { api } from '@/modules/api/rotki-api';
import { mapCollectionResponse } from '@/utils/collection';
import { nonEmptyProperties } from '@/utils/data';

interface UseInternalTxConflictsApiReturn {
  fetchInternalTxConflicts: (payload: MaybeRef<InternalTxConflictsRequestPayload>) => Promise<Collection<InternalTxConflict>>;
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

  return { fetchInternalTxConflicts };
}
