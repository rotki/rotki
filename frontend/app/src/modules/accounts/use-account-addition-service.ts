import type { Account } from '@rotki/common';
import type { ResultAsync } from 'plainfp/result-async';
import type { AccountPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { Module } from '@/modules/core/common/modules';
import { startPromise } from '@shared/utils';
import { get } from '@vueuse/shared';
import { pipe } from 'plainfp';
import { err, isErr, mapError, map as mapResult, ok, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { isEveryEvmChain, useAccountAdditionBatch } from '@/modules/accounts/use-account-addition-batch';
import { type AccountAdditionParams, useAccountAdditionCompletion, type UseAccountAdditionCompletionReturn } from '@/modules/accounts/use-account-addition-completion';
import { type AdditionOptions, useAccountAdditions } from '@/modules/accounts/use-account-additions';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { isBlockchain } from '@/modules/core/common/chains';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';

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

/**
 * What an addition did, for the caller to present.
 *
 * @remarks
 * Returned rather than thrown, so the caller decides the experience rather than the address count
 * deciding it. A form can hold its dialog open on failure while a bulk import only tallies.
 */
export interface AdditionSummary {
  readonly added: Account[];
  /**
   * Both payload kinds: an xpub can fail too, and the caller still has to hear about it. Each entry
   * keeps its `TaskError`, so a form caller can still reach an `ApiValidationError` cause and fill
   * in per-field errors instead of flattening every rejection into one generic message.
   */
  readonly failed: AccountAdditionFailure[];
  /**
   * Additions that deliberately added nothing, such as an address with no activity on any EVM
   * chain. Neither a failure nor a cancellation: the dock already reports each one with its reason,
   * so a form has nothing to hold open for.
   */
  readonly skipped: number;
  /** True when every failure was a cancellation, so nothing is worth reporting. */
  readonly cancelled: boolean;
}

type CompletionCallback = (params: AccountAdditionParams) => Promise<void>;

interface UseAccountAdditionServiceReturn {
  /**
   * Adds every payload entry to `chain`, which may be {@link EVM_PSEUDO_CHAIN} for "every EVM
   * chain". One function, because that is one operation with one parameter varying.
   */
  addAccounts: (chain: string, payload: AccountPayload[] | XpubAccountPayload, modules: Module[] | undefined, onComplete: CompletionCallback, options?: AdditionOptions) => Promise<AdditionSummary>;
  addSingleAccount: (account: AccountPayload | XpubAccountPayload, chain: string, options?: AdditionOptions) => ResultAsync<string, AccountAdditionFailure>;
  addSingleEvmAddress: (account: AccountPayload, options?: AdditionOptions) => ResultAsync<Account[], AccountAdditionFailure<AccountPayload>>;
  completeAccountAddition: UseAccountAdditionCompletionReturn['completeAccountAddition'];
  getNewAccountPayload: (chain: string, payload: AccountPayload[]) => AccountPayload[];
}

export function useAccountAdditionService(): UseAccountAdditionServiceReturn {
  const { addAccount, addEvmAccount } = useAccountAdditions();
  const { evmChains } = useSupportedChains();
  const { getAddresses } = useAccountAddresses();
  const { runAdditionBatch, runEvmAdditionBatch } = useAccountAdditionBatch();
  const { completeAccountAddition } = useAccountAdditionCompletion();

  const getNewAccountPayload = (chain: string, payload: AccountPayload[]): AccountPayload[] => {
    const knownAddresses: string[] = getAddresses(chain);
    return payload.filter(({ address }) => {
      const key = address.toLocaleLowerCase();
      return !knownAddresses.includes(key);
    });
  };

  /**
   * Adds one EVM address, resolving which chains it was actually added on.
   *
   * @remarks
   * The backend's `added` is optional and may come back as `{}`, which is truthy but has no entry
   * to destructure, so it is read through `Object.entries` and checked rather than destructured
   * directly. An `all` entry stands for every EVM chain rather than naming them.
   *
   * Nothing is reported from here: the addition's own activity carries the outcome, per-chain
   * breakdown included, into the dock.
   */
  const addSingleEvmAddress = async (
    account: AccountPayload,
    options?: AdditionOptions,
  ): ResultAsync<Account[], AccountAdditionFailure<AccountPayload>> => {
    const addedAccounts: Account[] = [];

    const outcome = await addEvmAccount(account, options);
    if (isErr(outcome)) {
      if (isActionable(outcome.error))
        logger.error(outcome.error.message);

      return err({ account, error: outcome.error });
    }

    const [addedEntry] = Object.entries(outcome.value.added ?? {});

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
    }

    return ok(addedAccounts);
  };

  const addSingleAccount = async (
    account: AccountPayload | XpubAccountPayload,
    chain: string,
    options?: AdditionOptions,
  ): ResultAsync<string, AccountAdditionFailure> => pipe(
    await addAccount(chain, 'xpub' in account ? account : [account], options),
    mapError((error: TaskError) => {
      if (isActionable(error))
        logger.error(error.message);

      return { account, error };
    }),
  );

  /**
   * The one addition path, whatever the address count.
   *
   * @remarks
   * Every entry fans out through the batch, a single one included, where the batch suppresses the
   * umbrella rather than showing a parent over one child. No limiter here: the
   * `accounts-add:<chain>` lane caps this at 2.
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
    let skipped = 0;
    let cancelled = false;

    const isXpub = 'xpub' in payload;
    const everyEvmChain = isEveryEvmChain(chain);

    /**
     * Sorts one addition's outcome into the added, skipped, cancelled or failed tally.
     *
     * @remarks
     * Nothing is reported from here. Each addition's activity has already settled with its outcome,
     * which the dock shows; a toast on top of that would say it twice.
     */
    const collect = (result: Result<Account[], AccountAdditionFailure<AccountPayload | XpubAccountPayload>>): void => {
      if (!isErr(result)) {
        addedAccounts.push(...result.value);
        return;
      }

      const { error } = result.error;
      if (isActionable(error))
        failed.push(result.error);
      else if (hasTag(error, 'Skipped'))
        skipped++;
      else
        cancelled = true;
    };

    /** A child's options: its umbrella, and whether the user asked, for the one-address case where it is the root. */
    const childOptions = (parent: AdditionOptions['parent']): AdditionOptions => ({ parent, userStarted: options?.userStarted });

    if (isXpub) {
      collect(mapResult(
        await addSingleAccount(payload, chain, options),
        address => [{ address, chain }],
      ));
    }
    else if (everyEvmChain) {
      const results = await runEvmAdditionBatch(
        payload,
        async (account, parent) => addSingleEvmAddress(account, childOptions(parent)),
        options,
      );
      results.forEach(result => collect(result));
    }
    else {
      const results = await runAdditionBatch(
        chain,
        payload,
        async (account, parent) => addSingleAccount(account, chain, childOptions(parent)),
        options,
      );
      results.forEach(result => collect(mapResult(result, address => [{ address, chain }])));
    }

    startPromise(onComplete({
      addedAccounts,
      chain: everyEvmChain ? undefined : chain,
      isXpub,
      modulesToEnable: modules,
    }));

    return { added: addedAccounts, cancelled, failed, skipped };
  };

  return {
    addAccounts,
    addSingleAccount,
    addSingleEvmAddress,
    completeAccountAddition,
    getNewAccountPayload,
  };
}
