/* eslint-disable max-lines */
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { TaskType } from '@/types/task-type';
import { isBlockchain } from '@/types/blockchain/chains';
import { Section } from '@/types/status';
import { useAccountsAddresses } from '@/composables/accounts/addresses';
import type { Account } from '@rotki/common/lib/account';
import type { MaybeRef } from '@vueuse/core';
import type {
  AccountPayload,
  AddAccountsPayload,
  BaseAddAccountsPayload,
} from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import type { AddressBookSimplePayload } from '@/types/eth-names';

export function useBlockchains() {
  const { addAccount, fetch, addEvmAccount } = useBlockchainAccounts();
  const { getAccountsByChain } = useAccountBalances();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { fetchLoopringBalances } = useEthBalancesStore();
  const { fetchDetected } = useBlockchainTokensStore();
  const { enableModule } = useSettingsStore();
  const { reset: resetDefi } = useDefiStore();
  const { resetDefiStatus } = useStatusStore();
  const { detectEvmAccounts: detectEvmAccountsCaller }
    = useBlockchainAccountsApi();
  const { getChainName, supportsTransactions, evmChains, isEvm } = useSupportedChains();

  const { isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const { resetStatus: resetNftSectionStatus } = useStatusUpdater(
    Section.NON_FUNGIBLE_BALANCES,
  );

  const getNewAccountPayload = (
    chain: Blockchain,
    payload: AccountPayload[],
  ): AccountPayload[] => {
    const knownAddresses = getAccountsByChain(chain);
    return payload.filter(({ xpub, address }) => {
      const key = (xpub?.xpub || address).toLocaleLowerCase();

      return !knownAddresses.includes(key);
    });
  };

  const { fetchEnsNames } = useAddressesNamesStore();
  const { allAddressMapping } = useAccountsAddresses();

  const fetchAccounts = async (
    blockchain?: Blockchain,
    refreshEns: boolean = false,
  ): Promise<void> => {
    const chains = blockchain ? [blockchain] : Object.values(Blockchain);
    await Promise.allSettled(chains.map(fetch));

    const namesPayload: AddressBookSimplePayload[] = [];
    const addressesMapping = get(allAddressMapping);

    chains.forEach((chain) => {
      if (!get(isEvm(chain)))
        return;

      const addresses = addressesMapping[chain];
      namesPayload.push(...addresses.map(address => ({ address, blockchain: chain })));
    });

    if (namesPayload.length > 0)
      startPromise(fetchEnsNames(namesPayload, refreshEns));
  };

  const refreshAccounts = async (
    blockchain?: MaybeRef<Blockchain>,
    periodic = false,
  ) => {
    const chain = get(blockchain);
    await fetchAccounts(chain, true);

    const isEth = chain === Blockchain.ETH;
    const isEth2 = chain === Blockchain.ETH2;

    const pending: Promise<any>[] = [
      fetchBlockchainBalances(
        {
          blockchain: chain,
          ignoreCache: isEth2,
        },
        periodic,
      ),
    ];

    if (isEth || !chain) {
      pending.push(fetchLoopringBalances(false));

      if (isEth)
        startPromise(refreshAccounts(Blockchain.ETH2));
    }

    await Promise.allSettled(pending);
  };

  const addEvmAccounts = async (
    payload: BaseAddAccountsPayload,
  ): Promise<void> => {
    const blockchain = 'EVM';

    const accountsToFinish: Account<Blockchain>[] = [];
    const finishAddition = async ({ chain, address }: Account<Blockchain>) => {
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

    const promiseResult = await Promise.allSettled(
      payload.payload.map(async (account) => {
        const add = await addEvmAccount(account);
        const { added, existed, failed, noActivity, ethContracts } = add;

        const notificationTitle = t(
          'actions.balances.blockchain_accounts_add.task.title',
          {
            blockchain,
          },
        );

        const getChainsText = (chains: string[], explanation?: string) =>
          chains
            .map((chain) => {
              let text = `- ${get(getChainName(chain))}`;
              if (explanation)
                text += ` (${explanation})`;

              return text;
            })
            .join('\n');

        if (added) {
          const [address, chains] = Object.entries(added)[0];

          const isAll = chains.length === 1 && chains[0] === 'all';

          const usedChains = isAll ? get(evmChains) : chains;

          usedChains.forEach((chain) => {
            if (!isBlockchain(chain)) {
              logger.error(`${chain} was not a valid blockchain`);
              return;
            }

            accountsToFinish.push({
              chain,
              address,
            });
          });

          notify({
            title: notificationTitle,
            message: t(
              'actions.balances.blockchain_accounts_add.success.description',
              {
                address: account.address,
                list: !isAll ? getChainsText(chains) : '',
              },
              isAll ? 1 : 2,
            ),
            severity: Severity.INFO,
            display: true,
          });
        }

        const listOfFailureText = [];
        if (noActivity) {
          listOfFailureText.push(
            getChainsText(
              Object.values(noActivity)[0],
              t(
                'actions.balances.blockchain_accounts_add.error.failed_reason.no_activity',
              ),
            ),
          );
        }

        if (existed) {
          listOfFailureText.push(
            getChainsText(
              Object.values(existed)[0],
              t(
                'actions.balances.blockchain_accounts_add.error.failed_reason.existed',
              ),
            ),
          );
        }

        if (ethContracts) {
          listOfFailureText.push(
            getChainsText(
              [t('actions.balances.blockchain_accounts_add.error.non_eth')],
              t(
                'actions.balances.blockchain_accounts_add.error.failed_reason.is_contract',
              ),
            ),
          );
        }

        if (failed)
          listOfFailureText.push(getChainsText(Object.values(failed)[0]));

        if (listOfFailureText.length > 0) {
          return notify({
            title: notificationTitle,
            message: t(
              'actions.balances.blockchain_accounts_add.error.failed',
              {
                address: account.address,
                list: listOfFailureText.join('\n'),
              },
            ),
            display: true,
          });
        }
      }),
    );

    const failedPayload: AccountPayload[] = [];
    if (
      payload.payload.length === 1
      && promiseResult[0].status === 'rejected'
    )
      throw promiseResult[0].reason;

    promiseResult.forEach((res, index) => {
      if (res.status === 'rejected') {
        logger.error(res.reason.message);
        failedPayload.push(payload.payload[index]);
      }
    });

    if (failedPayload.length > 0) {
      const titleError = t(
        'actions.balances.blockchain_accounts_add.task.title',
        { blockchain },
      );
      const description = t(
        'actions.balances.blockchain_accounts_add.error.failed_list_description',
        {
          list: failedPayload.map(({ address }) => `- ${address}`).join('\n'),
          address: payload.payload.length,
          blockchain,
        },
      );

      notify({
        title: titleError,
        message: description,
        display: true,
      });
    }

    const finish = async () => {
      resetDefi();
      resetDefiStatus();
      resetNftSectionStatus();

      await refreshAccounts();

      const chains = Object.values(Blockchain);

      // Sort accounts by chain, so they are called in order
      const accounts = accountsToFinish.sort((a, b) => chains.indexOf(a.chain) - chains.indexOf(b.chain));
      await awaitParallelExecution(accounts, item => item.address + item.chain, finishAddition);
    };

    startPromise(finish());
  };

  const addAccounts = async ({
    blockchain,
    payload,
    modules,
  }: AddAccountsPayload): Promise<void> => {
    const taskType = TaskType.ADD_ACCOUNT;
    if (get(isTaskRunning(taskType))) {
      logger.debug(`${TaskType[taskType]} is already running.`);
      return;
    }
    const filteredPayload = getNewAccountPayload(blockchain, payload);
    if (filteredPayload.length === 0) {
      const title = t('actions.balances.blockchain_accounts_add.task.title', {
        blockchain: get(getChainName(blockchain)),
      });
      const description = t(
        'actions.balances.blockchain_accounts_add.no_new.description',
      );
      notify({
        title,
        message: description,
        severity: Severity.INFO,
        display: true,
      });
      return;
    }

    const registeredAddresses: string[] = [];
    const promiseResult = await Promise.allSettled(
      filteredPayload.map(data => addAccount(blockchain, data)),
    );

    const failedPayload: AccountPayload[] = [];

    if (
      filteredPayload.length === 1
      && promiseResult[0].status === 'rejected'
    )
      throw promiseResult[0].reason;

    const isXpub = payload.length === 1 && payload[0].xpub;

    promiseResult.forEach((res, index) => {
      if (res.status === 'fulfilled' && (res.value !== '' || isXpub)) {
        registeredAddresses.push(res.value);
      }
      else {
        if (res.status === 'rejected')
          logger.error(res.reason.message);

        failedPayload.push(payload[index]);
      }
    });

    const titleError = t(
      'actions.balances.blockchain_accounts_add.task.title',
      { blockchain },
    );

    if (failedPayload.length > 0) {
      const description = t(
        'actions.balances.blockchain_accounts_add.error.failed_list_description',
        {
          list: failedPayload.map(({ address }) => `- ${address}`).join('\n'),
          address: filteredPayload.length,
          blockchain,
        },
      );

      notify({
        title: titleError,
        message: description,
        display: true,
      });
    }

    if (registeredAddresses.length > 0) {
      const refresh = async () => {
        if (blockchain === Blockchain.ETH) {
          if (modules) {
            await enableModule({
              enable: modules,
              addresses: registeredAddresses,
            });
          }

          resetDefi();
          resetDefiStatus();
          resetNftSectionStatus();
        }

        await refreshAccounts(blockchain);

        if (supportsTransactions(blockchain))
          await fetchDetected(blockchain, registeredAddresses);
      };
      try {
        await fetchAccounts(blockchain);
        startPromise(refresh());
      }
      catch (error: any) {
        logger.error(error);
        const description = t(
          'actions.balances.blockchain_accounts_add.error.description',
          {
            error: error.message,
            address: filteredPayload.length,
            blockchain,
          },
        );
        notify({
          title: titleError,
          message: description,
          display: true,
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
        title: t('actions.detect_evm_accounts.task.title').toString(),
      });

      return result;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          title: t('actions.detect_evm_accounts.error.title').toString(),
          message: t('actions.detect_evm_accounts.error.message', {
            message: error.message,
          }).toString(),
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
