import { Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { type MaybeRef } from '@vueuse/core';
import { useNonFungibleBalancesStore } from '@/store/balances/non-fungible';
import {
  type AccountPayload,
  type AddAccountsPayload,
  type BaseAddAccountsPayload
} from '@/store/balances/types';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';
import { useBlockchainAccountsStore } from '@/store/blockchain/accounts';
import { useBlockchainBalancesStore } from '@/store/blockchain/balances';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useDefiStore } from '@/store/defi';
import { useNotificationsStore } from '@/store/notifications';
import { useSettingsStore } from '@/store/settings';
import { useStatusStore } from '@/store/status';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { startPromise } from '@/utils';
import { logger } from '@/utils/logging';
import { isBlockchain, isTokenChain } from '@/types/blockchain/chains';

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
  const { addEvmAccount } = useBlockchainAccountsApi();

  const { isTaskRunning } = useTasks();
  const { notify } = useNotificationsStore();
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
        startPromise(fetchNonFungibleBalances(true));
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
        await Promise.allSettled([
          detectAndRefresh(),
          fetchNonFungibleBalances(true)
        ]);
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

  return {
    addAccounts,
    addEvmAccounts,
    fetchAccounts,
    refreshAccounts
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainStore, import.meta.hot));
}
