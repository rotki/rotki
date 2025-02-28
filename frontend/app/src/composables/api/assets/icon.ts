import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { apiUrls } from '@/services/api-urls';
import type { ActionResult } from '@rotki/common';

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
    let url = `${apiUrls.colibriApiUrl}/assets/icon?asset_id=${encodeURIComponent(identifier)}`;

    if (randomString)
      url += `&t=${randomString}`;

    return url;
  };

  const checkAsset = async (identifier: string, options: CheckAssetOptions): Promise<number> => {
    const url = `/assets/icon?asset_id=${encodeURIComponent(identifier)}`;
    const response = await api.instance.head<never>(url, {
      baseURL: apiUrls.colibriApiUrl,
      signal: options.abortController?.signal,
      validateStatus: code => [200, 202, 404].includes(code),
    });
    return response.status;
  };

  const uploadIcon = async (identifier: string, file: File): Promise<boolean> => {
    const data = new FormData();
    data.append('file', file);
    data.append('asset', identifier);
    const response = await api.instance.post<ActionResult<boolean>>(`/assets/icon/modify`, data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return handleResponse(response);
  };

  const setIcon = async (asset: string, file: string): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(`/assets/icon/modify`, {
      asset,
      file,
    });
    return handleResponse(response);
  };

  const refreshIcon = async (asset: string): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(`/assets/icon/modify`, {
      asset,
    });
    return handleResponse(response);
  };

  const clearIconCache = async (assets: string[] | null): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/cache/icons/clear',
      { entries: assets },
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  return {
    assetImageUrl,
    checkAsset,
    clearIconCache,
    refreshIcon,
    setIcon,
    uploadIcon,
  };
}
