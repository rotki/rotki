import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { chainSection } from '@/types/blockchain';
import { BlockchainBalances } from '@/types/blockchain/balances';
import { type AssetPrices } from '@/types/prices';
import { Status } from '@/types/status';
import { type BlockchainMetadata } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type BlockchainBalancePayload } from '@/types/blockchain/accounts';

export const useBlockchainBalances = () => {
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { queryBlockchainBalances } = useBlockchainBalancesApi();
  const { update: updateEth, updatePrices: updateEthPrices } =
    useEthBalancesStore();
  const { update: updateBtc, updatePrices: updateBtcPrices } =
    useBtcBalancesStore();
  const { update: updateChains, updatePrices: updateChainPrices } =
    useChainBalancesStore();
  const { fetchEnsNames } = useAddressesNamesStore();
  const { tc } = useI18n();

  const handleFetch = async (
    blockchain: Blockchain,
    ignoreCache = false
  ): Promise<void> => {
    const { setStatus, resetStatus, isFirstLoad } = useStatusUpdater(
      chainSection[blockchain]
    );

    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);

      const { taskId } = await queryBlockchainBalances(ignoreCache, blockchain);
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

  const fetch = async (
    blockchain: Blockchain,
    ignoreCache = false,
    periodic = false
  ): Promise<void> => {
    const { isLoading } = useStatusStore();
    const loading = isLoading(chainSection[blockchain]);

    const call = () => handleFetch(blockchain, ignoreCache);

    if (get(loading)) {
      if (periodic) {
        return;
      }

      await until(loading).toBe(false);
    }

    await call();
  };

  const fetchBlockchainBalances = async (
    payload: BlockchainBalancePayload = {
      ignoreCache: false
    },
    periodic = false
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
        chains.map(chain => fetch(chain, ignoreCache, periodic))
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
};
