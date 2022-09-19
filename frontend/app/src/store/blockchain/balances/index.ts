import { Blockchain } from '@rotki/common/lib/blockchain';
import { MaybeRef } from '@vueuse/core';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainBalanceApi } from '@/services/balances/blockchain';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { BlockchainBalancePayload } from '@/store/balances/types';
import { useBtcBalancesStore } from '@/store/blockchain/balances/btc';
import { useChainBalancesStore } from '@/store/blockchain/balances/chains';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { chainSection } from '@/types/blockchain';
import { BlockchainBalances } from '@/types/blockchain/balances';
import { AssetPrices } from '@/types/prices';
import { Status } from '@/types/status';
import { BlockchainMetadata } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

export const useBlockchainBalancesStore = defineStore(
  'balances/blockchain',
  () => {
    const { awaitTask } = useTasks();
    const { notify } = useNotifications();
    const { queryBlockchainBalances } = useBlockchainBalanceApi();
    const { update: updateEth, updatePrices: updateEthPrices } =
      useEthBalancesStore();
    const { update: updateBtc, updatePrices: updateBtcPrices } =
      useBtcBalancesStore();
    const { update: updateChains, updatePrices: updateChainPrices } =
      useChainBalancesStore();
    const { fetchEnsNames } = useEthNamesStore();
    const { tc } = useI18n();

    const fetch = async (
      chain: Blockchain,
      ignoreCache: boolean = false
    ): Promise<void> => {
      const { loading, setStatus, resetStatus, isFirstLoad } = useStatusUpdater(
        chainSection[chain]
      );

      if (loading()) {
        return;
      }

      try {
        setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);

        const { taskId } = await queryBlockchainBalances(ignoreCache, chain);
        const taskType = TaskType.QUERY_BLOCKCHAIN_BALANCES;
        const { result } = await awaitTask<
          BlockchainBalances,
          BlockchainMetadata
        >(
          taskId,
          taskType,
          {
            chain,
            title: tc('actions.balances.blockchain.task.title', 0, {
              chain
            }),
            numericKeys: []
          } as BlockchainMetadata,
          true
        );
        const balances = BlockchainBalances.parse(result);
        const ethBalances = balances.perAccount[Blockchain.ETH];

        if (ignoreCache && ethBalances) {
          const addresses = [...Object.keys(ethBalances)];
          await fetchEnsNames(addresses, ignoreCache);
        }
        updateEth(chain, balances);
        updateBtc(chain, balances);
        updateChains(chain, balances);
        setStatus(Status.LOADED);
      } catch (e: any) {
        logger.error(e);
        resetStatus();
      }
    };

    const fetchBlockchainBalances = async (
      payload: BlockchainBalancePayload = {
        ignoreCache: false
      }
    ): Promise<void> => {
      const { blockchain, ignoreCache } = payload;

      const chains: Blockchain[] = [];
      if (!blockchain) {
        chains.push(...Object.values(Blockchain));
      } else {
        chains.push(blockchain);
      }

      try {
        await Promise.allSettled(
          chains.map(chain => fetch(chain, ignoreCache))
        );
      } catch (e: any) {
        logger.error(e);
        const message = tc('actions.balances.blockchain.error.description', 0, {
          error: e.message
        });
        notify({
          title: tc('actions.balances.blockchain.error.title'),
          message,
          display: true
        });
      }
    };

    const updatePrices = (prices: MaybeRef<AssetPrices>) => {
      updateEthPrices(prices);
      updateBtcPrices(prices);
      updateChainPrices(prices);
    };

    return {
      fetchBlockchainBalances,
      updatePrices
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBlockchainBalancesStore, import.meta.hot)
  );
}
