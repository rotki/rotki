import { apiUrls } from '@/modules/core/api/api-urls';
import { api } from '@/modules/core/api/rotki-api';
import { HTTPStatus } from '@/modules/core/api/types/http';

interface UseCollectionIdentifiersReturn { getCollectionAssets: (collectionId: string) => Promise<string[]> }

export function useCollectionIdentifiers(): UseCollectionIdentifiersReturn {
  async function getCollectionAssets(collectionId: string): Promise<string[]> {
    return api.get<string[]>('/assets/collections', {
      query: { collectionId },
      baseURL: apiUrls.colibriApiUrl,
      validStatuses: [HTTPStatus.OK],
    });
  }
  return {
    getCollectionAssets,
  };
}
