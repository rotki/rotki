import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { type ComputedRef, type Ref } from 'vue';
import { AccountAssetBalances, type AssetBalances } from '@/types/balances';
import {
  type BlockchainAssetBalances,
  type BlockchainBalances
} from '@/types/blockchain/balances';
import { type EthChains, isEthChain } from '@/types/blockchain/chains';
import { Module } from '@/types/modules';
import { type AssetPrices } from '@/types/prices';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { removeZeroAssets } from '@/utils/balances';
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
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrievalStore();
  const { queryLoopringBalances } = useBlockchainBalancesApi();
  const { tc } = useI18n();

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
          title: tc('actions.balances.loopring.task.title')
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
    update,
    updatePrices,
    getLoopringAssetBalances,
    fetchLoopringBalances
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEthBalancesStore, import.meta.hot));
}
