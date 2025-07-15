import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import { type ActionResult, OwnedAssets, type SupportedAsset } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithoutSessionStatus,
  validWithSessionAndExternalService,
} from '@/services/utils';
import {
  type AssetIdResponse,
  type AssetRequestPayload,
  type CustomAsset,
  type CustomAssetRequestPayload,
  CustomAssets,
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
    const response = await api.instance.post<ActionResult<SupportedAssets>>(
      '/assets/all',
      snakeCaseTransformer(get(payload)),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return mapCollectionResponse(SupportedAssets.parse(handleResponse(response)));
  };

  const queryAllCustomAssets = async (
    payload: MaybeRef<CustomAssetRequestPayload>,
  ): Promise<Collection<CustomAsset>> => {
    const response = await api.instance.post<ActionResult<CustomAssets>>(
      '/assets/custom',
      snakeCaseTransformer(get(payload)),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return mapCollectionResponse(CustomAssets.parse(handleResponse(response)));
  };

  const queryOwnedAssets = async (): Promise<string[]> => {
    const ownedAssets = await api.instance.get<ActionResult<string[]>>('/assets', {
      validateStatus: validStatus,
    });

    return OwnedAssets.parse(handleResponse(ownedAssets));
  };

  const getAssetTypes = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>('/assets/types', {
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  const addAsset = async (asset: Omit<SupportedAsset, 'identifier'>): Promise<AssetIdResponse> => {
    const response = await api.instance.put<ActionResult<AssetIdResponse>>('/assets/all', snakeCaseTransformer(asset), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const editAsset = async (asset: SupportedAsset): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>('/assets/all', snakeCaseTransformer(asset), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const deleteAsset = async (identifier: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/assets/all', {
      data: snakeCaseTransformer({ identifier }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const getCustomAssetTypes = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>('/assets/custom/types', {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const addCustomAsset = async (asset: Omit<CustomAsset, 'identifier'>): Promise<string> => {
    const response = await api.instance.put<ActionResult<string>>('/assets/custom', snakeCaseTransformer(asset), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const editCustomAsset = async (asset: CustomAsset): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>('/assets/custom', snakeCaseTransformer(asset), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const deleteCustomAsset = async (identifier: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/assets/custom', {
      data: snakeCaseTransformer({ identifier }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

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
