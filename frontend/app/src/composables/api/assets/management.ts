import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import { OwnedAssets, type SupportedAsset } from '@rotki/common';
import { api } from '@/modules/api/rotki-api';
import {
  VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITHOUT_SESSION_STATUS,
} from '@/modules/api/utils';
import {
  type AssetIdResponse,
  type AssetRequestPayload,
  type CustomAsset,
  type CustomAssetRequestPayload,
  CustomAssets,
  SOLANA_CHAIN,
  SOLANA_TOKEN,
  SupportedAssets,
} from '@/types/asset';
import { mapCollectionResponse } from '@/utils/collection';

interface UseAssetManagementApiReturn {
  queryAllAssets: (payload: MaybeRef<AssetRequestPayload>) => Promise<Collection<SupportedAsset>>;
  queryAllCustomAssets: (payload: MaybeRef<CustomAssetRequestPayload>) => Promise<Collection<CustomAsset>>;
  queryOwnedAssets: () => Promise<string[]>;
  addAsset: (asset: Omit<SupportedAsset, 'identifier'>) => Promise<AssetIdResponse>;
  editAsset: (asset: SupportedAsset) => Promise<boolean>;
  deleteAsset: (identifier: string) => Promise<boolean>;
  getAssetTypes: () => Promise<string[]>;
  getCustomAssetTypes: () => Promise<string[]>;
  addCustomAsset: (asset: Omit<CustomAsset, 'identifier'>) => Promise<string>;
  editCustomAsset: (asset: CustomAsset) => Promise<boolean>;
  deleteCustomAsset: (identifier: string) => Promise<boolean>;
}

export function useAssetManagementApi(): UseAssetManagementApiReturn {
  const queryAllAssets = async (payload: MaybeRef<AssetRequestPayload>): Promise<Collection<SupportedAsset>> => {
    const payloadValue = get(payload);
    const transformedPayload = { ...payloadValue };

    if (transformedPayload.evmChain === SOLANA_CHAIN) {
      delete transformedPayload.evmChain;
      transformedPayload.assetType = SOLANA_TOKEN;
    }

    const response = await api.post<SupportedAssets>(
      '/assets/all',
      transformedPayload,
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );

    return mapCollectionResponse(SupportedAssets.parse(response));
  };

  const queryAllCustomAssets = async (
    payload: MaybeRef<CustomAssetRequestPayload>,
  ): Promise<Collection<CustomAsset>> => {
    const response = await api.post<CustomAssets>(
      '/assets/custom',
      get(payload),
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );

    return mapCollectionResponse(CustomAssets.parse(response));
  };

  const queryOwnedAssets = async (): Promise<string[]> => {
    const ownedAssets = await api.get<string[]>('/assets');

    return OwnedAssets.parse(ownedAssets);
  };

  const getAssetTypes = async (): Promise<string[]> => api.get<string[]>('/assets/types', {
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  const addAsset = async (asset: Omit<SupportedAsset, 'identifier'>): Promise<AssetIdResponse> => api.put<AssetIdResponse>('/assets/all', asset);

  const editAsset = async (asset: SupportedAsset): Promise<boolean> => api.patch<boolean>('/assets/all', asset);

  const deleteAsset = async (identifier: string): Promise<boolean> => api.delete<boolean>('/assets/all', {
    body: { identifier },
  });

  const getCustomAssetTypes = async (): Promise<string[]> => api.get<string[]>('/assets/custom/types');

  const addCustomAsset = async (asset: Omit<CustomAsset, 'identifier'>): Promise<string> => api.put<string>('/assets/custom', asset);

  const editCustomAsset = async (asset: CustomAsset): Promise<boolean> => api.patch<boolean>('/assets/custom', asset);

  const deleteCustomAsset = async (identifier: string): Promise<boolean> => api.delete<boolean>('/assets/custom', {
    body: { identifier },
  });

  return {
    addAsset,
    addCustomAsset,
    deleteAsset,
    deleteCustomAsset,
    editAsset,
    editCustomAsset,
    getAssetTypes,
    getCustomAssetTypes,
    queryAllAssets,
    queryAllCustomAssets,
    queryOwnedAssets,
  };
}
