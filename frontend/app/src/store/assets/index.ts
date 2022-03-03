import { AssetBalanceWithPrice } from '@rotki/common';
import { SupportedAsset } from '@rotki/common/lib/data';
import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { AssetUpdatePayload } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { convertSupportedAssets } from '@/store/assets/utils';
import { AssetPriceInfo } from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { useStore } from '@/store/utils';
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
  const checkForUpdate = async (): Promise<AssetUpdateCheckResult> => {
    const { awaitTask } = useTasks();
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
      const { awaitTask } = useTasks();
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

    const fetchSupportedAssets = async (refresh: boolean = false) => {
      set(supportedAssets, []);
      if (get(supportedAssets).length > 0 && !refresh) {
        return;
      }
      try {
        const assets = await api.assets.allAssets();
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

        return get(supportedAssets).find(
          asset => asset.identifier === identifier
        );
      });
    };

    const assetSymbol = (identifier: string) => {
      return computed<string>(() => {
        if (!identifier) return '';
        return get(assetInfo(identifier))?.symbol ?? identifier;
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
        return get(assetInfo(identifier))?.name ?? '';
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

if (module.hot) {
  module.hot.accept(acceptHMRUpdate(useAssets, module.hot));
  module.hot.accept(acceptHMRUpdate(useAssetInfoRetrieval, module.hot));
}
