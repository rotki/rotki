import { apiUrls } from '@/services/api-urls';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import type { ActionResult } from '@rotki/common';

interface UseCollectionIdentifiersReturn { getCollectionAssets: (collectionId: string) => Promise<string[]> }

export function useCollectionIdentifiers(): UseCollectionIdentifiersReturn {
  async function getCollectionAssets(collectionId: string): Promise<string[]> {
    const url = `/assets/collections?collection_id=${encodeURIComponent(collectionId)}`;
    const response = await api.instance.get<ActionResult<string[]>>(url, {
      baseURL: apiUrls.colibriApiUrl,
      validateStatus: code => [200].includes(code),
    });
    return handleResponse(response);
  }
  return {
    getCollectionAssets,
  };
}
