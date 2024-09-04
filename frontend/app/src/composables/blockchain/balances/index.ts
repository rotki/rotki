import { Blockchain } from '@rotki/common';
import { BlockchainBalances, type BtcBalances } from '@/types/blockchain/balances';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { Module } from '@/types/modules';
import { AccountAssetBalances, type AssetBalances } from '@/types/balances';
import { ReadOnlyTag } from '@/types/tags';
import type { BlockchainMetadata, TaskMeta } from '@/types/task';
import type { BlockchainAccount, BlockchainBalancePayload } from '@/types/blockchain/accounts';

function isBtcBalances(data?: BtcBalances | AssetBalances): data is BtcBalances {
  return !!data && (!!data.standalone || !!data.xpubs);
}

interface UseBlockchainbalancesReturn {
  fetchBlockchainBalances: (payload?: BlockchainBalancePayload, periodic?: boolean) => Promise<void>;
  fetchLoopringBalances: (refresh: boolean) => Promise<void>;
}

export function useBlockchainBalances(): UseBlockchainbalancesReturn {
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { queryBlockchainBalances } = useBlockchainBalancesApi();
  const blockchainStore = useBlockchainStore();
  const { accounts } = storeToRefs(blockchainStore);
  const { updateBalances, updateAccounts } = blockchainStore;
  const { getChainName, supportedChains } = useSupportedChains();
  const { t } = useI18n();
  const { setStatus, resetStatus, isFirstLoad } = useStatusUpdater(Section.BLOCKCHAIN);
  const { activeModules } = storeToRefs(useGeneralSettingsStore());
  const { queryLoopringBalances } = useBlockchainBalancesApi();
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

  const handleFetch = async (blockchain: string, ignoreCache = false): Promise<void> => {
    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING, { subsection: blockchain });

      const account = get(accounts)[blockchain];

      if (account && account.length > 0) {
        const { taskId } = await queryBlockchainBalances(ignoreCache, blockchain);
        const taskType = TaskType.QUERY_BLOCKCHAIN_BALANCES;
        const { result } = await awaitTask<BlockchainBalances, BlockchainMetadata>(
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
        const parsedBalances: BlockchainBalances = BlockchainBalances.parse(result);
        const perAccount = parsedBalances.perAccount[blockchain];

        if (isBtcBalances(perAccount)) {
          const totals = parsedBalances.totals;
          updateBalances(blockchain, convertBtcBalances(blockchain, totals, perAccount));
        }
        else {
          updateBalances(blockchain, parsedBalances);
        }
      }
      else {
        const emptyData: BlockchainBalances = {
          perAccount: {},
          totals: {
            assets: {},
            liabilities: {},
          },
        };
        updateBalances(blockchain, emptyData);
      }

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

  const fetch = async (blockchain: string, ignoreCache = false, periodic = false): Promise<void> => {
    const { isLoading } = useStatusStore();
    const loading = isLoading(Section.BLOCKCHAIN, blockchain);

    const call = (): Promise<void> => handleFetch(blockchain, ignoreCache);

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

    const chains: string[] = blockchain ? [blockchain] : get(supportedChains).map(chain => chain.id);

    try {
      await awaitParallelExecution(
        chains,
        chain => chain,
        chain => fetch(chain, ignoreCache, periodic),
        2,
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

  const fetchLoopringBalances = async (refresh: boolean): Promise<void> => {
    if (!get(activeModules).includes(Module.LOOPRING))
      return;

    const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(Section.BLOCKCHAIN);

    if (fetchDisabled(refresh, { subsection: 'loopring' }))
      return;

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, { subsection: 'loopring' });
    try {
      const taskType = TaskType.L2_LOOPRING;
      const { taskId } = await queryLoopringBalances();
      const { result } = await awaitTask<AccountAssetBalances, TaskMeta>(taskId, taskType, {
        title: t('actions.balances.loopring.task.title'),
      });

      const loopringBalances = AccountAssetBalances.parse(result);
      const accounts = Object.keys(loopringBalances).map(
        address =>
          ({
            data: {
              type: 'address',
              address,
            },
            chain: 'loopring',
            tags: [ReadOnlyTag.LOOPRING],
            nativeAsset: Blockchain.ETH.toUpperCase(),
            virtual: true,
          }) satisfies BlockchainAccount,
      );

      const loopring = Object.fromEntries(
        Object.entries(loopringBalances).map(([address, assets]) => [
          address,
          {
            assets,
            liabilities: {},
          },
        ]),
      );

      const assets: AssetBalances = {};
      for (const loopringAssets of Object.values(loopringBalances)) {
        for (const [asset, value] of Object.entries(loopringAssets)) {
          const identifier = getAssociatedAssetIdentifier(asset);
          const associatedAsset: string = get(identifier);
          const ownedAsset = assets[associatedAsset];

          if (!ownedAsset)
            assets[associatedAsset] = { ...value };
          else assets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
        }
      }

      const updatedTotals = {
        perAccount: {
          loopring,
        },
        totals: {
          assets,
          liabilities: {},
        },
      };
      updateBalances('loopring', updatedTotals);
      updateAccounts('loopring', accounts);
      setStatus(Status.LOADED, { subsection: 'loopring' });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.balances.loopring.error.title'),
          message: t('actions.balances.loopring.error.description', {
            error: error.message,
          }),
          display: true,
        });
      }
      resetStatus({ subsection: 'loopring' });
    }
  };

  return {
    fetchBlockchainBalances,
    fetchLoopringBalances,
  };
}
