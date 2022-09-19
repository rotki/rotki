import { SupportedAsset } from '@rotki/common/lib/data';
import { ComputedRef, Ref } from 'vue';
import { EVM_TOKEN } from '@/services/assets/consts';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { SupportedAssets } from '@/services/types-api';
import { ERC20Token } from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { getAddressFromEvmIdentifier, isEvmIdentifier } from '@/utils/assets';
import { uniqueStrings } from '@/utils/data';

export const useAssetInfoRetrieval = defineStore(
  'assets/infoRetrievals',
  () => {
    const supportedAssetsMap: Ref<SupportedAssets> = ref({});

    const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());
    const { t } = useI18n();

    const assetAssociationMap: ComputedRef<Record<string, string>> = computed(
      () => {
        const associationMap: Record<string, string> = {};
        if (get(treatEth2AsEth)) {
          associationMap['ETH2'] = 'ETH';
        }
        return associationMap;
      }
    );

    const getAssociatedAssetIdentifier = (
      identifier: string
    ): ComputedRef<string> =>
      computed(() => {
        return get(assetAssociationMap)[identifier] ?? identifier;
      });

    const getAssociatedAsset = (identifier: string) =>
      computed(() => {
        const associatedIdentifier = get(
          getAssociatedAssetIdentifier(identifier)
        );
        return get(supportedAssetsMap)[associatedIdentifier];
      });

    const supportedAssets: ComputedRef<SupportedAsset[]> = computed(() => {
      const assets: SupportedAsset[] = [];
      const supportedAssetsMapVal = get(supportedAssetsMap);
      Object.keys(supportedAssetsMapVal).forEach(identifier => {
        if (Object.keys(get(assetAssociationMap)).includes(identifier)) return;
        assets.push({
          identifier,
          ...supportedAssetsMapVal[identifier]
        });
      });
      return assets;
    });

    const allSupportedAssets: ComputedRef<SupportedAsset[]> = computed(() => {
      const assets: SupportedAsset[] = [];
      const supportedAssetsMapVal = get(supportedAssetsMap);
      Object.keys(supportedAssetsMapVal).forEach(identifier => {
        assets.push({
          identifier,
          ...supportedAssetsMapVal[identifier]
        });
      });
      return assets;
    });

    const fetchSupportedAssets = async (
      refresh: boolean = false
    ): Promise<void> => {
      if (get(supportedAssets).length > 0 && !refresh) {
        return;
      }
      try {
        const assets = await api.assets.allAssets();
        set(supportedAssetsMap, assets);
      } catch (e: any) {
        const { notify } = useNotifications();
        notify({
          title: t('actions.balances.supported_assets.error.title').toString(),
          message: t('actions.balances.supported_assets.error.message', {
            message: e.message
          }).toString(),
          display: true
        });
      }
    };

    const assetInfo = (
      identifier: string,
      enableAssociation: boolean = true
    ): ComputedRef<SupportedAsset | undefined> =>
      computed(() => {
        if (!identifier) return undefined;

        const asset = enableAssociation
          ? get(getAssociatedAsset(identifier))
          : get(supportedAssetsMap)[identifier];

        if (!asset) {
          return undefined;
        }

        return {
          ...asset,
          identifier
        };
      });

    const assetSymbol = (
      identifier: string,
      enableAssociation: boolean = true
    ): ComputedRef<string> =>
      computed(() => {
        if (!identifier) return '';

        const symbol = get(assetInfo(identifier, enableAssociation))?.symbol;

        if (symbol) return symbol;

        if (isEvmIdentifier(identifier)) {
          const address = getAddressFromEvmIdentifier(identifier);
          return `EVM Token: ${address}`;
        }

        return '';
      });

    const assetIdentifierForSymbol = (symbol: string): ComputedRef<string> =>
      computed(() => {
        if (!symbol) return '';
        return (
          get(supportedAssets).find(asset => asset.symbol === symbol)
            ?.identifier ?? ''
        );
      });

    const assetName = (
      identifier: string,
      enableAssociation: boolean = true
    ): ComputedRef<string> =>
      computed(() => {
        if (!identifier) return '';

        const name = get(assetInfo(identifier, enableAssociation))?.name;
        if (name) return name;

        if (isEvmIdentifier(identifier)) {
          const address = getAddressFromEvmIdentifier(identifier);
          return `EVM Token: ${address}`;
        }

        return '';
      });

    const tokenAddress = (
      identifier: string,
      enableAssociation: boolean = true
    ): ComputedRef<string> =>
      computed(() => {
        if (!identifier) return '';
        return get(assetInfo(identifier, enableAssociation))?.address ?? '';
      });

    const supportedAssetsSymbol: ComputedRef<string[]> = computed(() => {
      const data = get(supportedAssets)
        .map(value => get(assetSymbol(value.identifier)))
        .filter(uniqueStrings);

      if (get(treatEth2AsEth)) return data;
      return [...data, 'ETH2'];
    });

    const fetchTokenDetails = async (address: string): Promise<ERC20Token> => {
      const { awaitTask } = useTasks();
      try {
        const taskType = TaskType.ERC20_DETAILS;
        const { taskId } = await api.erc20details(address);
        const { result } = await awaitTask<ERC20Token, TaskMeta>(
          taskId,
          taskType,
          {
            title: t('actions.assets.erc20.task.title', { address }).toString(),
            numericKeys: balanceKeys
          }
        );
        return result;
      } catch (e: any) {
        const { notify } = useNotifications();
        notify({
          title: t('actions.assets.erc20.error.title', { address }).toString(),
          message: t('actions.assets.erc20.error.description', {
            message: e.message
          }).toString(),
          display: true
        });
        return {};
      }
    };

    const isEthereumToken = (asset: string): ComputedRef<boolean> =>
      computed(() => {
        const match = get(assetInfo(asset));
        if (match) {
          return match.assetType === EVM_TOKEN;
        }
        return false;
      });

    return {
      allSupportedAssets,
      supportedAssets,
      supportedAssetsMap,
      supportedAssetsSymbol,
      fetchTokenDetails,
      isEthereumToken,
      fetchSupportedAssets,
      getAssociatedAssetIdentifier,
      getAssociatedAsset,
      assetInfo,
      assetSymbol,
      assetIdentifierForSymbol,
      assetName,
      tokenAddress,
      getAssetInfo: (identifier: string) =>
        get(assetInfo(identifier)) as SupportedAsset | undefined,
      getAssetSymbol: (identifier: string) => get(assetSymbol(identifier)),
      getAssetIdentifierForSymbol: (symbol: string) =>
        get(assetIdentifierForSymbol(symbol)),
      getAssetName: (identifier: string) => get(assetName(identifier)),
      getTokenAddress: (identifier: string) => get(tokenAddress(identifier))
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAssetInfoRetrieval, import.meta.hot)
  );
}
