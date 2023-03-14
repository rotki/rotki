import { Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { type MaybeRef } from '@vueuse/core';
import { TaskType } from '@/types/task-type';
import { startPromise } from '@/utils';
import { logger } from '@/utils/logging';
import { isBlockchain, isTokenChain } from '@/types/blockchain/chains';
import {
  type AccountPayload,
  type AddAccountsPayload,
  type BaseAddAccountsPayload
} from '@/types/blockchain/accounts';
import { type TaskMeta } from '@/types/task';
import { useStatusUpdater } from '@/composables/status';
import { Section } from '@/types/status';

export const useBlockchains = () => {
  const { addAccount, fetch, addEvmAccount } = useBlockchainAccounts();
  const { getAccountsByChain } = useAccountBalances();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { fetchLoopringBalances } = useEthBalancesStore();
  const { fetchDetected } = useBlockchainTokensStore();
  const { enableModule } = useSettingsStore();
  const { reset: resetDefi } = useDefiStore();
  const { resetDefiStatus } = useStatusStore();
  const { detectEvmAccounts: detectEvmAccountsCaller } =
    useBlockchainAccountsApi();

  const { isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { tc } = useI18n();

  const { resetStatus: resetNftSectionStatus } = useStatusUpdater(
    Section.NON_FUNGIBLE_BALANCES
  );

  const getNewAccountPayload = (
    chain: Blockchain,
    payload: AccountPayload[]
  ): AccountPayload[] => {
    const knownAddresses = getAccountsByChain(chain);
    return payload.filter(({ xpub, address }) => {
      const key = (xpub?.xpub || address!).toLocaleLowerCase();

      return !knownAddresses.includes(key);
    });
  };

  const fetchAccounts = async (blockchain?: Blockchain): Promise<void> => {
    const promises: Promise<any>[] = [];

    const chains = Object.values(Blockchain);
    if (!blockchain) {
      promises.push(...chains.map(chain => fetch(chain)));
    } else {
      promises.push(fetch(blockchain));
    }

    await Promise.allSettled(promises);
  };

  const refreshAccounts = async (blockchain?: MaybeRef<Blockchain>) => {
    const chain = get(blockchain);
    await fetchAccounts(chain);

    const isEth = chain === Blockchain.ETH;
    const isEth2 = chain === Blockchain.ETH2;

    const pending: Promise<any>[] = [
      fetchBlockchainBalances({
        blockchain: chain,
        ignoreCache: isEth2
      })
    ];

    if (isEth || !chain) {
      pending.push(fetchLoopringBalances(false));

      if (isEth) {
        startPromise(refreshAccounts(Blockchain.ETH2));
      }
    }

    await Promise.allSettled(pending);
  };

  const addEvmAccounts = async (
    payload: BaseAddAccountsPayload
  ): Promise<void> => {
    const finishAddition = async (chain: Blockchain, addresses: string[]) => {
      const modules = payload.modules;
      if (chain === Blockchain.ETH) {
        if (modules) {
          await enableModule({
            enable: payload.modules,
            addresses
          });
        }
        resetDefi();
        resetDefiStatus();
        resetNftSectionStatus();
      }

      if (isTokenChain(chain)) {
        await fetchDetected(chain, addresses);
      }
      await refreshAccounts(chain);
    };

    const promiseResult = await Promise.allSettled(
      payload.payload.map(async p => {
        const addresses = await addEvmAccount(p);
        for (const chain in addresses) {
          if (!isBlockchain(chain)) {
            logger.error(`${chain} was not a valid blockchain`);
            continue;
          }
          startPromise(finishAddition(chain, addresses[chain]));
        }
      })
    );

    const failedPayload: AccountPayload[] = [];
    if (
      payload.payload.length === 1 &&
      promiseResult[0].status === 'rejected'
    ) {
      throw promiseResult[0].reason;
    }

    promiseResult.forEach((res, index) => {
      if (res.status === 'rejected') {
        logger.error(res.reason.message);
        failedPayload.push(payload.payload[index]);
      }
    });

    if (failedPayload.length > 0) {
      const titleError = tc(
        'actions.balances.blockchain_accounts_add.error.title',
        0,
        { blockchain: 'EVM' }
      );
      const description = tc(
        'actions.balances.blockchain_accounts_add.error.failed_list_description',
        0,
        {
          list: failedPayload.map(({ address }) => `- ${address}`).join('\n'),
          address: payload.payload.length,
          blockchain: 'EVM'
        }
      );

      notify({
        title: titleError,
        message: description,
        display: true
      });
    }
  };

  const addAccounts = async ({
    blockchain,
    payload,
    modules
  }: AddAccountsPayload): Promise<void> => {
    if (get(isTaskRunning(TaskType.ADD_ACCOUNT))) {
      logger.debug(`${TaskType[TaskType.ADD_ACCOUNT]} is already running.`);
      return;
    }
    const filteredPayload = getNewAccountPayload(blockchain, payload);
    if (filteredPayload.length === 0) {
      const title = tc(
        'actions.balances.blockchain_accounts_add.no_new.title',
        0,
        { blockchain }
      );
      const description = tc(
        'actions.balances.blockchain_accounts_add.no_new.description'
      );
      notify({
        title,
        message: description,
        severity: Severity.INFO,
        display: true
      });
      return;
    }

    const registeredAddresses: string[] = [];
    const promiseResult = await Promise.allSettled(
      filteredPayload.map(data => addAccount(blockchain, data))
    );

    const failedPayload: AccountPayload[] = [];

    if (
      filteredPayload.length === 1 &&
      promiseResult[0].status === 'rejected'
    ) {
      throw promiseResult[0].reason;
    }

    const isXpub = payload.length === 1 && payload[0].xpub;

    promiseResult.forEach((res, index) => {
      if (res.status === 'fulfilled' && (res.value !== '' || isXpub)) {
        registeredAddresses.push(res.value);
      } else {
        if (res.status === 'rejected') {
          logger.error(res.reason.message);
        }
        failedPayload.push(payload[index]);
      }
    });

    const titleError = tc(
      'actions.balances.blockchain_accounts_add.error.title',
      0,
      { blockchain }
    );

    if (failedPayload.length > 0) {
      const description = tc(
        'actions.balances.blockchain_accounts_add.error.failed_list_description',
        0,
        {
          list: failedPayload.map(({ address }) => `- ${address}`).join('\n'),
          address: filteredPayload.length,
          blockchain
        }
      );

      notify({
        title: titleError,
        message: description,
        display: true
      });
    }

    if (registeredAddresses.length > 0) {
      const refresh = async () => {
        if (blockchain === Blockchain.ETH && modules) {
          await enableModule({
            enable: modules,
            addresses: registeredAddresses
          });
        }
        resetDefi();
        resetDefiStatus();
        const detectAndRefresh = async () => {
          if (isTokenChain(blockchain)) {
            await fetchDetected(blockchain, registeredAddresses);
          }
          await refreshAccounts(blockchain);
        };
        await Promise.allSettled([detectAndRefresh()]);
        resetNftSectionStatus();
      };
      try {
        await fetchAccounts(blockchain);
        startPromise(refresh());
      } catch (e: any) {
        logger.error(e);
        const description = tc(
          'actions.balances.blockchain_accounts_add.error.description',
          0,
          {
            error: e.message,
            address: filteredPayload.length,
            blockchain
          }
        );
        notify({
          title: titleError,
          message: description,
          display: true
        });
      }
    }
  };

  const { awaitTask } = useTaskStore();
  const detectEvmAccounts = async () => {
    try {
      const taskType = TaskType.DETECT_EVM_ACCOUNTS;
      const { taskId } = await detectEvmAccountsCaller();
      const { result } = await awaitTask<any, TaskMeta>(taskId, taskType, {
        title: tc('actions.detect_evm_accounts.task.title').toString()
      });

      return result;
    } catch (e: any) {
      logger.error(e);
      notify({
        title: tc('actions.detect_evm_accounts.error.title').toString(),
        message: tc('actions.detect_evm_accounts.error.message', 0, {
          message: e.message
        }).toString(),
        display: true
      });
    }
  };

  return {
    addAccounts,
    addEvmAccounts,
    detectEvmAccounts,
    fetchAccounts,
    refreshAccounts
  };
};
