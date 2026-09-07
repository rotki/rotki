import type { ActionStatus } from '@/modules/core/common/action';
import type { DisabledChainQueries } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';
import { get } from '@vueuse/core';
import { toChainKey } from '@/modules/core/common/chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { useSettingsWriter } from '@/modules/settings/settings-writer';
import { useSetting } from '@/modules/settings/use-setting';

export interface UseSkipAddressQueriesReturn {
  /** True when every skippable chain already excludes this address. False when none are skippable. */
  isSkipped: (address: string, chains: string[]) => boolean;
  /** Add the address rule on every skippable chain, or lift it from all of them when it is set. */
  toggle: (address: string, chains: string[]) => Promise<ActionStatus>;
}

/**
 * The key `payload` stores `chain` under, whatever its spelling, or `undefined` when it has none.
 *
 * @remarks
 * Written by the settings dialog, by this composable and by the backend, so `polygon_pos` and
 * `polygonPos` both occur. Adding a second key for a chain that already has one leaves two rules
 * the reader folds together but the writer keeps overwriting one of.
 */
function findChainKey(payload: DisabledChainQueries, chain: string): string | undefined {
  const target = toChainKey(chain);
  return Object.keys(payload).find(key => toChainKey(key) === target);
}

function sameAddress(a: string, b: string): boolean {
  return a.toLowerCase() === b.toLowerCase();
}

function clonePayload(payload: DisabledChainQueries): DisabledChainQueries {
  return Object.fromEntries(Object.entries(payload).map(([chain, addresses]) => [chain, [...addresses]]));
}

/**
 * `payload` with `address` excluded on each of `chains`.
 *
 * @remarks
 * A chain whose entry is empty is switched off whole, which already covers every address on it, so
 * it is left alone rather than given a narrower rule that would read as a downgrade.
 *
 * An entry that differs from `address` only by case is **replaced** rather than left as it is: the
 * backend compares addresses exactly, so a lower-cased entry written by hand or by an older client
 * never matches the checksummed address the row carries, and the rule silently does nothing while
 * this module - which folds case - reports the account as skipped.
 *
 * Exported for its spec: {@link useSkipAddressQueries} only ever calls it under conditions it has
 * already established, which leaves the guards that make it total untestable through the composable.
 */
export function skipAddress(payload: DisabledChainQueries, address: string, chains: string[]): DisabledChainQueries {
  const next = clonePayload(payload);
  for (const chain of chains) {
    const key = findChainKey(next, chain);
    if (key === undefined) {
      next[chain] = [address];
      continue;
    }
    const addresses = next[key];
    if (addresses.length === 0)
      continue;
    const existing = addresses.findIndex(entry => sameAddress(entry, address));
    if (existing === -1)
      addresses.push(address);
    else
      addresses[existing] = address;
  }
  return next;
}

/**
 * `payload` without `address` on any of `chains`.
 *
 * @remarks
 * The chain's key is **deleted** once its last address goes, never left as an empty array: an empty
 * array is the payload's spelling for "this entire chain is switched off", so lifting the last
 * address rule that way would silently skip the whole chain instead of nothing.
 *
 * Exported for its spec, as {@link skipAddress} is.
 */
export function unskipAddress(payload: DisabledChainQueries, address: string, chains: string[]): DisabledChainQueries {
  const next = clonePayload(payload);
  for (const chain of chains) {
    const key = findChainKey(next, chain);
    if (key === undefined)
      continue;
    const addresses = next[key];
    if (addresses.length === 0)
      continue;
    const remaining = addresses.filter(existing => !sameAddress(existing, address));
    if (remaining.length === addresses.length)
      continue;
    if (remaining.length === 0)
      delete next[key];
    else
      next[key] = remaining;
  }
  return next;
}

/**
 * Serializes every write this module makes, across all of its callers.
 *
 * @remarks
 * A toggle is a read-modify-write of one shared setting, and each row holds its own composable. Two
 * rows toggled before the first write lands would otherwise both build a payload from the state
 * before either, and the second would erase the first with no error to show for it. Queued, each
 * payload is built once the previous write has updated the settings repo, which
 * `useSettingsOperations.update` does before it resolves.
 *
 * A rejected write must not stall the queue, so the chain is kept on its settled form.
 */
let writeQueue: Promise<unknown> = Promise.resolve();

async function queued<T>(task: () => Promise<T>): Promise<T> {
  const run = writeQueue.then(task, task);
  writeQueue = run.catch(() => undefined);
  return run;
}

/**
 * Write side of the `disabledChainQueries` setting for one address, as the accounts table needs it:
 * skip this address on the chains the row shows, or stop skipping it, in a single call.
 *
 * @remarks
 * The settings dialog edits the same setting through {@link useDisabledChainQueriesState}, which
 * models it as a list of rules with ids so a row can be edited in place. A quick action has no rule
 * to edit - it knows an address and some chains - so it works on the payload directly and shares
 * only the read side, {@link useDisabledChains}.
 *
 * A chain switched off whole is never touched here, in either direction: it is a decision about the
 * chain rather than about this account, and undoing it from a single row would silently re-enable
 * every other address on it.
 */
export function useSkipAddressQueries(): UseSkipAddressQueriesReturn {
  const disabledChainQueries = useSetting('disabledChainQueries');
  const { isAddressExcluded, isChainExcluded } = useDisabledChains();
  const { write } = useSettingsWriter();

  const skippableChains = (chains: string[]): string[] => chains.filter(chain => !isChainExcluded(chain));

  const isSkipped = (address: string, chains: string[]): boolean => {
    const skippable = skippableChains(chains);
    return skippable.length > 0 && skippable.every(chain => isAddressExcluded(chain, address));
  };

  const toggle = async (address: string, chains: string[]): Promise<ActionStatus> => queued(async () => {
    const skippable = skippableChains(chains);
    if (skippable.length === 0)
      return { success: true };

    const current = get(disabledChainQueries);
    const payload = isSkipped(address, chains)
      ? unskipAddress(current, address, skippable)
      : skipAddress(current, address, skippable);

    return write('disabledChainQueries', payload);
  });

  return {
    isSkipped,
    toggle,
  };
}
