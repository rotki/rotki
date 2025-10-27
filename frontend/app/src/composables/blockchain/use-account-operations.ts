import type { MaybeRef } from '@vueuse/core';
import type { AddressBookSimplePayload } from '@/types/eth-names';
import type { TaskMeta } from '@/types/task';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { useBlockchainAccounts } from '@/composables/blockchain/accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { arrayify } from '@/utils/array';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

interface UseAccountOperationsReturn {
  detectEvmAccounts: () => Promise<void>;
  fetchAccounts: (blockchain?: string | string[], refreshEns?: boolean) => Promise<void>;
  refreshAccounts: (blockchain?: MaybeRef<string>, addresses?: string[], isXpub?: boolean, periodic?: boolean) => Promise<void>;
  resetStatuses: () => void;
}

export function useAccountOperations(): UseAccountOperationsReturn {
  const { fetch } = useBlockchainAccounts();
  const { fetchBlockchainBalances, fetchLoopringBalances } = useBlockchainBalances();
  const { fetchEnsNames } = useAddressesNamesStore();
  const { detectEvmAccounts: detectEvmAccountsCaller } = useBlockchainAccountsApi();
  const { isEvm, supportedChains, supportsTransactions } = useSupportedChains();
  const { getAddresses } = useAccountAddresses();

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const { resetStatus: resetNftSectionStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);

  const resetStatuses = (): void => {
    resetNftSectionStatus();
  };

  const fetchAccounts = async (blockchain?: string | string[], refreshEns: boolean = false): Promise<void> => {
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    await awaitParallelExecution(chains, chain => chain, fetch, 2);

    const namesPayload: AddressBookSimplePayload[] = [];

    chains.forEach((chain) => {
      if (!get(isEvm(chain)))
        return;

      const addresses = getAddresses(chain);
      namesPayload.push(...addresses.map(address => ({ address, blockchain: chain })));
    });

    if (namesPayload.length > 0)
      startPromise(fetchEnsNames(namesPayload, refreshEns));
  };

  const refreshAccounts = async (blockchain?: MaybeRef<string>, addresses?: string[], isXpub = false, periodic = false): Promise<void> => {
    const chain = get(blockchain);
    const uniqueAddresses = addresses && addresses.length > 0 && chain && !supportsTransactions(chain) ? addresses.filter(uniqueStrings) : undefined;
    await fetchAccounts(chain, true);

    const isEth = chain === Blockchain.ETH;
    const isEth2 = chain === Blockchain.ETH2;

    const pending: Promise<any>[] = [fetchBlockchainBalances({ addresses: uniqueAddresses, blockchain: chain, ignoreCache: !!(isEth2 || uniqueAddresses), isXpub }, periodic)];

    if (isEth || !chain) {
      pending.push(fetchLoopringBalances(false));

      if (isEth)
        startPromise(refreshAccounts(Blockchain.ETH2));
    }

    await Promise.allSettled(pending);
  };

  const detectEvmAccounts = async (): Promise<void> => {
    try {
      const taskType = TaskType.DETECT_EVM_ACCOUNTS;
      const { taskId } = await detectEvmAccountsCaller();
      await awaitTask<unknown, TaskMeta>(taskId, taskType, {
        title: t('actions.detect_evm_accounts.task.title'),
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.detect_evm_accounts.error.message', {
            message: error.message,
          }),
          title: t('actions.detect_evm_accounts.error.title'),
        });
      }
    }
  };

  return {
    detectEvmAccounts,
    fetchAccounts,
    refreshAccounts,
    resetStatuses,
  };
}
