import { Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { TaskType } from '@/types/task-type';
import { isBlockchain } from '@/types/blockchain/chains';
import { Section } from '@/types/status';
import type { EvmAccountsResult } from '@/types/api/accounts';
import type { Account } from '@rotki/common/lib/account';
import type { MaybeRef } from '@vueuse/core';
import type {
  AccountPayload,
  AddAccountsPayload,
  XpubAccountPayload,
} from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import type { AddressBookSimplePayload } from '@/types/eth-names';

export function useBlockchains() {
  const { addAccount, fetch, addEvmAccount } = useBlockchainAccounts();
  const { fetchBlockchainBalances, fetchLoopringBalances } = useBlockchainBalances();
  const { fetchDetected } = useBlockchainTokensStore();
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

  const getNewAccountPayload = (
    chain: string,
    payload: AccountPayload[],
  ): AccountPayload[] => {
    const knownAddresses: string[] = getAddresses(chain);
    return payload.filter(({ address }) => {
      const key = address.toLocaleLowerCase();
      return !knownAddresses.includes(key);
    });
  };

  const getChainsText = (chains: string[], explanation?: string) => chains.map((chain) => {
    let text = `- ${get(getChainName(chain))}`;
    if (explanation)
      text += ` (${explanation})`;

    return text;
  }).join('\n');

  const { fetchEnsNames } = useAddressesNamesStore();

  const fetchAccounts = async (
    blockchain?: string,
    refreshEns: boolean = false,
  ): Promise<void> => {
    const chains = blockchain ? [blockchain] : get(supportedChains).map(chain => chain.id);
    await awaitParallelExecution(chains, chain => chain, fetch, 2);
    await Promise.allSettled(chains.map(fetch));

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

  const refreshAccounts = async (
    blockchain?: MaybeRef<string>,
    periodic = false,
  ) => {
    const chain = get(blockchain);
    await fetchAccounts(chain, true);

    const isEth = chain === Blockchain.ETH;
    const isEth2 = chain === Blockchain.ETH2;

    const pending: Promise<any>[] = [
      fetchBlockchainBalances({ blockchain: chain, ignoreCache: isEth2 }, periodic),
    ];

    if (isEth || !chain) {
      pending.push(fetchLoopringBalances(false));

      if (isEth)
        startPromise(refreshAccounts(Blockchain.ETH2));
    }

    await Promise.allSettled(pending);
  };

  function notifyFailed(
    { noActivity, existed, ethContracts, failed }: EvmAccountsResult,
    title: string,
    account: AccountPayload,
  ): void {
    const listOfFailureText: string[] = [];
    if (noActivity) {
      listOfFailureText.push(getChainsText(
        Object.values(noActivity)[0],
        t('actions.balances.blockchain_accounts_add.error.failed_reason.no_activity'),
      ));
    }

    if (existed) {
      listOfFailureText.push(getChainsText(
        Object.values(existed)[0],
        t('actions.balances.blockchain_accounts_add.error.failed_reason.existed'),
      ));
    }

    if (ethContracts) {
      listOfFailureText.push(getChainsText(
        [t('actions.balances.blockchain_accounts_add.error.non_eth')],
        t('actions.balances.blockchain_accounts_add.error.failed_reason.is_contract'),
      ));
    }

    if (failed)
      listOfFailureText.push(getChainsText(Object.values(failed)[0]));

    if (listOfFailureText.length <= 0)
      return;

    notify({
      title,
      message: t('actions.balances.blockchain_accounts_add.error.failed', {
        address: account.address,
        list: listOfFailureText.join('\n'),
      }),
      display: true,
    });
  }

  const addEvmAccounts = async (
    payload: AddAccountsPayload,
  ): Promise<void> => {
    const blockchain = 'EVM';

    const title = t('actions.balances.blockchain_accounts_add.task.title', { blockchain });

    const failedAddition: AccountPayload[] = [];
    const successfulAddition: Account[] = [];

    const singleAddition = payload.payload.length === 1;

    const addSingleAddress = async (account: AccountPayload): Promise<void> => {
      try {
        const result = await addEvmAccount(account);
        const { added } = result;

        if (added) {
          const [address, chains] = Object.entries(added)[0];
          const isAll = chains.length === 1 && chains[0] === 'all';
          const usedChains = isAll ? get(evmChains) : chains;

          usedChains.forEach((chain) => {
            if (!isBlockchain(chain)) {
              logger.error(`${chain} was not a valid blockchain`);
              return;
            }

            successfulAddition.push({
              chain,
              address,
            });
          });

          notify({
            title,
            message: t('actions.balances.blockchain_accounts_add.success.description', {
              address: account.address,
              list: !isAll ? getChainsText(chains) : '',
            }, isAll ? 1 : 2),
            severity: Severity.INFO,
            display: true,
          });
        }

        notifyFailed(result, title, account);
      }
      catch (error: any) {
        logger.error(error.message);
        failedAddition.push(account);
        // if there is only a single account do normal form validation
        if (payload.payload.length === 1)
          throw error;
      }
    };

    if (singleAddition)
      await addSingleAddress(payload.payload[0]);
    else
      await Promise.allSettled(payload.payload.map(addSingleAddress));

    if (failedAddition.length > 0) {
      const title = t('actions.balances.blockchain_accounts_add.task.title', { blockchain });
      const message = t('actions.balances.blockchain_accounts_add.error.failed_list_description', {
        list: failedAddition.map(({ address }) => `- ${address}`).join('\n'),
        address: payload.payload.length,
        blockchain,
      });

      notify({
        title,
        message,
        display: true,
      });
    }

    const finishAddition = async ({ chain, address }: Account) => {
      const modules = payload.modules;
      if (chain === Blockchain.ETH && modules) {
        await enableModule({
          enable: payload.modules,
          addresses: [address],
        });
      }

      if (supportsTransactions(chain))
        await fetchDetected(chain, [address]);
    };

    const finish = async () => {
      resetDefi();
      resetDefiStatus();
      resetNftSectionStatus();
      await refreshAccounts();

      const chains = get(supportedChains).map(chain => chain.id);

      // Sort accounts by chain, so they are called in order
      const accounts = successfulAddition.sort((a, b) => chains.indexOf(a.chain) - chains.indexOf(b.chain));
      await awaitParallelExecution(accounts, item => item.address + item.chain, finishAddition, 2);
    };

    startPromise(finish());
  };

  const addAccounts = async (chain: string, data: AddAccountsPayload | XpubAccountPayload): Promise<void> => {
    const taskType = TaskType.ADD_ACCOUNT;
    if (get(isTaskRunning(taskType))) {
      logger.debug(`${TaskType[taskType]} is already running.`);
      return;
    }
    const isXpub = 'xpub' in data;
    const filteredPayload = isXpub ? [] : getNewAccountPayload(chain, data.payload);
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

    const registeredAddresses: string[] = [];
    const failedPayload: AccountPayload[] = [];

    const singleAddition = filteredPayload.length === 1;
    const addSingleAddress = async (data: AccountPayload): Promise<void> => {
      try {
        const address = await addAccount(chain, [data]);
        if (address || isXpub)
          registeredAddresses.push(address);
      }
      catch (error: any) {
        logger.error(error.message);
        failedPayload.push(data);
        // if there is only a single account do normal form validation
        if (singleAddition)
          throw error;
      }
    };

    if (singleAddition)
      await addSingleAddress(filteredPayload[0]);
    else
      await Promise.allSettled(filteredPayload.map(addSingleAddress));

    const title = t('actions.balances.blockchain_accounts_add.task.title', { blockchain: chain });

    if (failedPayload.length > 0) {
      const message = t('actions.balances.blockchain_accounts_add.error.failed_list_description', {
        list: failedPayload.map(({ address }) => `- ${address}`).join('\n'),
        address: filteredPayload.length,
        blockchain: chain,
      });

      notify({
        title,
        message,
        display: true,
      });
    }

    if (registeredAddresses.length <= 0)
      return;

    const refresh = async () => {
      if (chain === Blockchain.ETH) {
        if ('modules' in data && data.modules)
          await enableModule({ enable: data.modules, addresses: registeredAddresses });

        resetDefi();
        resetDefiStatus();
        resetNftSectionStatus();
      }

      await refreshAccounts(chain);

      if (supportsTransactions(chain))
        await fetchDetected(chain, registeredAddresses);
    };

    try {
      await fetchAccounts(chain);
      startPromise(refresh());
    }
    catch (error: any) {
      logger.error(error);
      const description = t(
        'actions.balances.blockchain_accounts_add.error.description',
        {
          error: error.message,
          address: filteredPayload.length,
          blockchain: chain,
        },
      );
      notify({
        title,
        message: description,
        display: true,
      });
    }
  };

  const detectEvmAccounts = async () => {
    try {
      const taskType = TaskType.DETECT_EVM_ACCOUNTS;
      const { taskId } = await detectEvmAccountsCaller();
      const { result } = await awaitTask<any, TaskMeta>(taskId, taskType, {
        title: t('actions.detect_evm_accounts.task.title'),
      });

      return result;
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
