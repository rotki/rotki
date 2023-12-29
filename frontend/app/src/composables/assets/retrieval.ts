import { type MaybeRef } from '@vueuse/core';
import { type AssetInfo } from '@rotki/common/lib/data';
import { CUSTOM_ASSET } from '@/types/asset';
import { type ERC20Token } from '@/types/blockchain/accounts';
import { TaskType } from '@/types/task-type';
import { type TaskMeta } from '@/types/task';
import { type EvmChainAddress } from '@/types/history/events';

export const useAssetInfoRetrieval = () => {
  const { t } = useI18n();
  const { erc20details } = useAssetInfoApi();
  const { retrieve, isPending } = useAssetCacheStore();
  const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());
  const { notify } = useNotificationsStore();
  const { awaitTask } = useTaskStore();

  const assetAssociationMap: ComputedRef<Record<string, string>> = computed(
    () => {
      const associationMap: Record<string, string> = {};
      if (get(treatEth2AsEth)) {
        associationMap.ETH2 = 'ETH';
      }
      return associationMap;
    }
  );

  const getAssociatedAssetIdentifier = (
    identifier: string
  ): ComputedRef<string> =>
    computed(() => get(assetAssociationMap)[identifier] ?? identifier);

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
    isCollectionParent: MaybeRef<boolean> = true
  ): ComputedRef<AssetInfo | null> =>
    computed(() => {
      const id = get(identifier);
      if (!id) {
        return null;
      }

      if (get(isPending(id))) {
        return null;
      }

      const key = get(enableAssociation)
        ? get(getAssociatedAssetIdentifier(id))
        : id;

      const data = get(retrieve(key));

      const isCustomAsset =
        data?.isCustomAsset || data?.assetType === CUSTOM_ASSET;

      if (isCustomAsset) {
        return {
          ...data,
          symbol: data.name,
          isCustomAsset
        };
      }
      const { fetchedAssetCollections } = storeToRefs(useAssetCacheStore());
      const collectionData =
        get(isCollectionParent) && data?.collectionId
          ? get(fetchedAssetCollections)[data.collectionId]
          : null;

      const name =
        collectionData?.name || data?.name || getAssetNameFallback(id);
      const symbol =
        collectionData?.symbol || data?.symbol || getAssetNameFallback(id);

      return {
        ...data,
        isCustomAsset,
        name,
        symbol
      };
    });

  const assetSymbol = (
    identifier: MaybeRef<string | undefined>,
    enableAssociation: MaybeRef<boolean> = true
  ): ComputedRef<string> =>
    computed(() => {
      const id = get(identifier);
      if (!id) {
        return '';
      }

      const symbol = get(assetInfo(id, enableAssociation))?.symbol;
      if (symbol) {
        return symbol;
      }

      return '';
    });

  const assetName = (
    identifier: MaybeRef<string | undefined>,
    enableAssociation: MaybeRef<boolean> = true
  ): ComputedRef<string> =>
    computed(() => {
      const id = get(identifier);
      if (!id) {
        return '';
      }

      const name = get(assetInfo(id, enableAssociation))?.name;
      if (name) {
        return name;
      }

      return '';
    });

  const tokenAddress = (
    identifier: MaybeRef<string>,
    enableAssociation: MaybeRef<boolean> = true
  ): ComputedRef<string> =>
    computed(() => {
      const id = get(identifier);
      if (!id) {
        return '';
      }

      const key = get(enableAssociation)
        ? get(getAssociatedAssetIdentifier(id))
        : id;
      return getAddressFromEvmIdentifier(key);
    });

  const fetchTokenDetails = async (
    payload: EvmChainAddress
  ): Promise<ERC20Token> => {
    try {
      const taskType = TaskType.ERC20_DETAILS;
      const { taskId } = await erc20details(payload);
      const { result } = await awaitTask<ERC20Token, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.assets.erc20.task.title', payload)
        }
      );
      return result;
    } catch (e: any) {
      if (!isTaskCancelled(e)) {
        notify({
          title: t('actions.assets.erc20.error.title', payload),
          message: t('actions.assets.erc20.error.description', {
            message: e.message
          }),
          display: true
        });
      }
      return {};
    }
  };

  return {
    fetchTokenDetails,
    getAssociatedAssetIdentifier,
    assetInfo,
    assetSymbol,
    assetName,
    tokenAddress
  };
};
