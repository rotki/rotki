import { Blockchain } from '@rotki/common/lib/blockchain';
import { BlockchainBalances } from '@/types/blockchain/balances';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { AssetPrices } from '@/types/prices';
import type { BlockchainMetadata } from '@/types/task';
import type { MaybeRef } from '@vueuse/core';
import type { BlockchainBalancePayload } from '@/types/blockchain/accounts';

export function useBlockchainBalances() {
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { queryBlockchainBalances } = useBlockchainBalancesApi();
  const { update: updateEth, updatePrices: updateEthPrices } = useEthBalancesStore();
  const { update: updateBtc, updatePrices: updateBtcPrices } = useBtcBalancesStore();
  const { update: updateChains, updatePrices: updateChainPrices } = useChainBalancesStore();
  const { getChainName } = useSupportedChains();
  const { t } = useI18n();
  const { setStatus, resetStatus, isFirstLoad } = useStatusUpdater(Section.BLOCKCHAIN);

  const handleFetch = async (
    blockchain: Blockchain,
    ignoreCache = false,
  ): Promise<void> => {
    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING, { subsection: blockchain });

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
          title: t('actions.balances.blockchain.task.title', {
            chain: get(getChainName(blockchain)),
          }),
        },
        true,
      );
      const balances = BlockchainBalances.parse(result);
      updateEth(blockchain, balances);
      updateBtc(blockchain, balances);
      updateChains(blockchain, balances);
      setStatus(Status.LOADED, { subsection: blockchain });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          title: t('actions.balances.blockchain.error.title'),
          message: t('actions.balances.blockchain.error.description', {
            error: error.message,
          }),
          display: true,
        });
      }
      resetStatus({ subsection: blockchain });
    }
  };

  const fetch = async (
    blockchain: Blockchain,
    ignoreCache = false,
    periodic = false,
  ): Promise<void> => {
    const { isLoading } = useStatusStore();
    const loading = isLoading(Section.BLOCKCHAIN, blockchain);

    const call = () => handleFetch(blockchain, ignoreCache);

    if (get(loading)) {
      if (periodic)
        return;

      await until(loading).toBe(false);
    }

    await call();
  };

  const fetchBlockchainBalances = async (
    payload: BlockchainBalancePayload = {
      ignoreCache: false,
    },
    periodic = false,
  ): Promise<void> => {
    const { blockchain, ignoreCache } = payload;

    const chains: Blockchain[] = blockchain
      ? [blockchain]
      : Object.values(Blockchain);

    try {
      await Promise.allSettled(
        chains.map(chain => fetch(chain, ignoreCache, periodic)),
      );
    }
    catch (error: any) {
      logger.error(error);
      const message = t('actions.balances.blockchain.error.description', {
        error: error.message,
      });
      notify({
        title: t('actions.balances.blockchain.error.title'),
        message,
        display: true,
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
    updatePrices,
  };
}
