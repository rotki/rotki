import type { RefreshAccountsParams } from '@/composables/blockchain/use-account-operations';
import type { AccountPayload, AddAccountsPayload, XpubAccountPayload } from '@/types/blockchain/accounts';
import type { Module } from '@/types/modules';
import { type Account, assert, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useBlockchainAccounts } from '@/composables/blockchain/accounts';
import { useAccountAdditionNotifications } from '@/composables/blockchain/use-account-addition-notifications';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useSettingsStore } from '@/store/settings';
import { isBlockchain } from '@/types/blockchain/chains';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { logger } from '@/utils/logging';

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

// Callback types for account addition completion
interface AccountAdditionParams {
  addedAccounts: Account[];
  modulesToEnable?: Module[];
  chain?: string;
  isXpub?: boolean;
}

interface EvmAccountAdditionParams {
  addedAccounts: Account[];
  modulesToEnable?: Module[];
}

interface ChainAccountAdditionParams {
  addedAccounts: Account[];
  chain: string;
  modulesToEnable?: Module[];
}

type RefreshAccountsCallback = (params: RefreshAccountsParams) => Promise<void>;

type EvmCompletionCallback = (params: EvmAccountAdditionParams) => Promise<void>;

type ChainCompletionCallback = (params: ChainAccountAdditionParams) => Promise<void>;

function CHAIN_ORDER_COMPARATOR(chains: string[]): (a: Account, b: Account) => number {
  return (
    a: Account,
    b: Account,
  ): number => chains.indexOf(a.chain) - chains.indexOf(b.chain);
}

interface UseAccountAdditionServiceReturn {
  addMultipleAccounts: (payload: AccountPayload[], chain: string, modules: Module[] | undefined, onComplete: ChainCompletionCallback) => Promise<void>;
  addMultipleEvmAccounts: (payload: AddAccountsPayload, onComplete: EvmCompletionCallback) => Promise<void>;
  addSingleAccount: (account: AccountPayload | XpubAccountPayload, chain: string) => Promise<AccountAdditionSuccess | AccountAdditionFailure>;
  addSingleEvmAddress: (account: AccountPayload) => Promise<EvmAccountAdditionSuccess | EvmAccountAdditionFailure>;
  completeAccountAddition: (params: AccountAdditionParams, onRefreshAccounts: RefreshAccountsCallback) => Promise<void>;
  getNewAccountPayload: (chain: string, payload: AccountPayload[]) => AccountPayload[];
}

export function useAccountAdditionService(): UseAccountAdditionServiceReturn {
  const { addAccount, addEvmAccount } = useBlockchainAccounts();
  const { fetchDetected } = useBlockchainTokensStore();
  const { enableModule } = useSettingsStore();
  const { evmChains, supportedChains, supportsTransactions } = useSupportedChains();
  const { getAddresses } = useAccountAddresses();
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

  const completeAccountAddition = async (
    params: AccountAdditionParams,
    onRefreshAccounts: RefreshAccountsCallback,
  ): Promise<void> => {
    const {
      addedAccounts,
      chain,
      isXpub,
      modulesToEnable,
    } = params;

    await onRefreshAccounts({ addresses: addedAccounts.map(item => item.address), blockchain: chain, isXpub });
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

  const addMultipleEvmAccounts = async (
    payload: AddAccountsPayload,
    onComplete: EvmCompletionCallback,
  ): Promise<void> => {
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

    startPromise(onComplete({ addedAccounts, modulesToEnable: payload.modules }));
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

  const addMultipleAccounts = async (
    payload: AccountPayload[],
    chain: string,
    modules: Module[] | undefined,
    onComplete: ChainCompletionCallback,
  ): Promise<void> => {
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

    startPromise(onComplete({ addedAccounts, chain, modulesToEnable: modules }));
  };

  return {
    addMultipleAccounts,
    addMultipleEvmAccounts,
    addSingleAccount,
    addSingleEvmAddress,
    completeAccountAddition,
    getNewAccountPayload,
  };
}
