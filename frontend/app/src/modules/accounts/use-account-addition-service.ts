import type { ResultAsync } from 'plainfp/result-async';
import type { AccountPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { FetchAccountsParams, RefreshAccountsParams } from '@/modules/accounts/use-account-operations';
import type { Module } from '@/modules/core/common/modules';
import { type Account, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { pipe } from 'plainfp';
import { err, isErr, mapError, map as mapResult, ok, type Result } from 'plainfp/result';
import { isEveryEvmChain, useAccountAdditionBatch } from '@/modules/accounts/use-account-addition-batch';
import { useAccountAdditionNotifications } from '@/modules/accounts/use-account-addition-notifications';
import { type AdditionOptions, useAccountAdditions } from '@/modules/accounts/use-account-additions';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
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
export interface AccountAdditionFailure<T = AccountPayload | XpubAccountPayload> {
  error: TaskError;
  account: T;
}

// Callback types for account addition completion
export interface AccountAdditionParams {
  addedAccounts: Account[];
  modulesToEnable?: Module[];
  chain?: string;
  isXpub?: boolean;
}

/**
 * What an addition did, for the caller to present. Returned rather than thrown, so the *caller*
 * decides the experience instead of the address count deciding it: one address used to throw (form
 * dialog stays open) while two reported through a toast and closed the dialog as a success, even
 * when some of them failed.
 */
export interface AdditionSummary {
  readonly added: Account[];
  /**
   * Both payload kinds: an xpub can fail too, and the caller still has to hear about it. Each entry
   * keeps its `TaskError`, so a form caller can still reach an `ApiValidationError` cause and fill
   * in per-field errors instead of flattening every rejection into one generic message.
   */
  readonly failed: AccountAdditionFailure[];
  /** True when every failure was a cancellation, so nothing is worth reporting. */
  readonly cancelled: boolean;
}

type RefreshAccountsCallback = (params: RefreshAccountsParams) => Promise<void>;

type FetchAccountsCallback = (params?: FetchAccountsParams) => Promise<void>;

type CompletionCallback = (params: AccountAdditionParams) => Promise<void>;

interface UseAccountAdditionServiceReturn {
  /**
   * Adds every payload entry to `chain`, which may be {@link EVM_PSEUDO_CHAIN} for "every EVM
   * chain". One function, because that is one operation with one parameter varying.
   */
  addAccounts: (chain: string, payload: AccountPayload[] | XpubAccountPayload, modules: Module[] | undefined, onComplete: CompletionCallback, options?: AdditionOptions) => Promise<AdditionSummary>;
  addSingleAccount: (account: AccountPayload | XpubAccountPayload, chain: string, options?: AdditionOptions) => ResultAsync<string, AccountAdditionFailure>;
  addSingleEvmAddress: (account: AccountPayload, options?: AdditionOptions) => ResultAsync<Account[], AccountAdditionFailure<AccountPayload>>;
  completeAccountAddition: (params: AccountAdditionParams, onRefreshAccounts: RefreshAccountsCallback, onFetchAccounts: FetchAccountsCallback) => Promise<void>;
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
  const { runAdditionBatch, runEvmAdditionBatch } = useAccountAdditionBatch();
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
    onFetchAccounts: FetchAccountsCallback,
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

    // ⚠️ §6's known exception, and it is correct: a chain that will detect deliberately skips its
    // own balance read, because detection ends in one. Only a chain that cannot hold tokens has to
    // ask for balances itself.
    if (chain !== undefined && !supportsTransactions(chain)) {
      await onRefreshAccounts({ addresses: addedAccounts.map(item => item.address), blockchain: chain, isXpub });
    }
    else {
      await onFetchAccounts({ blockchain: chain, refreshEns: true });
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

  const addSingleEvmAddress = async (
    account: AccountPayload,
    options?: AdditionOptions,
  ): ResultAsync<Account[], AccountAdditionFailure<AccountPayload>> => {
    const addedAccounts: Account[] = [];

    const outcome = await addEvmAccount(account, options);
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

  const addSingleAccount = async (
    account: AccountPayload | XpubAccountPayload,
    chain: string,
    options?: AdditionOptions,
  ): ResultAsync<string, AccountAdditionFailure> => pipe(
    await addAccount(chain, 'xpub' in account ? account : [account], options),
    mapError((error: TaskError) => {
      // As in `addSingleEvmAddress`: a cancellation is not a failure to log.
      if (isActionable(error))
        logger.error(error.message);

      return { account, error };
    }),
  );

  /**
   * The one addition path. Every entry fans out through the batch — including a single one, where
   * the batch suppresses the umbrella — so the address count no longer changes the mechanism, only
   * how it is presented.
   *
   * No limiter here: the `accounts-add:<chain>` lane caps this at 2.
   */
  const addAccounts = async (
    chain: string,
    payload: AccountPayload[] | XpubAccountPayload,
    modules: Module[] | undefined,
    onComplete: CompletionCallback,
    options?: AdditionOptions,
  ): Promise<AdditionSummary> => {
    const addedAccounts: Account[] = [];
    const failed: AccountAdditionFailure[] = [];
    let cancelled = false;

    const isXpub = 'xpub' in payload;
    const everyEvmChain = isEveryEvmChain(chain);

    const collect = (result: Result<Account[], AccountAdditionFailure<AccountPayload | XpubAccountPayload>>): void => {
      if (!isErr(result)) {
        addedAccounts.push(...result.value);
        return;
      }

      // A cancellation is recorded, never reported: the user asked for it, so neither the failure
      // list nor "failed to add N of M addresses" should mention it.
      if (!isActionable(result.error.error)) {
        cancelled = true;
        return;
      }

      failed.push(result.error);
    };

    if (isXpub) {
      // One xpub is one unit of work, so there is nothing to fan out — but it still returns the
      // same summary, so the caller has one shape to handle.
      collect(mapResult(
        await addSingleAccount(payload, chain, options),
        address => [{ address, chain }],
      ));
    }
    else if (everyEvmChain) {
      const results = await runEvmAdditionBatch(
        payload,
        account => account.address,
        // No options object when there is no umbrella: a single-item batch with no outer parent has
        // nothing to attach to, and `{ parent: undefined }` would only be noise on the way down.
        async (account, parent) => addSingleEvmAddress(account, parent ? { parent } : undefined),
        options?.parent,
      );
      results.forEach(result => collect(result));
    }
    else {
      const results = await runAdditionBatch(
        chain,
        payload,
        account => account.address,
        async (account, parent) => addSingleAccount(account, chain, parent ? { parent } : undefined),
        options?.parent,
      );
      results.forEach(result => collect(mapResult(result, address => [{ address, chain }])));
    }

    // The notification lists addresses, so an xpub failure is not one of its rows — the caller
    // reports that from the summary instead.
    const failedAddresses = failed
      .map(failure => failure.account)
      .filter((account): account is AccountPayload => !('xpub' in account));
    if (failedAddresses.length > 0)
      notifyFailedToAddAddress(failedAddresses, isXpub ? 1 : payload.length, everyEvmChain ? undefined : chain);

    startPromise(onComplete({
      addedAccounts,
      chain: everyEvmChain ? undefined : chain,
      isXpub,
      modulesToEnable: modules,
    }));

    return { added: addedAccounts, cancelled, failed };
  };

  return {
    addAccounts,
    addSingleAccount,
    addSingleEvmAddress,
    completeAccountAddition,
    getNewAccountPayload,
  };
}
