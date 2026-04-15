import type { MaybeRef } from 'vue';
import type { AddressBookSimplePayload } from '@/modules/address-names/eth-names';
import type { TaskMeta } from '@/modules/tasks/types';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccounts } from '@/modules/accounts/use-blockchain-accounts-api';
import { useEnsOperations } from '@/modules/address-names/use-ens-operations';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { Section } from '@/modules/common/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

export interface RefreshAccountsParams {
  blockchain?: MaybeRef<string>;
  addresses?: string[];
  isXpub?: boolean;
  periodic?: boolean;
}

interface UseAccountOperationsReturn {
  detectEvmAccounts: () => Promise<void>;
  fetchAccounts: (blockchain?: string | string[], refreshEns?: boolean) => Promise<void>;
  refreshAccounts: (params?: RefreshAccountsParams) => Promise<void>;
  resetStatuses: () => void;
}

export function useAccountOperations(): UseAccountOperationsReturn {
  const { fetch } = useBlockchainAccounts();
  const { fetchBlockchainBalances, fetchLoopringBalances, refreshBlockchainBalances } = useBlockchainBalances();
  const { fetchEnsNames } = useEnsOperations();
  const { detectEvmAccounts: detectEvmAccountsCaller } = useBlockchainAccountsApi();
  const { isEvm, supportedChains, supportsTransactions } = useSupportedChains();
  const { getAddresses } = useAccountAddresses();

  const { runTask } = useTaskHandler();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  const { resetStatus: resetNftSectionStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

  const resetStatuses = (): void => {
    resetNftSectionStatus();
  };

  const fetchAccounts = async (blockchain?: string | string[], refreshEns: boolean = false): Promise<void> => {
    let chains: string[];
    if (blockchain)
      chains = Array.isArray(blockchain) ? blockchain : [blockchain];
    else
      chains = get(supportedChains).map(chain => chain.id);
    await awaitParallelExecution(chains, chain => chain, fetch, 2);

    const namesPayload: AddressBookSimplePayload[] = [];

    chains.forEach((chain) => {
      if (!isEvm(chain))
        return;

      const addresses = getAddresses(chain);
      namesPayload.push(...addresses.map(address => ({ address, blockchain: chain })));
    });

    if (namesPayload.length > 0)
      startPromise(fetchEnsNames(namesPayload, refreshEns));
  };

  const refreshAccounts = async (params: RefreshAccountsParams = {}): Promise<void> => {
    const { addresses, blockchain, isXpub = false, periodic = false } = params;
    const chain = get(blockchain);
    const uniqueAddresses = addresses && addresses.length > 0 && chain && !supportsTransactions(chain) ? addresses.filter(uniqueStrings) : undefined;
    await fetchAccounts(chain, true);

    const isEth = chain === Blockchain.ETH;
    const isEth2 = chain === Blockchain.ETH2;

    const shouldRefresh = !!(isEth2 || uniqueAddresses);
    const pending: Promise<any>[] = [
      shouldRefresh
        ? refreshBlockchainBalances({ addresses: uniqueAddresses, blockchain: chain, isXpub }, periodic)
        : fetchBlockchainBalances({ addresses: uniqueAddresses, blockchain: chain, isXpub }),
    ];

    if (isEth || !chain) {
      pending.push(fetchLoopringBalances(false));

      if (isEth && getAddresses(Blockchain.ETH2).length > 0)
        startPromise(refreshAccounts({ blockchain: Blockchain.ETH2 }));
    }

    await Promise.allSettled(pending);
  };

  const detectEvmAccounts = async (): Promise<void> => {
    const outcome = await runTask<unknown, TaskMeta>(
      async () => detectEvmAccountsCaller(),
      { type: TaskType.DETECT_EVM_ACCOUNTS, meta: { title: t('actions.detect_evm_accounts.task.title') } },
    );

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.detect_evm_accounts.error.title'),
        t('actions.detect_evm_accounts.error.message', {
          message: outcome.message,
        }),
      );
    }
  };

  return {
    detectEvmAccounts,
    fetchAccounts,
    refreshAccounts,
    resetStatuses,
  };
}
