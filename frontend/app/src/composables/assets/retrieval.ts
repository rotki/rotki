import { type AssetInfo, NotificationGroup, Severity } from '@rotki/common';
import { isCancel } from 'axios';
import { type AssetsWithId, CUSTOM_ASSET } from '@/types/asset';
import { TaskType } from '@/types/task-type';
import type { MaybeRef } from '@vueuse/core';
import type { ERC20Token } from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import type { EvmChainAddress } from '@/types/history/events';
import type { AssetSearchParams } from '@/composables/api/assets/info';

export interface AssetResolutionOptions {
  associate?: boolean;
  collectionParent?: boolean;
}

interface AssetWithResolutionStatus extends AssetInfo {
  resolved: boolean;
};

interface UseAssetInfoRetrievalReturn {
  fetchTokenDetails: (payload: EvmChainAddress) => Promise<ERC20Token>;
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>;
  getAssetAssociationIdentifiers: (identifier: string) => string[];
  assetInfo: (identifier: MaybeRef<string | undefined>, options?: MaybeRef<AssetResolutionOptions>) => ComputedRef<AssetWithResolutionStatus | null>;
  refetchAssetInfo: (key: string) => void;
  assetSymbol: (identifier: MaybeRef<string | undefined>, enableAssociation?: MaybeRef<boolean>) => ComputedRef<string>;
  assetName: (identifier: MaybeRef<string | undefined>, enableAssociation?: MaybeRef<boolean>) => ComputedRef<string>;
  tokenAddress: (identifier: MaybeRef<string>, enableAssociation?: MaybeRef<boolean>) => ComputedRef<string>;
  assetSearch: (params: AssetSearchParams) => Promise<AssetsWithId>;
}

export function useAssetInfoRetrieval(): UseAssetInfoRetrievalReturn {
  const { t } = useI18n();
  const { erc20details, assetSearch: assetSearchCaller } = useAssetInfoApi();
  const { retrieve, queueIdentifier } = useAssetCacheStore();
  const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());
  const { notify } = useNotificationsStore();
  const { awaitTask } = useTaskStore();

  const { isEvm } = useSupportedChains();

  const assetAssociationMap = computed<Record<string, string>>(() => {
    const associationMap: Record<string, string> = {};
    if (get(treatEth2AsEth))
      associationMap.ETH2 = 'ETH';

    return associationMap;
  });

  const getAssociatedAssetIdentifier = (identifier: string): ComputedRef<string> =>
    computed(() => get(assetAssociationMap)[identifier] ?? identifier);

  const getAssetAssociationIdentifiers = (identifier: string): string[] => {
    const assets = [identifier];

    Object.entries(get(assetAssociationMap)).forEach(([key, item]) => {
      if (item !== identifier)
        return;

      assets.push(key);
    });

    return assets;
  };

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
        symbol: data.name,
        isCustomAsset,
        resolved: !!data,
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
      symbol,
      resolved: !!data,
    };
  });

  const assetSymbol = (
    identifier: MaybeRef<string | undefined>,
    enableAssociation: MaybeRef<boolean> = true,
  ): ComputedRef<string> => computed(() => {
    const id = get(identifier);
    if (!id)
      return '';

    const symbol = get(assetInfo(id, { associate: get(enableAssociation) }))?.symbol;
    return symbol || '';
  });

  const assetName = (
    identifier: MaybeRef<string | undefined>,
    enableAssociation: MaybeRef<boolean> = true,
  ): ComputedRef<string> => computed(() => {
    const id = get(identifier);
    if (!id)
      return '';

    const name = get(assetInfo(id, { associate: get(enableAssociation) }))?.name;
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
          title: t('actions.assets.erc20.error.title', payload),
          message: t('actions.assets.erc20.error.description', {
            message: error.message,
          }),
          display: true,
        });
      }
      return {};
    }
  };

  const assetSearch = async (params: AssetSearchParams): Promise<AssetsWithId> => {
    try {
      const evmChain = params.evmChain && get(isEvm(params.evmChain)) ? params.evmChain : undefined;
      return await assetSearchCaller({ ...params, evmChain });
    }
    catch (error: any) {
      if (isCancel(error))
        return [];

      notify({
        title: t('asset_search.error.title'),
        message: t('asset_search.error.message', {
          message: error.message,
        }),
        severity: Severity.ERROR,
        display: true,
        group: NotificationGroup.ASSET_SEARCH_ERROR,
      });
      return [];
    }
  };

  return {
    fetchTokenDetails,
    getAssociatedAssetIdentifier,
    getAssetAssociationIdentifiers,
    assetInfo,
    refetchAssetInfo: queueIdentifier,
    assetSymbol,
    assetName,
    tokenAddress,
    assetSearch,
  };
}
