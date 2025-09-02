import type { BlockchainMetadata } from '@/types/task';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import {
  BlockchainBalances,
  type BtcBalances,
} from '@/types/blockchain/balances';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { convertBtcBalances } from '@/utils/blockchain/accounts';
import { logger } from '@/utils/logging';

function isBtcBalances(data?: BtcBalances | any): data is BtcBalances {
  return !!data && (!!data.standalone || !!data.xpubs);
}

interface UseBalanceProcessingServiceReturn {
  handleFetch: (blockchain: string, ignoreCache: boolean, threshold: string | undefined) => Promise<void>;
}

export function useBalanceProcessingService(): UseBalanceProcessingServiceReturn {
  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { queryBlockchainBalances } = useBlockchainBalancesApi();
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { updateBalances } = useBalancesStore();
  const { getChainName } = useSupportedChains();
  const { t } = useI18n({ useScope: 'global' });
  const { isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.BLOCKCHAIN);

  const handleFetch = async (blockchain: string, ignoreCache: boolean, threshold: string | undefined): Promise<void> => {
    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING, { subsection: blockchain });

      const account = get(accounts)[blockchain];

      if (account && account.length > 0) {
        const { taskId } = await queryBlockchainBalances(ignoreCache, blockchain, threshold);
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
          display: true,
          message: t('actions.balances.blockchain.error.description', {
            error: error.message,
          }),
          title: t('actions.balances.blockchain.error.title'),
        });
      }
      resetStatus({ subsection: blockchain });
    }
  };

  return {
    handleFetch,
  };
}
