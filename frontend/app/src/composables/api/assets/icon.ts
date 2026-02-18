import { defaultApiUrls } from '@/modules/api/api-urls';
import { api } from '@/modules/api/rotki-api';
import { HTTPStatus } from '@/types/api/http';

interface CheckAssetOptions {
  abortController?: AbortController;
}

interface UseAssetIconApiReturn {
  assetImageUrl: (identifier: string, randomString?: string | number) => string;
  uploadIcon: (identifier: string, file: File) => Promise<boolean>;
  setIcon: (asset: string, file: string) => Promise<boolean>;
  refreshIcon: (asset: string) => Promise<boolean>;
  clearIconCache: (assets: string[] | null) => Promise<boolean>;
  checkAsset: (identifier: string, options: CheckAssetOptions) => Promise<number>;
}

export function useAssetIconApi(): UseAssetIconApiReturn {
  const assetImageUrl = (identifier: string, randomString?: string | number): string => {
    const url = new URL('/assets/icon', defaultApiUrls.colibriApiUrl);
    url.searchParams.set('asset_id', identifier);
    url.searchParams.set('use_collection_icon', 'true');

    if (randomString)
      url.searchParams.set('t', String(randomString));

    return url.toString();
  };

  const checkAsset = async (identifier: string, options: CheckAssetOptions): Promise<number> => {
    const params = new URLSearchParams();
    params.set('asset_id', identifier);
    params.set('use_collection_icon', 'true');
    return api.headStatus(`/assets/icon?${params.toString()}`, {
      baseURL: defaultApiUrls.colibriApiUrl,
      signal: options.abortController?.signal,
      validStatuses: [HTTPStatus.OK, HTTPStatus.ACCEPTED, HTTPStatus.NOT_FOUND],
    });
  };

  const uploadIcon = async (identifier: string, file: File): Promise<boolean> => {
    const data = new FormData();
    data.append('file', file);
    data.append('asset', identifier);
    return api.post<boolean>(`/assets/icon/modify`, data);
  };

  const setIcon = async (asset: string, file: string): Promise<boolean> => api.put<boolean>(`/assets/icon/modify`, {
    asset,
    file,
  });

  const refreshIcon = async (asset: string): Promise<boolean> => api.patch<boolean>(`/assets/icon/modify`, {
    asset,
  });

  const clearIconCache = async (assets: string[] | null): Promise<boolean> => api.post<boolean>(
    '/cache/icons/clear',
    { entries: assets },
  );

  return {
    assetImageUrl,
    checkAsset,
    clearIconCache,
    refreshIcon,
    setIcon,
    uploadIcon,
  };
}
