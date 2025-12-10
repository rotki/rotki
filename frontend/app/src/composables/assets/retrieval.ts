import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import type { ERC20Token } from '@/types/blockchain/accounts';
import type { EvmChainAddress } from '@/types/history/events';
import type { TaskMeta } from '@/types/task';
import {
  type AssetInfoWithId,
  getAddressFromEvmIdentifier,
  getAddressFromSolanaIdentifier,
  getNftAssetIdDetail,
  isEvmIdentifier,
  isEvmIdentifierWithNftId,
  isSolanaTokenIdentifier,
  NotificationGroup,
  Severity,
} from '@rotki/common';
import { type AssetSearchParams, useAssetInfoApi } from '@/composables/api/assets/info';
import { getAssociatedAssetIdentifier, processAssetInfo, useAssetAssociationMap } from '@/composables/assets/common';
import { useSupportedChains } from '@/composables/info/chains';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { type AssetsWithId, EVM_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/types/asset';
import { TaskType } from '@/types/task-type';
import { isAbortError, isTaskCancelled } from '@/utils';

export interface AssetResolutionOptions {
  associate?: boolean;
  collectionParent?: boolean;
}

interface AssetWithResolutionStatus extends AssetInfoWithId {
  resolved: boolean;
}

interface AssetContractInfo {
  location: string;
  address: string;
  nftId?: string;
}

export type AssetInfoReturn = (identifier: MaybeRef<string | undefined>, options?: MaybeRef<AssetResolutionOptions>) => ComputedRef<AssetWithResolutionStatus | null>;

export type AssetSymbolReturn = (identifier: MaybeRef<string | undefined>, options?: MaybeRef<AssetResolutionOptions>) => ComputedRef<string>;

export type AssetNameReturn = (identifier: MaybeRef<string | undefined>, options?: MaybeRef<AssetResolutionOptions>) => ComputedRef<string>;

type AssetContractInfoReturn = (identifier: MaybeRef<string | undefined>, options?: MaybeRef<AssetResolutionOptions>) => ComputedRef<AssetContractInfo | undefined>;

interface UseAssetInfoRetrievalReturn {
  assetAssociationMap: ComputedRef<Record<string, string>>;
  assetContractInfo: AssetContractInfoReturn;
  assetInfo: AssetInfoReturn;
  assetName: AssetNameReturn;
  assetSearch: (params: AssetSearchParams) => Promise<AssetsWithId>;
  assetSymbol: AssetSymbolReturn;
  fetchTokenDetails: (payload: EvmChainAddress) => Promise<ERC20Token>;
  getAssetSymbol: (identifier: string | undefined, options?: AssetResolutionOptions) => string;
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>;
  refetchAssetInfo: (key: string) => void;
  tokenAddress: (identifier: MaybeRef<string>, options?: AssetResolutionOptions) => ComputedRef<string>;
}

export function useAssetInfoRetrieval(): UseAssetInfoRetrievalReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { assetSearch: assetSearchCaller, erc20details } = useAssetInfoApi();
  const { queueIdentifier, retrieve } = useAssetCacheStore();
  const { notify } = useNotificationsStore();
  const { awaitTask } = useTaskStore();

  const { getChain } = useSupportedChains();

  const assetAssociationMap = useAssetAssociationMap();

  const getAssociatedAssetIdentifierComputed = (identifier: string): ComputedRef<string> =>
    computed(() => getAssociatedAssetIdentifier(identifier, get(assetAssociationMap)));

  const assetInfo = (
    identifier: MaybeRef<string | undefined>,
    options: MaybeRef<AssetResolutionOptions> = {},
  ): ComputedRef<(AssetInfoWithId & { resolved: boolean }) | null> => computed(() => {
    const id = get(identifier);
    if (!id)
      return null;

    const {
      associate = true,
      collectionParent = true,
    } = get(options);

    const key = associate ? get(getAssociatedAssetIdentifierComputed(id)) : id;
    const data = get(retrieve(key));

    const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());
    const collectionData = collectionParent && data?.collectionId
      ? get(fetchedAssetCollections)[data.collectionId]
      : null;

    const processedInfo = processAssetInfo(data, id, collectionData);

    if (!processedInfo) {
      return null;
    }

    return {
      ...processedInfo,
      identifier: key,
      resolved: !!data,
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

  const assetContractInfo = (
    identifier: MaybeRef<string | undefined>,
    options?: MaybeRef<AssetResolutionOptions>,
  ): ComputedRef<AssetContractInfo | undefined> => computed(() => {
    const id = get(identifier);
    if (!id)
      return undefined;

    const asset = get(assetInfo(id, options));

    if (!asset)
      return undefined;

    const { assetType, identifier: usedId } = asset;

    if (assetType === EVM_TOKEN) {
      const location = asset.evmChain ?? undefined;
      if (isEvmIdentifier(usedId)) {
        return {
          address: getAddressFromEvmIdentifier(usedId),
          location,
        };
      }

      if (isEvmIdentifierWithNftId(usedId)) {
        const nftDetail = getNftAssetIdDetail(usedId);
        if (!nftDetail) {
          return undefined;
        }
        return {
          address: nftDetail.contractAddress,
          location,
          nftId: nftDetail.nftId,
        };
      }
    }

    if (isSolanaTokenIdentifier(usedId) && assetType === SOLANA_TOKEN) {
      return {
        address: getAddressFromSolanaIdentifier(usedId),
        location: SOLANA_CHAIN,
      };
    }

    return undefined;
  });

  const tokenAddress = (
    identifier: MaybeRef<string>,
    options?: MaybeRef<AssetResolutionOptions>,
  ): ComputedRef<string> =>
    computed(() => get(assetContractInfo(identifier, options))?.address || '');

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
      if (isAbortError(error))
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
    assetContractInfo,
    assetInfo,
    assetName,
    assetSearch,
    assetSymbol,
    fetchTokenDetails,
    getAssetSymbol,
    getAssociatedAssetIdentifier: getAssociatedAssetIdentifierComputed,
    refetchAssetInfo: queueIdentifier,
    tokenAddress,
  };
}
