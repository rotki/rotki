import { type Account, Blockchain, Severity } from '@rotki/common';
import { TaskType } from '@/types/task-type';
import { isBlockchain } from '@/types/blockchain/chains';
import { Section } from '@/types/status';
import type { MaybeRef } from '@vueuse/core';
import type { AccountPayload, AddAccountsPayload, XpubAccountPayload } from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import type { AddressBookSimplePayload } from '@/types/eth-names';
import type { Module } from '@/types/modules';

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

interface UseBlockchainsReturn {
  addAccounts: (chain: string, data: AddAccountsPayload | XpubAccountPayload) => Promise<void>;
  addEvmAccounts: (payload: AddAccountsPayload) => Promise<void>;
  detectEvmAccounts: () => Promise<void>;
  fetchAccounts: (blockchain?: string, refreshEns?: boolean) => Promise<void>;
  refreshAccounts: (blockchain?: MaybeRef<string>, periodic?: boolean) => Promise<void>;
}

function CHAIN_ORDER_COMPARATOR(chains: string[]): (a: Account, b: Account) => number {
  return (
    a: Account,
    b: Account,
  ): number => chains.indexOf(a.chain) - chains.indexOf(b.chain);
}

export function useBlockchains(): UseBlockchainsReturn {
  const { addAccount, fetch, addEvmAccount } = useBlockchainAccounts();
  const { fetchBlockchainBalances, fetchLoopringBalances } = useBlockchainBalances();
  const { fetchDetected } = useBlockchainTokensStore();
  const { fetchEnsNames } = useAddressesNamesStore();
  const { enableModule } = useSettingsStore();
  const { reset: resetDefi } = useDefiStore();
  const { resetDefiStatus } = useStatusStore();
  const { detectEvmAccounts: detectEvmAccountsCaller } = useBlockchainAccountsApi();
  const { getChainName, supportsTransactions, evmChains, isEvm, supportedChains } = useSupportedChains();
  const { getAddresses } = useBlockchainStore();

  const { isTaskRunning, awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const { resetStatus: resetNftSectionStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);
  const {
    notifyUser,
    createFailureNotification,
    notifyFailedToAddAddress,
  } = useAccountAdditionNotifications();

  const getNewAccountPayload = (chain: string, payload: AccountPayload[]): AccountPayload[] => {
    const knownAddresses: string[] = getAddresses(chain);
    return payload.filter(({ address }) => {
      const key = address.toLocaleLowerCase();
      return !knownAddresses.includes(key);
    });
  };

  const fetchAccounts = async (blockchain?: string, refreshEns: boolean = false): Promise<void> => {
    const chains = blockchain ? [blockchain] : get(supportedChains).map(chain => chain.id);
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
    resetDefi();
    resetDefiStatus();
    resetNftSectionStatus();
  };

  const completeAccountAddition = async (
    params: { addedAccounts: Account[]; modulesToEnable?: Module[]; chain?: string },
  ): Promise<void> => {
    const {
      addedAccounts,
      modulesToEnable,
      chain,
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
        const { chain, address }: Account = account;
        if (chain === Blockchain.ETH && modulesToEnable) {
          await enableModule({
            enable: modulesToEnable,
            addresses: [address],
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
            logger.error(`${chain} was not a valid blockchain`);
            return;
          }

          addedAccounts.push({
            chain,
            address,
          });
        });

        notifyUser({ account, isAll, chains });
      }

      createFailureNotification(result, account);

      return {
        type: 'success',
        accounts: addedAccounts,
      };
    }
    catch (error: any) {
      logger.error(error.message);
      return {
        type: 'error',
        error,
        account,
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
      }
      , 2,
    );

    if (failedToAddAccounts.length > 0)
      notifyFailedToAddAddress(failedToAddAccounts, payload.payload.length);

    startPromise(completeAccountAddition({ addedAccounts, modulesToEnable: payload.modules }));
  };

  const addEvmAccounts = async (payload: AddAccountsPayload): Promise<void> => {
    if (payload.payload.length === 1) {
      const addResult = await addSingleEvmAddress(payload.payload[0]);
      if (addResult.type === 'error')
        throw addResult.error;

      startPromise(completeAccountAddition({ addedAccounts: addResult.accounts, modulesToEnable: payload.modules }));
    }
    else {
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
        type: 'success',
        address,
      };
    }
    catch (error: any) {
      logger.error(error.message);
      return {
        type: 'error',
        account,
        error,
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
      }
      , 2,
    );

    if (failedToAddAccounts.length > 0)
      notifyFailedToAddAddress(failedToAddAccounts, payload.length, chain);

    startPromise(completeAccountAddition({ addedAccounts, modulesToEnable: modules, chain }));
  };

  const addAccounts = async (chain: string, payload: AddAccountsPayload | XpubAccountPayload): Promise<void> => {
    const taskType = TaskType.ADD_ACCOUNT;
    if (get(isTaskRunning(taskType))) {
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
        title,
        message,
        severity: Severity.INFO,
        display: true,
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
          title: t('actions.detect_evm_accounts.error.title'),
          message: t('actions.detect_evm_accounts.error.message', {
            message: error.message,
          }),
          display: true,
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
