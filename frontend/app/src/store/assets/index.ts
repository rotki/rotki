import { AssetBalanceWithPrice } from '@rotki/common';
import { SupportedAsset } from '@rotki/common/lib/data';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { computed, ref } from 'vue';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { EVM_TOKEN } from '@/services/assets/consts';
import { AssetUpdatePayload } from '@/services/assets/types';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { SupportedAssets } from '@/services/types-api';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import {
  AssetPriceInfo,
  ERC20Token,
  NonFungibleBalance
} from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { showMessage } from '@/store/utils';
import {
  ApplyUpdateResult,
  AssetDBVersion,
  AssetMergePayload,
  AssetUpdateCheckResult,
  AssetUpdateResult
} from '@/types/assets';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { getAddressFromEvmIdentifier, isEvmIdentifier } from '@/utils/assets';
import { Zero } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';
import { getNftBalance, isNft } from '@/utils/nft';

export const useAssets = defineStore('assets', () => {
  const { awaitTask } = useTasks();

  const checkForUpdate = async (): Promise<AssetUpdateCheckResult> => {
    try {
      const taskType = TaskType.ASSET_UPDATE;
      const { taskId } = await api.assets.checkForAssetUpdate();
      const { result } = await awaitTask<AssetDBVersion, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.t('actions.assets.versions.task.title').toString(),
          numericKeys: []
        }
      );

      return {
        updateAvailable: result.local < result.remote,
        versions: result
      };
    } catch (e: any) {
      const title = i18n.t('actions.assets.versions.task.title').toString();
      const description = i18n
        .t('actions.assets.versions.error.description', { message: e.message })
        .toString();
      const { notify } = useNotifications();
      notify({
        title,
        message: description,
        display: true
      });
      return {
        updateAvailable: false
      };
    }
  };

  const applyUpdates = async ({
    version,
    resolution
  }: AssetUpdatePayload): Promise<ApplyUpdateResult> => {
    try {
      const { taskId } = await api.assets.performUpdate(version, resolution);
      const { result } = await awaitTask<AssetUpdateResult, TaskMeta>(
        taskId,
        TaskType.ASSET_UPDATE_PERFORM,
        {
          title: i18n.t('actions.assets.update.task.title').toString(),
          numericKeys: []
        }
      );

      if (typeof result === 'boolean') {
        return {
          done: true
        };
      }
      return {
        done: false,
        conflicts: result
      };
    } catch (e: any) {
      const title = i18n.t('actions.assets.update.task.title').toString();
      const description = i18n
        .t('actions.assets.update.error.description', { message: e.message })
        .toString();
      const { notify } = useNotifications();
      notify({
        title,
        message: description,
        display: true
      });
      return {
        done: false
      };
    }
  };

  const mergeAssets = async ({
    sourceIdentifier,
    targetIdentifier
  }: AssetMergePayload): Promise<ActionStatus> => {
    try {
      const success = await api.assets.mergeAssets(
        sourceIdentifier,
        targetIdentifier
      );
      return {
        success
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  const importCustomAssets = async (file: File): Promise<ActionStatus> => {
    try {
      await api.assets.importCustom(file, !interop.appSession);
      return {
        success: true
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  const exportCustomAssets = async (): Promise<ActionStatus> => {
    try {
      let file: string | undefined = undefined;
      if (interop.appSession) {
        const directory = await interop.openDirectory(
          i18n.t('profit_loss_report.select_directory').toString()
        );
        if (!directory) {
          return {
            success: false,
            message: i18n.t('assets.backup.missing_directory').toString()
          };
        }
        file = directory;
      }
      return await api.assets.exportCustom(file);
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  return {
    checkForUpdate,
    applyUpdates,
    mergeAssets,
    importCustomAssets,
    exportCustomAssets
  };
});

export const useAssetInfoRetrieval = defineStore(
  'assets/infoRetrievals',
  () => {
    const supportedAssetsMap = ref<SupportedAssets>({});

    const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());

    const assetAssociationMap = computed<{ [key: string]: string }>(() => {
      const associationMap: { [key: string]: string } = {};
      if (get(treatEth2AsEth)) {
        associationMap['ETH2'] = 'ETH';
      }
      return associationMap;
    });

    const getAssociatedAssetIdentifier = (identifier: string) =>
      computed<string>(() => {
        return get(assetAssociationMap)[identifier] ?? identifier;
      });

    const getAssociatedAsset = (identifier: string) =>
      computed(() => {
        const associatedIdentifier = get(
          getAssociatedAssetIdentifier(identifier)
        );
        return get(supportedAssetsMap)[associatedIdentifier];
      });

    const supportedAssets = computed<SupportedAsset[]>(() => {
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

    const allSupportedAssets = computed<SupportedAsset[]>(() => {
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

    const fetchSupportedAssets = async (refresh: boolean = false) => {
      if (get(supportedAssets).length > 0 && !refresh) {
        return;
      }
      try {
        const assets = await api.assets.allAssets();
        set(supportedAssetsMap, assets);
      } catch (e: any) {
        const { notify } = useNotifications();
        notify({
          title: i18n
            .t('actions.balances.supported_assets.error.title')
            .toString(),
          message: i18n
            .t('actions.balances.supported_assets.error.message', {
              message: e.message
            })
            .toString(),
          display: true
        });
      }
    };

    const assetInfo = (
      identifier: string,
      enableAssociation: boolean = true
    ) => {
      return computed<SupportedAsset | undefined>(() => {
        if (!identifier) return undefined;

        if (isNft(identifier)) {
          const nftBalance: NonFungibleBalance | null =
            getNftBalance(identifier);

          if (nftBalance) {
            return {
              identifier: nftBalance.id,
              symbol: nftBalance.name,
              name: nftBalance.name,
              assetType: 'ethereum_token'
            } as SupportedAsset;
          }
        }

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
    };

    const assetSymbol = (
      identifier: string,
      enableAssociation: boolean = true
    ) => {
      return computed<string>(() => {
        if (!identifier) return '';

        const symbol = get(assetInfo(identifier, enableAssociation))?.symbol;

        if (symbol) return symbol;

        if (isEvmIdentifier(identifier)) {
          const address = getAddressFromEvmIdentifier(identifier);
          return `EVM Token: ${address}`;
        }

        return '';
      });
    };

    const assetIdentifierForSymbol = (symbol: string) => {
      return computed<string>(() => {
        if (!symbol) return '';
        return (
          get(supportedAssets).find(asset => asset.symbol === symbol)
            ?.identifier ?? ''
        );
      });
    };

    const assetName = (
      identifier: string,
      enableAssociation: boolean = true
    ) => {
      return computed<string>(() => {
        if (!identifier) return '';

        const name = get(assetInfo(identifier, enableAssociation))?.name;
        if (name) return name;

        if (isEvmIdentifier(identifier)) {
          const address = getAddressFromEvmIdentifier(identifier);
          return `EVM Token: ${address}`;
        }

        return '';
      });
    };

    const tokenAddress = (
      identifier: string,
      enableAssociation: boolean = true
    ) => {
      return computed<string>(() => {
        if (!identifier) return '';
        return get(assetInfo(identifier, enableAssociation))?.evmAddress ?? '';
      });
    };

    const assetPriceInfo = (identifier: string) => {
      return computed<AssetPriceInfo>(() => {
        const { aggregatedBalances } = useBlockchainBalancesStore();
        const assetValue = (
          get(aggregatedBalances()) as AssetBalanceWithPrice[]
        ).find((value: AssetBalanceWithPrice) => value.asset === identifier);
        return {
          usdPrice: assetValue?.usdPrice ?? Zero,
          amount: assetValue?.amount ?? Zero,
          usdValue: assetValue?.usdValue ?? Zero
        };
      });
    };

    const supportedAssetsSymbol = computed<string[]>(() => {
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
            title: i18n
              .t('actions.assets.erc20.task.title', { address })
              .toString(),
            numericKeys: balanceKeys
          }
        );
        return result;
      } catch (e: any) {
        const { notify } = useNotifications();
        notify({
          title: i18n
            .t('actions.assets.erc20.error.title', { address })
            .toString(),
          message: i18n
            .t('actions.assets.erc20.error.description', {
              message: e.message
            })
            .toString(),
          display: true
        });
        return {};
      }
    };

    const isEthereumToken = (asset: string) =>
      computed<boolean>(() => {
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
      assetPriceInfo,
      getAssetInfo: (identifier: string) =>
        get(assetInfo(identifier)) as SupportedAsset | undefined,
      getAssetSymbol: (identifier: string) => get(assetSymbol(identifier)),
      getAssetIdentifierForSymbol: (symbol: string) =>
        get(assetIdentifierForSymbol(symbol)),
      getAssetName: (identifier: string) => get(assetName(identifier)),
      getTokenAddress: (identifier: string) => get(tokenAddress(identifier)),
      getAssetPriceInfo: (identifier: string) => get(assetPriceInfo(identifier))
    };
  }
);

export const useIgnoredAssetsStore = defineStore('ignoredAssets', () => {
  const ignoredAssets = ref<string[]>([]);

  const { fetchSupportedAssets } = useAssetInfoRetrieval();
  const { notify } = useNotifications();

  const fetchIgnoredAssets = async (): Promise<void> => {
    try {
      const ignored = await api.assets.ignoredAssets();
      set(ignoredAssets, ignored);
    } catch (e: any) {
      const title = i18n.tc('actions.session.ignored_assets.error.title');
      const message = i18n.tc(
        'actions.session.ignored_assets.error.message',
        0,
        {
          error: e.message
        }
      );
      notify({
        title,
        message,
        display: true
      });
    }
  };

  const ignoreAsset = async (
    assets: string[] | string
  ): Promise<ActionStatus> => {
    try {
      const ignored = await api.assets.modifyAsset(
        true,
        Array.isArray(assets) ? assets : [assets]
      );
      set(ignoredAssets, ignored);
      return { success: true };
    } catch (e: any) {
      notify({
        title: i18n.t('ignore.failed.ignore_title').toString(),
        message: i18n
          .t('ignore.failed.ignore_message', {
            length: Array.isArray(assets) ? assets.length : 1,
            message: e.message
          })
          .toString(),
        display: true
      });
      return { success: false, message: e.message };
    }
  };

  const unignoreAsset = async (
    assets: string[] | string
  ): Promise<ActionStatus> => {
    try {
      const ignored = await api.assets.modifyAsset(
        false,
        Array.isArray(assets) ? assets : [assets]
      );
      set(ignoredAssets, ignored);
      return { success: true };
    } catch (e: any) {
      notify({
        title: i18n.t('ignore.failed.unignore_title').toString(),
        message: i18n
          .t('ignore.failed.unignore_message', {
            length: Array.isArray(assets) ? assets.length : 1,
            message: e.message
          })
          .toString(),
        display: true
      });
      return { success: false, message: e.message };
    }
  };

  const updateIgnoredAssets = async (): Promise<void> => {
    const { awaitTask } = useTasks();

    try {
      const taskType = TaskType.UPDATE_IGNORED_ASSETS;
      const { taskId } = await api.assets.updateIgnoredAssets();
      const taskMeta = {
        title: i18n
          .t('actions.session.update_ignored_assets.task.title')
          .toString(),
        numericKeys: []
      };

      const { result } = await awaitTask<number, TaskMeta>(
        taskId,
        taskType,
        taskMeta
      );

      const title = i18n
        .t('actions.session.update_ignored_assets.success.title')
        .toString();
      const message =
        result > 0
          ? i18n
              .t('actions.session.update_ignored_assets.success.message', {
                total: result
              })
              .toString()
          : i18n
              .t(
                'actions.session.update_ignored_assets.success.empty_message',
                { total: result }
              )
              .toString();

      showMessage(message, title);
      await fetchIgnoredAssets();
      await fetchSupportedAssets();
    } catch (e: any) {
      const title = i18n.tc(
        'actions.session.update_ignored_assets.error.title'
      );
      const message = i18n.tc(
        'actions.session.update_ignored_assets.error.message',
        0,
        {
          error: e.message
        }
      );
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
  };

  const isAssetIgnored = (asset: string) =>
    computed<boolean>(() => {
      return get(ignoredAssets).includes(asset);
    });

  return {
    ignoredAssets,
    fetchIgnoredAssets,
    ignoreAsset,
    unignoreAsset,
    updateIgnoredAssets,
    isAssetIgnored
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAssets, import.meta.hot));
  import.meta.hot.accept(
    acceptHMRUpdate(useAssetInfoRetrieval, import.meta.hot)
  );
  import.meta.hot.accept(
    acceptHMRUpdate(useIgnoredAssetsStore, import.meta.hot)
  );
}
