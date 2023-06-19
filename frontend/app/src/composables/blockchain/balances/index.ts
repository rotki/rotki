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
  const { isEvm } = useSupportedChains();
  const { t } = useI18n();

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
          title: t('actions.balances.blockchain.task.title', {
            chain: blockchain
          })
        },
        true
      );
      const balances = BlockchainBalances.parse(result);
      updateEth(blockchain, balances);
      updateBtc(blockchain, balances);
      updateChains(blockchain, balances);
      setStatus(Status.LOADED);

      if (isEvm(blockchain)) {
        const perChainBalances = balances.perAccount[blockchain];
        if (!perChainBalances) {
          return;
        }

        const addresses = [...Object.keys(perChainBalances)];
        startPromise(
          fetchEnsNames(
            addresses.map(address => ({ address, blockchain })),
            ignoreCache
          )
        );
      }
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.balances.blockchain.error.title'),
        message: t('actions.balances.blockchain.error.description', {
          error: e.message
        }),
        display: true
      });
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

    const chains: Blockchain[] = blockchain
      ? [blockchain]
      : Object.values(Blockchain);

    try {
      await Promise.allSettled(
        chains.map(chain => fetch(chain, ignoreCache, periodic))
      );
    } catch (e: any) {
      logger.error(e);
      const message = t('actions.balances.blockchain.error.description', {
        error: e.message
      });
      notify({
        title: t('actions.balances.blockchain.error.title'),
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
