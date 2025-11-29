import { apiUrls } from '@/modules/api/api-urls';
import { api } from '@/modules/api/rotki-api';
import { HTTPStatus } from '@/types/api/http';

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
