import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import type { ERC20Token } from '@/types/blockchain/accounts';
import type { EvmChainAddress } from '@/types/history/events';
import type { TaskMeta } from '@/types/task';
import { type AssetInfo, getAddressFromEvmIdentifier, isEvmIdentifier, NotificationGroup, Severity } from '@rotki/common';
import { isCancel } from 'axios';
import { type AssetSearchParams, useAssetInfoApi } from '@/composables/api/assets/info';
import { useSupportedChains } from '@/composables/info/chains';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { type AssetsWithId, CUSTOM_ASSET } from '@/types/asset';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';

export interface AssetResolutionOptions {
  associate?: boolean;
  collectionParent?: boolean;
}

interface AssetWithResolutionStatus extends AssetInfo {
  resolved: boolean;
};

export type AssetInfoReturn = (identifier: MaybeRef<string | undefined>, options?: MaybeRef<AssetResolutionOptions>) => ComputedRef<AssetWithResolutionStatus | null>;

export type AssetSymbolReturn = (identifier: MaybeRef<string | undefined>, options?: MaybeRef<AssetResolutionOptions>) => ComputedRef<string>;

export type AssetNameReturn = (identifier: MaybeRef<string | undefined>, options?: MaybeRef<AssetResolutionOptions>) => ComputedRef<string>;

interface UseAssetInfoRetrievalReturn {
  assetAssociationMap: ComputedRef<Record<string, string>>;
  fetchTokenDetails: (payload: EvmChainAddress) => Promise<ERC20Token>;
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>;
  assetInfo: AssetInfoReturn;
  refetchAssetInfo: (key: string) => void;
  assetSymbol: AssetSymbolReturn;
  assetName: AssetNameReturn;
  getAssetSymbol: (identifier: string | undefined, options?: AssetResolutionOptions) => string;
  tokenAddress: (identifier: MaybeRef<string>, enableAssociation?: MaybeRef<boolean>) => ComputedRef<string>;
  assetSearch: (params: AssetSearchParams) => Promise<AssetsWithId>;
}

export function useAssetInfoRetrieval(): UseAssetInfoRetrievalReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { assetSearch: assetSearchCaller, erc20details } = useAssetInfoApi();
  const { queueIdentifier, retrieve } = useAssetCacheStore();
  const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());
  const { notify } = useNotificationsStore();
  const { awaitTask } = useTaskStore();

  const { getChain } = useSupportedChains();

  const assetAssociationMap = computed<Record<string, string>>(() => {
    const associationMap: Record<string, string> = {};
    if (get(treatEth2AsEth))
      associationMap.ETH2 = 'ETH';

    return associationMap;
  });

  const getAssociatedAssetIdentifier = (identifier: string): ComputedRef<string> =>
    computed(() => get(assetAssociationMap)[identifier] ?? identifier);

  const getAssetNameFallback = (id: string): string => {
    if (isEvmIdentifier(id)) {
      const address = getAddressFromEvmIdentifier(id);
      return `EVM Token: ${address}`;
    }
    return '';
  };

  const assetInfo = (
    identifier: MaybeRef<string | undefined>,
    options: MaybeRef<AssetResolutionOptions> = {},
  ): ComputedRef<(AssetInfo & { resolved: boolean }) | null> => computed(() => {
    const id = get(identifier);
    if (!id)
      return null;

    const {
      associate = true,
      collectionParent = true,
    } = get(options);

    const key = associate ? get(getAssociatedAssetIdentifier(id)) : id;
    const data = get(retrieve(key));

    const isCustomAsset = data?.isCustomAsset || data?.assetType === CUSTOM_ASSET;

    if (isCustomAsset) {
      return {
        ...data,
        isCustomAsset,
        resolved: !!data,
        symbol: data.name,
      };
    }
    const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());
    const collectionData = collectionParent && data?.collectionId
      ? get(fetchedAssetCollections)[data.collectionId]
      : null;

    const fallback = getAssetNameFallback(id);
    const name = collectionData?.name || data?.name || fallback;
    const symbol = collectionData?.symbol || data?.symbol || fallback;

    return {
      ...data,
      isCustomAsset,
      name,
      resolved: !!data,
      symbol,
    };
  });

  const assetSymbol = (
    identifier: MaybeRef<string | undefined>,
    options?: MaybeRef<AssetResolutionOptions>,
  ): ComputedRef<string> => computed(() => {
    const id = get(identifier);
    if (!id)
      return '';

    const symbol = get(assetInfo(id, options))?.symbol;
    return symbol || '';
  });

  const getAssetSymbol = (identifier: string | undefined, options?: AssetResolutionOptions): string => {
    if (!identifier)
      return '';
    return get(assetInfo(identifier, options))?.symbol ?? '';
  };

  const assetName = (
    identifier: MaybeRef<string | undefined>,
    options?: MaybeRef<AssetResolutionOptions>,
  ): ComputedRef<string> => computed(() => {
    const id = get(identifier);
    if (!id)
      return '';

    const name = get(assetInfo(id, options))?.name;
    return name || '';
  });

  const tokenAddress = (
    identifier: MaybeRef<string>,
    enableAssociation: MaybeRef<boolean> = true,
  ): ComputedRef<string> =>
    computed(() => {
      const id = get(identifier);
      if (!id)
        return '';

      const key = get(enableAssociation) ? get(getAssociatedAssetIdentifier(id)) : id;
      return getAddressFromEvmIdentifier(key);
    });

  const fetchTokenDetails = async (payload: EvmChainAddress): Promise<ERC20Token> => {
    try {
      const taskType = TaskType.ERC20_DETAILS;
      const { taskId } = await erc20details(payload);
      const { result } = await awaitTask<ERC20Token, TaskMeta>(taskId, taskType, {
        title: t('actions.assets.erc20.task.title', payload),
      });
      return result;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.assets.erc20.error.description', {
            message: error.message,
          }),
          title: t('actions.assets.erc20.error.title', payload),
        });
      }
      return {};
    }
  };

  const assetSearch = async (params: AssetSearchParams): Promise<AssetsWithId> => {
    try {
      const evmChain = params.evmChain && getChain(params.evmChain) ? params.evmChain : undefined;
      return await assetSearchCaller({ ...params, evmChain });
    }
    catch (error: any) {
      if (isCancel(error))
        return [];

      notify({
        display: true,
        group: NotificationGroup.ASSET_SEARCH_ERROR,
        message: t('asset_search.error.message', {
          message: error.message,
        }),
        severity: Severity.ERROR,
        title: t('asset_search.error.title'),
      });
      return [];
    }
  };

  return {
    assetAssociationMap,
    assetInfo,
    assetName,
    assetSearch,
    assetSymbol,
    fetchTokenDetails,
    getAssetSymbol,
    getAssociatedAssetIdentifier,
    refetchAssetInfo: queueIdentifier,
    tokenAddress,
  };
}
