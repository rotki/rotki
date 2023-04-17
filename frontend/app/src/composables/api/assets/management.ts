import { type ActionResult, type SupportedAsset } from '@rotki/common/lib/data';
import { OwnedAssets } from '@rotki/common/lib/statistics';
import { type MaybeRef } from '@vueuse/core';
import { type Collection } from '@/types/collection';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionAndExternalService,
  validWithoutSessionStatus
} from '@/services/utils';
import {
  type AssetIdResponse,
  type AssetRequestPayload,
  type CustomAsset,
  type CustomAssetRequestPayload,
  CustomAssets,
  SupportedAssets
} from '@/types/asset';

export const useAssetManagementApi = () => {
  const queryAllAssets = async (
    pagination: MaybeRef<AssetRequestPayload>
  ): Promise<Collection<SupportedAsset>> => {
    const response = await api.instance.post<ActionResult<SupportedAssets>>(
      '/assets/all',
      snakeCaseTransformer(get(pagination)),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return mapCollectionResponse(
      SupportedAssets.parse(handleResponse(response))
    );
  };

  const queryAllCustomAssets = async (
    pagination: MaybeRef<CustomAssetRequestPayload>
  ): Promise<Collection<CustomAsset>> => {
    const response = await api.instance.post<ActionResult<CustomAssets>>(
      '/assets/custom',
      snakeCaseTransformer(get(pagination)),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return mapCollectionResponse(CustomAssets.parse(handleResponse(response)));
  };

  const queryOwnedAssets = async (): Promise<string[]> => {
    const ownedAssets = await api.instance.get<ActionResult<string[]>>(
      '/assets',
      {
        validateStatus: validStatus
      }
    );

    return OwnedAssets.parse(handleResponse(ownedAssets));
  };

  const addEthereumToken = async (
    token: Omit<SupportedAsset, 'identifier'>
  ): Promise<AssetIdResponse> => {
    const response = await api.instance.put<ActionResult<AssetIdResponse>>(
      '/assets/ethereum',
      snakeCaseTransformer({ token }),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const editEthereumToken = async (
    token: Omit<SupportedAsset, 'identifier'>
  ): Promise<AssetIdResponse> => {
    const response = await api.instance.patch<ActionResult<AssetIdResponse>>(
      '/assets/ethereum',
      snakeCaseTransformer({ token }),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteEthereumToken = async (
    address: string,
    chain: string
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/ethereum',
      {
        data: snakeCaseTransformer({ address, chain }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const getAssetTypes = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(
      '/assets/types',
      {
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const addAsset = async (
    asset: Omit<SupportedAsset, 'identifier'>
  ): Promise<AssetIdResponse> => {
    const response = await api.instance.put<ActionResult<AssetIdResponse>>(
      '/assets/all',
      snakeCaseTransformer(asset),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const editAsset = async (asset: SupportedAsset): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/assets/all',
      snakeCaseTransformer(asset),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteAsset = async (identifier: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/all',
      {
        data: snakeCaseTransformer({ identifier }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const getCustomAssetTypes = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(
      '/assets/custom/types',
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const addCustomAsset = async (
    asset: Omit<CustomAsset, 'identifier'>
  ): Promise<string> => {
    const response = await api.instance.put<ActionResult<string>>(
      '/assets/custom',
      snakeCaseTransformer(asset),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const editCustomAsset = async (asset: CustomAsset): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/assets/custom',
      snakeCaseTransformer(asset),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteCustomAsset = async (identifier: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/custom',
      {
        data: snakeCaseTransformer({ identifier }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    queryAllAssets,
    queryAllCustomAssets,
    queryOwnedAssets,
    addEthereumToken,
    editEthereumToken,
    deleteEthereumToken,
    addAsset,
    editAsset,
    deleteAsset,
    getAssetTypes,
    getCustomAssetTypes,
    addCustomAsset,
    editCustomAsset,
    deleteCustomAsset
  };
};
