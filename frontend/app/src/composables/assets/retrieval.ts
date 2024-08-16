import { type AssetInfo, NotificationGroup, Severity } from '@rotki/common';
import { type AssetsWithId, CUSTOM_ASSET } from '@/types/asset';
import { TaskType } from '@/types/task-type';
import type { MaybeRef } from '@vueuse/core';
import type { ERC20Token } from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import type { EvmChainAddress } from '@/types/history/events';

export function useAssetInfoRetrieval() {
  const { t } = useI18n();
  const { erc20details, assetSearch: assetSearchCaller } = useAssetInfoApi();
  const { retrieve, queueIdentifier } = useAssetCacheStore();
  const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());
  const { notify } = useNotificationsStore();
  const { awaitTask } = useTaskStore();

  const assetAssociationMap = computed<Record<string, string>>(() => {
    const associationMap: Record<string, string> = {};
    if (get(treatEth2AsEth))
      associationMap.ETH2 = 'ETH';

    return associationMap;
  });

  const getAssociatedAssetIdentifier = (identifier: string): ComputedRef<string> =>
    computed(() => get(assetAssociationMap)[identifier] ?? identifier);

  const getAssetAssociationIdentifiers = (
    identifier: string,
  ): ComputedRef<string[]> => computed(() => {
    const assets = [identifier];

    Object.entries(get(assetAssociationMap)).forEach(([key, item]) => {
      if (item !== identifier)
        return;

      assets.push(key);
    });

    return assets;
  });

  const getAssetNameFallback = (id: string) => {
    if (isEvmIdentifier(id)) {
      const address = getAddressFromEvmIdentifier(id);
      return `EVM Token: ${address}`;
    }
    return '';
  };

  const assetInfo = (
    identifier: MaybeRef<string | undefined>,
    enableAssociation: MaybeRef<boolean> = true,
    isCollectionParent: MaybeRef<boolean> = true,
  ): ComputedRef<AssetInfo | null> =>
    computed(() => {
      const id = get(identifier);
      if (!id)
        return null;

      const key = get(enableAssociation) ? get(getAssociatedAssetIdentifier(id)) : id;

      const data = get(retrieve(key));

      const isCustomAsset = data?.isCustomAsset || data?.assetType === CUSTOM_ASSET;

      if (isCustomAsset) {
        return {
          ...data,
          symbol: data.name,
          isCustomAsset,
        };
      }
      const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());
      const collectionData
        = get(isCollectionParent) && data?.collectionId ? get(fetchedAssetCollections)[data.collectionId] : null;

      const name = collectionData?.name || data?.name || getAssetNameFallback(id);
      const symbol = collectionData?.symbol || data?.symbol || getAssetNameFallback(id);

      return {
        ...data,
        isCustomAsset,
        name,
        symbol,
      };
    });

  const assetSymbol = (
    identifier: MaybeRef<string | undefined>,
    enableAssociation: MaybeRef<boolean> = true,
  ): ComputedRef<string> =>
    computed(() => {
      const id = get(identifier);
      if (!id)
        return '';

      const symbol = get(assetInfo(id, enableAssociation))?.symbol;
      if (symbol)
        return symbol;

      return '';
    });

  const assetName = (
    identifier: MaybeRef<string | undefined>,
    enableAssociation: MaybeRef<boolean> = true,
  ): ComputedRef<string> =>
    computed(() => {
      const id = get(identifier);
      if (!id)
        return '';

      const name = get(assetInfo(id, enableAssociation))?.name;
      if (name)
        return name;

      return '';
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

  const assetSearch = async (
    keyword: string,
    limit = 25,
    searchNfts = false,
    signal?: AbortSignal,
  ): Promise<AssetsWithId> => {
    try {
      return await assetSearchCaller(keyword, limit, searchNfts, signal);
    }
    catch (error: any) {
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
