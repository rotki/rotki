import type { AccountPayload, AddAccountsPayload, XpubAccountPayload } from '@/types/blockchain/accounts';
import type { AddressBookSimplePayload } from '@/types/eth-names';
import type { Module } from '@/types/modules';
import type { TaskMeta } from '@/types/task';
import type { MaybeRef } from '@vueuse/core';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { useBlockchainAccounts } from '@/composables/blockchain/accounts';
import { useAccountAdditionNotifications } from '@/composables/blockchain/use-account-addition-notifications';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useNotificationsStore } from '@/store/notifications';
import { useSettingsStore } from '@/store/settings';
import { useTaskStore } from '@/store/tasks';
import { isBlockchain } from '@/types/blockchain/chains';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { arrayify } from '@/utils/array';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { logger } from '@/utils/logging';
import { type Account, assert, Blockchain, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';

interface EvmAccountAdditionSuccess {
  type: 'success';
  accounts: Account[];
}

interface EvmAccountAdditionFailure {
  type: 'error';
  error: Error;
  account: AccountPayload;
}

interface AccountAdditionSuccess {
  type: 'success';
  address: string;
}

interface AccountAdditionFailure {
  type: 'error';
  error: Error;
  account: AccountPayload | XpubAccountPayload;
}

interface AddAccountsOption {
  wait: boolean;
}

interface UseBlockchainsReturn {
  addAccounts: (chain: string, data: AddAccountsPayload | XpubAccountPayload, options?: AddAccountsOption) => Promise<void>;
  addEvmAccounts: (payload: AddAccountsPayload, options?: AddAccountsOption) => Promise<void>;
  detectEvmAccounts: () => Promise<void>;
  fetchAccounts: (blockchain?: string | string[], refreshEns?: boolean) => Promise<void>;
  refreshAccounts: (blockchain?: MaybeRef<string>, periodic?: boolean) => Promise<void>;
}

function CHAIN_ORDER_COMPARATOR(chains: string[]): (a: Account, b: Account) => number {
  return (
    a: Account,
    b: Account,
  ): number => chains.indexOf(a.chain) - chains.indexOf(b.chain);
}

export function useBlockchains(): UseBlockchainsReturn {
  const { addAccount, addEvmAccount, fetch } = useBlockchainAccounts();
  const { fetchBlockchainBalances, fetchLoopringBalances } = useBlockchainBalances();
  const { fetchDetected } = useBlockchainTokensStore();
  const { fetchEnsNames } = useAddressesNamesStore();
  const { enableModule } = useSettingsStore();
  const { detectEvmAccounts: detectEvmAccountsCaller } = useBlockchainAccountsApi();
  const { evmChains, getChainName, isEvm, supportedChains, supportsTransactions } = useSupportedChains();
  const { getAddresses } = useAccountAddresses();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const { resetStatus: resetNftSectionStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);
  const {
    createFailureNotification,
    notifyFailedToAddAddress,
    notifyUser,
  } = useAccountAdditionNotifications();

  const getNewAccountPayload = (chain: string, payload: AccountPayload[]): AccountPayload[] => {
    const knownAddresses: string[] = getAddresses(chain);
    return payload.filter(({ address }) => {
      const key = address.toLocaleLowerCase();
      return !knownAddresses.includes(key);
    });
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

  const refreshAccounts = async (blockchain?: MaybeRef<string>, periodic = false): Promise<void> => {
    const chain = get(blockchain);
    await fetchAccounts(chain, true);

    const isEth = chain === Blockchain.ETH;
    const isEth2 = chain === Blockchain.ETH2;

    const pending: Promise<any>[] = [fetchBlockchainBalances({ blockchain: chain, ignoreCache: isEth2 }, periodic)];

    if (isEth || !chain) {
      pending.push(fetchLoopringBalances(false));

      if (isEth)
        startPromise(refreshAccounts(Blockchain.ETH2));
    }

    await Promise.allSettled(pending);
  };

  const resetStatuses = (): void => {
    resetNftSectionStatus();
  };

  const completeAccountAddition = async (
    params: { addedAccounts: Account[]; modulesToEnable?: Module[]; chain?: string },
  ): Promise<void> => {
    const {
      addedAccounts,
      chain,
      modulesToEnable,
    } = params;
    resetStatuses();

    await refreshAccounts(chain);
    const chains = chain ? [chain] : get(supportedChains).map(chain => chain.id);
    // Sort accounts by chain, so they are called in order
    const sortedAccounts = addedAccounts.sort(CHAIN_ORDER_COMPARATOR(chains));

    await awaitParallelExecution(
      sortedAccounts,
      item => item.address + item.chain,
      async (account) => {
        const { address, chain }: Account = account;
        if (chain === Blockchain.ETH && modulesToEnable) {
          await enableModule({
            addresses: [address],
            enable: modulesToEnable,
          });
        }

        if (supportsTransactions(chain))
          await fetchDetected(chain, [address]);
      },
      2,
    );
  };

  const addSingleEvmAddress = async (account: AccountPayload): Promise<EvmAccountAdditionSuccess | EvmAccountAdditionFailure> => {
    const addedAccounts: Account[] = [];

    try {
      const { added, ...result } = await addEvmAccount(account);

      if (added) {
        const [address, chains] = Object.entries(added)[0];
        const isAll = chains.length === 1 && chains[0] === 'all';
        const usedChains = isAll ? get(evmChains) : chains;

        usedChains.forEach((chain) => {
          if (!isBlockchain(chain)) {
            logger.error(`${chain.toString()} was not a valid blockchain`);
            return;
          }

          addedAccounts.push({
            address,
            chain,
          });
        });

        notifyUser({ account, chains, isAll });
      }

      createFailureNotification(result, account);

      return {
        accounts: addedAccounts,
        type: 'success',
      };
    }
    catch (error: any) {
      logger.error(error.message);
      return {
        account,
        error,
        type: 'error',
      };
    }
  };

  const addMultipleEvmAccounts = async (payload: AddAccountsPayload): Promise<void> => {
    const addedAccounts: Account[] = [];
    const failedToAddAccounts: AccountPayload[] = [];

    await awaitParallelExecution(
      payload.payload,
      account => account.address,
      async (account) => {
        const result = await addSingleEvmAddress(account);
        if (result.type === 'success')
          addedAccounts.push(...result.accounts);

        else
          failedToAddAccounts.push(result.account);
      },
      2,
    );

    if (failedToAddAccounts.length > 0)
      notifyFailedToAddAddress(failedToAddAccounts, payload.payload.length);

    startPromise(completeAccountAddition({ addedAccounts, modulesToEnable: payload.modules }));
  };

  const addEvmAccounts = async (payload: AddAccountsPayload, options?: AddAccountsOption): Promise<void> => {
    if (payload.payload.length === 1) {
      const addResult = await addSingleEvmAddress(payload.payload[0]);
      if (addResult.type === 'error')
        throw addResult.error;

      startPromise(completeAccountAddition({ addedAccounts: addResult.accounts, modulesToEnable: payload.modules }));
    }
    else {
      if (options?.wait)
        await addMultipleEvmAccounts(payload);
      else
        startPromise(addMultipleEvmAccounts(payload));
    }
  };

  const addSingleAccount = async (
    account: AccountPayload | XpubAccountPayload,
    chain: string,
  ): Promise<AccountAdditionSuccess | AccountAdditionFailure> => {
    const isXpub = 'xpub' in account;
    try {
      const address = await addAccount(chain, isXpub ? account : [account]);
      return {
        address,
        type: 'success',
      };
    }
    catch (error: any) {
      logger.error(error.message);
      return {
        account,
        error,
        type: 'error',
      };
    }
  };

  const addMultipleAccounts = async (payload: AccountPayload[], chain: string, modules?: (Module)[]): Promise<void> => {
    const addedAccounts: Account[] = [];
    const failedToAddAccounts: AccountPayload[] = [];

    await awaitParallelExecution(
      payload,
      account => account.address,
      async (account) => {
        const result = await addSingleAccount(account, chain);
        if (result.type === 'success') {
          addedAccounts.push({ address: result.address, chain });
        }
        else {
          assert(!('xpub' in result.account));
          failedToAddAccounts.push(result.account);
        }
      },
      2,
    );

    if (failedToAddAccounts.length > 0)
      notifyFailedToAddAddress(failedToAddAccounts, payload.length, chain);

    startPromise(completeAccountAddition({ addedAccounts, chain, modulesToEnable: modules }));
  };

  const addAccounts = async (chain: string, payload: AddAccountsPayload | XpubAccountPayload, options?: AddAccountsOption): Promise<void> => {
    const taskType = TaskType.ADD_ACCOUNT;
    if (isTaskRunning(taskType)) {
      logger.debug(`${TaskType[taskType]} is already running.`);
      return;
    }
    const isXpub = 'xpub' in payload;
    const modules = isXpub ? [] : payload.modules;

    const filteredPayload = isXpub ? [] : getNewAccountPayload(chain, payload.payload);
    if (filteredPayload.length === 0 && !isXpub) {
      const title = t('actions.balances.blockchain_accounts_add.task.title', {
        blockchain: get(getChainName(chain)),
      });
      const message = t('actions.balances.blockchain_accounts_add.no_new.description');
      notify({
        display: true,
        message,
        severity: Severity.INFO,
        title,
      });
      return;
    }

    if (filteredPayload.length === 1 || isXpub) {
      const addResult = await addSingleAccount(isXpub ? payload : filteredPayload[0], chain);
      if (addResult.type === 'error')
        throw addResult.error;

      startPromise(completeAccountAddition({
        addedAccounts: [{
          address: addResult.address,
          chain,
        }],
        modulesToEnable: modules,
      }));
    }
    else {
      if (options?.wait)
        await addMultipleAccounts(filteredPayload, chain, modules);
      else
        startPromise(addMultipleAccounts(filteredPayload, chain, modules));
    }
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
    addAccounts,
    addEvmAccounts,
    detectEvmAccounts,
    fetchAccounts,
    refreshAccounts,
  };
}
