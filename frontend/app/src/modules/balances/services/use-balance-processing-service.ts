import type { BlockchainMetadata } from '@/modules/tasks/types';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
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
  handleFetch: (payload: FetchBlockchainBalancePayload, threshold: string | undefined) => Promise<void>;
}

export function useBalanceProcessingService(): UseBalanceProcessingServiceReturn {
  const { runTask } = useTaskHandler();
  const { notifyError } = useNotifications();
  const { queryBlockchainBalances, queryXpubBalances } = useBlockchainBalancesApi();
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { updateBalances } = useBalancesStore();
  const { getChainName } = useSupportedChains();
  const { t } = useI18n({ useScope: 'global' });
  const { isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.BLOCKCHAIN);

  const handleFetch = async (payload: FetchBlockchainBalancePayload, threshold: string | undefined): Promise<void> => {
    const blockchain = payload.blockchain;
    setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING, { subsection: blockchain });

    const account = get(accounts)[blockchain];

    if (account && account.length > 0) {
      const meta: BlockchainMetadata = {
        blockchain,
        title: t('actions.balances.blockchain.task.title', {
          chain: getChainName(blockchain),
        }),
      };

      const outcome = await runTask<BlockchainBalances, BlockchainMetadata>(
        async () => !payload.isXpub ? queryBlockchainBalances(payload, threshold) : queryXpubBalances(payload),
        { type: TaskType.QUERY_BLOCKCHAIN_BALANCES, meta, unique: false },
      );

      if (outcome.success) {
        const parsedBalances: BlockchainBalances = BlockchainBalances.parse(outcome.result);
        const perAccount = parsedBalances.perAccount[blockchain];

        if (isBtcBalances(perAccount)) {
          const totals = parsedBalances.totals;
          updateBalances(blockchain, convertBtcBalances(blockchain, totals, perAccount));
        }
        else {
          updateBalances(blockchain, parsedBalances);
        }

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
      const emptyData: BlockchainBalances = {
        perAccount: {},
        totals: {
          assets: {},
          liabilities: {},
        },
      };
      updateBalances(blockchain, emptyData);
      setStatus(Status.LOADED, { subsection: blockchain });
    }
  };

  return {
    handleFetch,
  };
}
