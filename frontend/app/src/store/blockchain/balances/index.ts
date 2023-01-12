import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { useBlockchainBalanceApi } from '@/services/balances/blockchain';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { type BlockchainBalancePayload } from '@/store/balances/types';
import { useBtcBalancesStore } from '@/store/blockchain/balances/btc';
import { useChainBalancesStore } from '@/store/blockchain/balances/chains';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';
import { useNotificationsStore } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { chainSection } from '@/types/blockchain';
import { BlockchainBalances } from '@/types/blockchain/balances';
import { type AssetPrices } from '@/types/prices';
import { Status } from '@/types/status';
import { type BlockchainMetadata } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

export const useBlockchainBalancesStore = defineStore(
  'balances/blockchain',
  () => {
    const { awaitTask } = useTasks();
    const { notify } = useNotificationsStore();
    const { queryBlockchainBalances } = useBlockchainBalanceApi();
    const { update: updateEth, updatePrices: updateEthPrices } =
      useEthBalancesStore();
    const { update: updateBtc, updatePrices: updateBtcPrices } =
      useBtcBalancesStore();
    const { update: updateChains, updatePrices: updateChainPrices } =
      useChainBalancesStore();
    const { fetchEnsNames } = useAddressesNamesStore();
    const { tc } = useI18n();

    const fetch = async (
      blockchain: Blockchain,
      ignoreCache = false
    ): Promise<void> => {
      const { loading, setStatus, resetStatus, isFirstLoad } = useStatusUpdater(
        chainSection[blockchain]
      );

      if (loading()) {
        return;
      }

      try {
        setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);

        const { taskId } = await queryBlockchainBalances(
          ignoreCache,
          blockchain
        );
        const taskType = TaskType.QUERY_BLOCKCHAIN_BALANCES;
        const { result } = await awaitTask<
          BlockchainBalances,
          BlockchainMetadata
        >(
          taskId,
          taskType,
          {
            blockchain,
            title: tc('actions.balances.blockchain.task.title', 0, {
              chain: blockchain
            })
          },
          true
        );
        const balances = BlockchainBalances.parse(result);
        const ethBalances = balances.perAccount[Blockchain.ETH];

        if (ethBalances) {
          const addresses = [...Object.keys(ethBalances)];
          await fetchEnsNames(addresses, ignoreCache);
        }
        updateEth(blockchain, balances);
        updateBtc(blockchain, balances);
        updateChains(blockchain, balances);
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
