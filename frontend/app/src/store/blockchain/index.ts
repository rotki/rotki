import { Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { MaybeRef } from '@vueuse/core';
import { useNonFungibleBalancesStore } from '@/store/balances/non-fungible';
import { AccountPayload, AddAccountsPayload } from '@/store/balances/types';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';
import { useBlockchainAccountsStore } from '@/store/blockchain/accounts';
import { useBlockchainBalancesStore } from '@/store/blockchain/balances';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useDefiStore } from '@/store/defi';
import { useNotifications } from '@/store/notifications';
import { useSettingsStore } from '@/store/settings';
import { useStatusStore } from '@/store/status';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { startPromise } from '@/utils';
import { logger } from '@/utils/logging';

export const useBlockchainStore = defineStore('blockchain', () => {
  const { addAccount, fetch } = useBlockchainAccountsStore();
  const { getAccountsByChain } = useAccountBalancesStore();
  const { fetchBlockchainBalances } = useBlockchainBalancesStore();
  const { fetchNonFungibleBalances } = useNonFungibleBalancesStore();
  const { fetchLoopringBalances } = useEthBalancesStore();
  const { fetchDetected } = useBlockchainTokensStore();
  const { enableModule } = useSettingsStore();
  const { reset: resetDefi } = useDefiStore();
  const { resetDefiStatus } = useStatusStore();

  const { isTaskRunning } = useTasks();
  const { notify } = useNotifications();
  const { tc } = useI18n();

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
    const pending: Promise<any>[] = [
      fetchBlockchainBalances({
        blockchain: chain,
        ignoreCache: false
      })
    ];

    const isEth = chain === Blockchain.ETH;

    if (isEth || !chain) {
      pending.push(
        fetchBlockchainBalances({
          blockchain: Blockchain.ETH2,
          ignoreCache: false
        })
      );
      pending.push(fetchLoopringBalances(false));
    }

    await Promise.allSettled(pending);
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

    if (filteredPayload.length === 1) {
      if (promiseResult[0].status === 'rejected') {
        throw promiseResult[0].reason;
      }
    }

    promiseResult.forEach((res, index) => {
      if (res.status === 'fulfilled' && res.value !== '') {
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
      try {
        if (blockchain === Blockchain.ETH && modules) {
          await enableModule({
            enable: modules,
            addresses: registeredAddresses
          });
        }
        resetDefi();
        resetDefiStatus();
        if (blockchain === Blockchain.ETH) {
          await fetchDetected(registeredAddresses);
        }
        startPromise(fetchNonFungibleBalances());
        startPromise(refreshAccounts(blockchain));
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

  return {
    addAccounts,
    fetchAccounts,
    refreshAccounts
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainStore, import.meta.hot));
}
