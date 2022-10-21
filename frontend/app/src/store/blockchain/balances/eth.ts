import { AssetBalance } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { MaybeRef } from '@vueuse/core';
import isEmpty from 'lodash/isEmpty';
import { ComputedRef, Ref } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainBalanceApi } from '@/services/balances/blockchain';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { AccountAssetBalances, AssetBalances } from '@/types/balances';
import {
  BlockchainAssetBalances,
  BlockchainBalances
} from '@/types/blockchain/balances';
import { EthChains, isEthChain } from '@/types/blockchain/chains';
import { Module } from '@/types/modules';
import { AssetPrices } from '@/types/prices';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { removeZeroAssets, toSortedAssetBalanceArray } from '@/utils/balances';
import { balanceSum } from '@/utils/calculation';
import {
  updateAssetBalances,
  updateBlockchainAssetBalances,
  updateTotalsPrices
} from '@/utils/prices';

type Totals = Record<EthChains, AssetBalances>;
type Balances = Record<EthChains, BlockchainAssetBalances>;

const defaultTotals = (): Totals => ({
  ETH: {},
  ETH2: {}
});

const defaultBalances = (): Balances => ({
  ETH: {},
  ETH2: {}
});

export const useEthBalancesStore = defineStore('balances/eth', () => {
  const loopring: Ref<AccountAssetBalances> = ref({});

  const balances: Ref<Balances> = ref(defaultBalances());
  const totals: Ref<Totals> = ref(defaultTotals());
  const liabilities: Ref<Totals> = ref(defaultTotals());

  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const { awaitTask } = useTasks();
  const { notify } = useNotifications();
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { queryLoopringBalances } = useBlockchainBalanceApi();
  const { tc } = useI18n();

  const ethAddresses: ComputedRef<string[]> = computed(() => {
    const { ETH } = get(balances);
    return ETH ? Object.keys(ETH) : [];
  });

  const getLoopringAssetBalances = (
    address: MaybeRef<string> = ref('')
  ): ComputedRef<AssetBalances> =>
    computed(() => {
      const ownedAssets: AssetBalances = {};
      const accountAddress = get(address);

      const balances = get(loopring);
      for (const [address, assets] of Object.entries(balances)) {
        if (accountAddress && accountAddress !== address) {
          continue;
        }
        for (const [asset, value] of Object.entries(assets)) {
          const identifier = getAssociatedAssetIdentifier(asset);
          const associatedAsset: string = get(identifier);
          const ownedAsset = ownedAssets[associatedAsset];

          if (!ownedAsset) {
            ownedAssets[associatedAsset] = { ...value };
          } else {
            ownedAssets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
          }
        }
      }
      return ownedAssets;
    });

  const getLoopringBalances = (address: MaybeRef<string>) =>
    computed<AssetBalance[]>(() => {
      const ownedAssets = getLoopringAssetBalances(address);
      return toSortedAssetBalanceArray(get(ownedAssets), asset =>
        get(isAssetIgnored(asset))
      );
    });

  const accountAssets = (address: MaybeRef<string>) =>
    computed<AssetBalance[]>(() => {
      const accountAddress = get(address);
      const ethAccount = get(balances)[Blockchain.ETH][accountAddress];
      if (!ethAccount || isEmpty(ethAccount)) {
        return [];
      }

      return Object.entries(ethAccount.assets)
        .filter(([asset]) => !get(isAssetIgnored(asset)))
        .map(
          ([asset, { amount, usdValue }]) =>
            ({
              asset,
              amount,
              usdValue
            } as AssetBalance)
        );
    });

  const accountLiabilities = (address: MaybeRef<string>) =>
    computed<AssetBalance[]>(() => {
      const accountAddress = get(address);
      const ethAccount = get(balances)[Blockchain.ETH][accountAddress];
      if (!ethAccount || isEmpty(ethAccount)) {
        return [];
      }

      return Object.entries(ethAccount.liabilities)
        .filter(([asset]) => !get(isAssetIgnored(asset)))
        .map(
          ([asset, { amount, usdValue }]) =>
            ({
              asset,
              amount,
              usdValue
            } as AssetBalance)
        );
    });

  const accountHasDetails = (address: MaybeRef<string>) => {
    const accountAddress = get(address);
    const ethAccount = get(balances)[Blockchain.ETH][accountAddress];
    const loopringBalance = get(loopring)[accountAddress] || {};
    if (!ethAccount || isEmpty(ethAccount)) {
      return false;
    }

    const assetsCount = Object.entries(ethAccount.assets).length;
    const liabilitiesCount = Object.entries(ethAccount.liabilities).length;
    const loopringsCount = Object.entries(loopringBalance).length;

    return assetsCount + liabilitiesCount + loopringsCount > 1;
  };

  const fetchLoopringBalances = async (refresh: boolean) => {
    if (!get(activeModules).includes(Module.LOOPRING)) {
      return;
    }

    const { getStatus, setStatus, resetStatus, loading } = useStatusUpdater(
      Section.L2_LOOPRING_BALANCES
    );

    const status = getStatus();

    if (loading() || (status === Status.LOADED && !refresh)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);
    try {
      const taskType = TaskType.L2_LOOPRING;
      const { taskId } = await queryLoopringBalances();
      const { result } = await awaitTask<AccountAssetBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: tc('actions.balances.loopring.task.title'),
          numericKeys: []
        }
      );

      set(loopring, AccountAssetBalances.parse(result));
      setStatus(Status.LOADED);
    } catch (e: any) {
      notify({
        title: tc('actions.balances.loopring.error.title'),
        message: tc('actions.balances.loopring.error.description', 0, {
          error: e.message
        }),
        display: true
      });
      resetStatus();
    }
  };

  const update = (
    chain: Blockchain,
    { perAccount, totals: updatedTotals }: BlockchainBalances
  ) => {
    if (!isEthChain(chain)) {
      return;
    }

    set(balances, {
      ...get(balances),
      [chain]: perAccount[chain] ?? {}
    });

    set(totals, {
      ...get(totals),
      [chain]: removeZeroAssets(updatedTotals.assets)
    });

    set(liabilities, {
      ...get(liabilities),
      [chain]: removeZeroAssets(updatedTotals.liabilities)
    });
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>) => {
    set(totals, updateTotalsPrices(totals, prices));
    set(liabilities, updateTotalsPrices(liabilities, prices));
    set(balances, updateBlockchainAssetBalances(balances, prices));
    set(loopring, updateAssetBalances(loopring, prices));
  };

  return {
    balances,
    loopring,
    totals,
    liabilities,
    ethAddresses,
    update,
    updatePrices,
    accountAssets,
    accountLiabilities,
    accountHasDetails,
    getLoopringBalances,
    getLoopringAssetBalances,
    fetchLoopringBalances
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEthBalancesStore, import.meta.hot));
}
