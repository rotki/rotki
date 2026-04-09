import type { BlockchainMetadata } from '@/modules/tasks/types';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import {
  BlockchainBalances,
  type BtcBalances,
  type FetchBlockchainBalancePayload,
} from '@/types/blockchain/balances';
import { Section, Status } from '@/types/status';
import { convertBtcBalances } from '@/utils/blockchain/accounts';
import { logger } from '@/utils/logging';

function isBtcBalances(data?: BtcBalances | any): data is BtcBalances {
  return !!data && (!!data.standalone || !!data.xpubs);
}

interface UseBalanceProcessingServiceReturn {
  handleCachedFetch: (payload: FetchBlockchainBalancePayload, threshold: string | undefined) => Promise<void>;
  handleRefresh: (payload: FetchBlockchainBalancePayload) => Promise<void>;
}

export function useBalanceProcessingService(): UseBalanceProcessingServiceReturn {
  const { runTask } = useTaskHandler();
  const { notifyError } = useNotifications();
  const { queryBlockchainBalances, refreshBlockchainBalances, queryXpubBalances } = useBlockchainBalancesApi();
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { updateBalances } = useBalancesStore();
  const { updateTimestamps } = useBlockchainRefreshTimestampsStore();
  const { getChainName } = useSupportedChains();
  const { t } = useI18n({ useScope: 'global' });
  const { isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.BLOCKCHAIN);

  const processBalanceResult = (blockchain: string, result: unknown): void => {
    const parsedBalances: BlockchainBalances = BlockchainBalances.parse(result);

    if (parsedBalances.lastRefreshTs)
      updateTimestamps(parsedBalances.lastRefreshTs);

    const perAccount = parsedBalances.perAccount[blockchain];

    if (isBtcBalances(perAccount))
      updateBalances(blockchain, convertBtcBalances(blockchain, parsedBalances.totals, perAccount));
    else
      updateBalances(blockchain, parsedBalances);
  };

  const executeBalanceQuery = async (
    blockchain: string,
    apiCall: () => Promise<{ taskId: number }>,
  ): Promise<void> => {
    const account = get(accounts)[blockchain];

    if (account && account.length > 0) {
      const meta: BlockchainMetadata = {
        blockchain,
        title: t('actions.balances.blockchain.task.title', {
          chain: getChainName(blockchain),
        }),
      };

      const outcome = await runTask<BlockchainBalances, BlockchainMetadata>(
        apiCall,
        { type: TaskType.QUERY_BLOCKCHAIN_BALANCES, meta, unique: false },
      );

      if (outcome.success) {
        processBalanceResult(blockchain, outcome.result);
        setStatus(Status.LOADED, { subsection: blockchain });
      }
      else {
        if (isActionableFailure(outcome)) {
          logger.error(outcome.error);
          notifyError(
            t('actions.balances.blockchain.error.title'),
            t('actions.balances.blockchain.error.description', {
              error: outcome.message,
            }),
          );
        }
        resetStatus({ subsection: blockchain });
      }
    }
    else {
      updateBalances(blockchain, {
        perAccount: {},
        totals: {
          assets: {},
          liabilities: {},
        },
      });
      setStatus(Status.LOADED, { subsection: blockchain });
    }
  };

  const handleCachedFetch = async (payload: FetchBlockchainBalancePayload, threshold: string | undefined): Promise<void> => {
    const { blockchain } = payload;
    setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING, { subsection: blockchain });
    await executeBalanceQuery(blockchain, async () => queryBlockchainBalances(payload, threshold));
  };

  const handleRefresh = async (payload: FetchBlockchainBalancePayload): Promise<void> => {
    const { blockchain, isXpub } = payload;
    setStatus(Status.REFRESHING, { subsection: blockchain });
    await executeBalanceQuery(
      blockchain,
      async () => !isXpub ? refreshBlockchainBalances(payload) : queryXpubBalances(payload),
    );
  };

  return {
    handleCachedFetch,
    handleRefresh,
  };
}
