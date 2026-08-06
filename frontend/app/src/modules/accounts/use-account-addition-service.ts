import type { ResultAsync } from 'plainfp/result-async';
import type { AccountPayload, AddAccountsPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { RefreshAccountsParams } from '@/modules/accounts/use-account-operations';
import type { Module } from '@/modules/core/common/modules';
import { type Account, assert, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { pipe } from 'plainfp';
import { err, isErr, mapError, ok } from 'plainfp/result';
import { useAccountAdditionNotifications } from '@/modules/accounts/use-account-addition-notifications';
import { useAccountAdditions } from '@/modules/accounts/use-account-additions';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { awaitParallelExecution } from '@/modules/core/common/async/await-parallel-execution';
import { isBlockchain } from '@/modules/core/common/chains';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useTagOperations } from '@/modules/tags/use-tag-operations';

/**
 * A failed addition, carrying the payload that failed so the caller can report it without
 * correlating by index. The old `{ type: 'success' | 'error' }` unions were a `Result` spelled by
 * hand, and (because `addAccount` signalled failure with `''`) the success branch also absorbed
 * cancellations.
 */
interface AccountAdditionFailure<T = AccountPayload | XpubAccountPayload> {
  error: TaskError;
  account: T;
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
  addSingleAccount: (account: AccountPayload | XpubAccountPayload, chain: string) => ResultAsync<string, AccountAdditionFailure>;
  addSingleEvmAddress: (account: AccountPayload) => ResultAsync<Account[], AccountAdditionFailure<AccountPayload>>;
  completeAccountAddition: (params: AccountAdditionParams, onRefreshAccounts: RefreshAccountsCallback, onFetchAccounts?: FetchAccountsCallback) => Promise<void>;
  getNewAccountPayload: (chain: string, payload: AccountPayload[]) => AccountPayload[];
}

export function useAccountAdditionService(): UseAccountAdditionServiceReturn {
  const { addAccount, addEvmAccount } = useAccountAdditions();
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

  const addSingleEvmAddress = async (account: AccountPayload): ResultAsync<Account[], AccountAdditionFailure<AccountPayload>> => {
    const addedAccounts: Account[] = [];

    const outcome = await addEvmAccount(account);
    if (isErr(outcome)) {
      // Only a real failure is worth a log line. A cancelled bulk add would otherwise write one
      // console error per in-flight address, which is the noise this branch exists to avoid.
      if (isActionable(outcome.error))
        logger.error(outcome.error.message);

      return err({ account, error: outcome.error });
    }

    const { added, ...result } = outcome.value;

    // `added` is an optional record, so `{}` is a valid response: truthy, but with no entry to
    // destructure. That threw `undefined is not iterable`, which the removed try/catch used to
    // turn into a failure result and now escapes as a rejection.
    const [addedEntry] = Object.entries(added ?? {});

    if (addedEntry) {
      const [address, chains] = addedEntry;
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

    return ok(addedAccounts);
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
        // Only a real failure is reported. Cancelling the group mid-add would otherwise raise
        // "failed to add N of M addresses" for work the user deliberately stopped.
        if (isErr(result)) {
          if (isActionable(result.error.error))
            failedToAddAccounts.push(result.error.account);
        }
        else {
          addedAccounts.push(...result.value);
        }
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
  ): ResultAsync<string, AccountAdditionFailure> => pipe(
    await addAccount(chain, 'xpub' in account ? account : [account]),
    mapError((error: TaskError) => {
      // As in `addSingleEvmAddress`: a cancellation is not a failure to log.
      if (isActionable(error))
        logger.error(error.message);

      return { account, error };
    }),
  );

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
        // As above: a cancellation is not a failure to report.
        if (isErr(result)) {
          if (isActionable(result.error.error)) {
            assert(!('xpub' in result.error.account));
            failedToAddAccounts.push(result.error.account);
          }
        }
        else {
          addedAccounts.push({ address: result.value, chain });
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
