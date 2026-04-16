import type { AccountPayload, AddAccountsPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { RefreshAccountsParams } from '@/modules/accounts/use-account-operations';
import type { Module } from '@/modules/common/modules';
import { type Account, assert, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAdditionNotifications } from '@/modules/accounts/use-account-addition-notifications';
import { useBlockchainAccounts } from '@/modules/accounts/use-blockchain-accounts-api';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { awaitParallelExecution } from '@/modules/common/async/await-parallel-execution';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { logger } from '@/modules/common/logging/logging';
import { isBlockchain } from '@/modules/onchain/chains';
import { useTagOperations } from '@/modules/session/use-tag-operations';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

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

type FetchAccountsCallback = (blockchain?: string | string[], refreshEns?: boolean) => Promise<void>;

type EvmCompletionCallback = (params: EvmAccountAdditionParams) => Promise<void>;

type ChainCompletionCallback = (params: ChainAccountAdditionParams) => Promise<void>;

interface UseAccountAdditionServiceReturn {
  addMultipleAccounts: (payload: AccountPayload[], chain: string, modules: Module[] | undefined, onComplete: ChainCompletionCallback) => Promise<void>;
  addMultipleEvmAccounts: (payload: AddAccountsPayload, onComplete: EvmCompletionCallback) => Promise<void>;
  addSingleAccount: (account: AccountPayload | XpubAccountPayload, chain: string) => Promise<AccountAdditionSuccess | AccountAdditionFailure>;
  addSingleEvmAddress: (account: AccountPayload) => Promise<EvmAccountAdditionSuccess | EvmAccountAdditionFailure>;
  completeAccountAddition: (params: AccountAdditionParams, onRefreshAccounts: RefreshAccountsCallback, onFetchAccounts?: FetchAccountsCallback) => Promise<void>;
  getNewAccountPayload: (chain: string, payload: AccountPayload[]) => AccountPayload[];
}

export function useAccountAdditionService(): UseAccountAdditionServiceReturn {
  const { addAccount, addEvmAccount } = useBlockchainAccounts();
  const { detectTokens: detectTokensForChain } = useTokenDetectionOrchestrator();
  const { trackAddedAddresses } = useBlockchainAccountsStore();
  const { fetchTags } = useTagOperations();
  const { enableModule } = useSettingsOperations();
  const { evmChains, supportsTransactions } = useSupportedChains();
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
    onFetchAccounts?: FetchAccountsCallback,
  ): Promise<void> => {
    const {
      addedAccounts,
      chain,
      isXpub,
      modulesToEnable,
    } = params;

    // Refresh tags first in case new system tags (like 'Contract') were created
    await fetchTags();

    trackAddedAddresses(addedAccounts.map(item => item.address));

    const chainsSupportsTransactions = !chain || supportsTransactions(chain);
    if (chainsSupportsTransactions && onFetchAccounts) {
      // For EVM chains, only load account metadata without fetching balances.
      // Token detection runs next and explicitly triggers a balance refresh.
      await onFetchAccounts(chain, true);
    }
    else {
      await onRefreshAccounts({ addresses: addedAccounts.map(item => item.address), blockchain: chain, isXpub });
    }

    // Enable modules for ETH accounts
    if (modulesToEnable) {
      const ethAccounts = addedAccounts.filter(a => a.chain === Blockchain.ETH);
      for (const account of ethAccounts) {
        await enableModule({
          addresses: [account.address],
          enable: modulesToEnable,
        });
      }
    }

    // Group accounts by chain for token detection
    const accountsByChain = new Map<string, string[]>();
    for (const { address, chain: accountChain } of addedAccounts) {
      if (!supportsTransactions(accountChain))
        continue;

      const existing = accountsByChain.get(accountChain) ?? [];
      existing.push(address);
      accountsByChain.set(accountChain, existing);
    }

    // Detect tokens per chain — orchestrator handles queuing + balance refresh
    for (const [accountChain, chainAddresses] of accountsByChain) {
      await detectTokensForChain(accountChain, chainAddresses);
    }
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
    catch (error: unknown) {
      logger.error(getErrorMessage(error));
      return {
        account,
        error: error instanceof Error ? error : new Error(getErrorMessage(error)),
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
    catch (error: unknown) {
      logger.error(getErrorMessage(error));
      return {
        account,
        error: error instanceof Error ? error : new Error(getErrorMessage(error)),
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
