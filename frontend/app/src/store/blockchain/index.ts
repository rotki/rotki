import { Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { useNonFungibleBalancesStore } from '@/store/balances/non-funginble';
import { AddAccountsPayload } from '@/store/balances/types';
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
  const { fetchNonFunginbleBalances } = useNonFungibleBalancesStore();
  const { fetchLoopringBalances } = useEthBalancesStore();
  const { fetchDetected } = useBlockchainTokensStore();
  const { enableModule } = useSettingsStore();

  const { isTaskRunning } = useTasks();
  const { notify } = useNotifications();
  const { tc } = useI18n();

  const getNewAddresses = (
    chain: Blockchain,
    addresses: string[]
  ): string[] => {
    const knownAddresses = getAccountsByChain(chain);
    return addresses.filter(
      address => !knownAddresses.includes(address.toLocaleLowerCase())
    );
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

  const refreshAccounts = async (blockchain?: Blockchain) => {
    await fetchAccounts(blockchain);
    const pending: Promise<any>[] = [
      fetchBlockchainBalances({
        blockchain,
        ignoreCache: true
      })
    ];

    if (blockchain === Blockchain.ETH) {
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

    const addresses = getNewAddresses(
      blockchain,
      payload.map(({ address }) => address)
    );
    if (addresses.length === 0) {
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

    try {
      const addr = await Promise.all(
        payload.map(data => addAccount(blockchain, data))
      );
      if (blockchain === Blockchain.ETH && modules) {
        await enableModule({
          enable: modules,
          addresses
        });
      }
      useDefiStore().reset();
      useStatusStore().resetDefiStatus();
      if (blockchain === Blockchain.ETH) {
        await fetchDetected(addr.filter(add => add.length > 0));
      }
      startPromise(fetchNonFunginbleBalances());
      startPromise(refreshAccounts(blockchain));
    } catch (e: any) {
      logger.error(e);
      const title = tc(
        'actions.balances.blockchain_accounts_add.error.title',
        0,
        { blockchain }
      );
      const description = tc(
        'actions.balances.blockchain_accounts_add.error.description',
        0,
        {
          error: e.message,
          address: addresses.length,
          blockchain
        }
      );
      notify({
        title,
        message: description,
        display: true
      });
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
