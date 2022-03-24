import { AssetBalanceWithPrice } from '@rotki/common';
import { SupportedAsset } from '@rotki/common/lib/data';
import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { AssetUpdatePayload } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { SupportedAssets } from '@/services/types-api';
import { convertSupportedAssets } from '@/store/assets/utils';
import { AssetPriceInfo } from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { showMessage, useStore } from '@/store/utils';
import {
  ApplyUpdateResult,
  AssetDBVersion,
  AssetMergePayload,
  AssetUpdateCheckResult,
  AssetUpdateResult
} from '@/types/assets';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';

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
    const isLocal = interop.isPackaged && api.defaultBackend;
    try {
      await api.assets.importCustom(file, !isLocal);
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
      const isLocal = interop.isPackaged && api.defaultBackend;
      let file: string | undefined = undefined;
      if (isLocal) {
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
    const store = useStore();
    const supportedAssets = ref<SupportedAsset[]>([]);
    const supportedAssetsMap = ref<SupportedAssets>({});

    const fetchSupportedAssets = async (refresh: boolean = false) => {
      set(supportedAssets, []);
      if (get(supportedAssets).length > 0 && !refresh) {
        return;
      }
      try {
        const assets = await api.assets.allAssets();
        set(supportedAssetsMap, assets);
        set(supportedAssets, convertSupportedAssets(assets));
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

    const assetInfo = (identifier: string) => {
      return computed<SupportedAsset | undefined>(() => {
        if (!identifier) return undefined;

        if (identifier.startsWith('_nft_')) {
          const nonFungibleBalances = store.state.balances!.nonFungibleBalances;

          for (const address in nonFungibleBalances) {
            const nfb = nonFungibleBalances[address];
            for (const balance of nfb) {
              if (balance.id === identifier) {
                return {
                  identifier: balance.id,
                  symbol: balance.name,
                  name: balance.name,
                  assetType: 'ethereum_token'
                } as SupportedAsset;
              }
            }
          }
        }

        const asset = get(supportedAssetsMap)[identifier];

        if (!asset) {
          return undefined;
        }

        return {
          ...asset,
          identifier
        };
      });
    };

    const assetSymbol = (identifier: string) => {
      return computed<string>(() => {
        if (!identifier) return '';

        const symbol = get(assetInfo(identifier))?.symbol;

        if (symbol) return symbol;

        if (identifier.startsWith('_ceth_')) {
          const address = identifier.slice(6);
          return `Ethereum Token: ${address}`;
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

    const assetName = (identifier: string) => {
      return computed<string>(() => {
        if (!identifier) return '';

        const name = get(assetInfo(identifier))?.name;
        if (name) return name;

        if (identifier.startsWith('_ceth_')) {
          const address = identifier.slice(5);
          return `Ethereum Token: ${address}`;
        }

        return '';
      });
    };

    const tokenAddress = (identifier: string) => {
      return computed<string>(() => {
        if (!identifier) return '';
        return get(assetInfo(identifier))?.ethereumAddress ?? '';
      });
    };

    const assetPriceInfo = (identifier: string) => {
      return computed<AssetPriceInfo>(() => {
        const assetValue = store.getters['balances/aggregatedBalances'].find(
          (value: AssetBalanceWithPrice) => value.asset === identifier
        );
        return {
          usdPrice: store.state.balances!.prices[identifier] ?? Zero,
          amount: assetValue?.amount ?? Zero,
          usdValue: assetValue?.usdValue ?? Zero
        };
      });
    };

    return {
      supportedAssets,
      supportedAssetsMap,
      fetchSupportedAssets,
      assetInfo,
      assetSymbol,
      assetIdentifierForSymbol,
      assetName,
      tokenAddress,
      assetPriceInfo,
      getAssetInfo: (identifier: string) => get(assetInfo(identifier)),
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
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
  };

  const ignoreAsset = async (asset: string): Promise<ActionStatus> => {
    try {
      const ignored = await api.assets.modifyAsset(true, asset);
      set(ignoredAssets, ignored);
      return { success: true };
    } catch (e: any) {
      return { success: false, message: e.message };
    }
  };

  const unignoreAsset = async (asset: string): Promise<ActionStatus> => {
    try {
      const ignored = await api.assets.modifyAsset(false, asset);
      set(ignoredAssets, ignored);
      return { success: true };
    } catch (e: any) {
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
