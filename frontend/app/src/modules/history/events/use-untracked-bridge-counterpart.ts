import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';

interface UseUntrackedBridgeCounterpartReturn {
  isCounterpartUntracked: (transaction: UnmatchedBridgeTransaction) => boolean;
}

/**
 * The address on the other side of an unmatched bridge leg, as recorded by the
 * decoder: the destination address for a deposit, the source address for a withdrawal.
 */
export function getBridgeCounterpartAddress(transaction: UnmatchedBridgeTransaction): string | undefined {
  return transaction.direction === 'deposit' ? transaction.bridge?.toAddress : transaction.bridge?.fromAddress;
}

/**
 * The chain on the other side of an unmatched bridge leg, as recorded by the decoder:
 * the destination chain for a deposit, the source chain for a withdrawal. EVM chains
 * are recorded as numeric chain ids and other chains as name strings.
 */
export function getBridgeCounterpartChain(transaction: UnmatchedBridgeTransaction): string | number | undefined {
  return transaction.direction === 'deposit' ? transaction.bridge?.toChain : transaction.bridge?.fromChain;
}

/**
 * Detects bridge legs whose counterpart chain can no longer be queried, so the
 * counterpart event can never be pulled. Decoders record EVM chains as numeric chain
 * ids; a string chain is a non-EVM chain, which today means ZKsync Lite — whose API
 * has shut down. For such legs creating a synthetic counterpart event is the
 * suggested resolution.
 */
export function isCounterpartUnqueryable(transaction: UnmatchedBridgeTransaction): boolean {
  return typeof getBridgeCounterpartChain(transaction) === 'string';
}

/**
 * Detects bridge legs whose counterpart address is not tracked by rotki. Such a leg can
 * never be matched -- rotki only decodes transactions of tracked addresses, so the
 * counterpart event cannot exist in the database -- and resolving it as external is the
 * correct action. The check is across all chains: an address tracked anywhere is
 * considered tracked, so the guidance only appears when a match is truly impossible.
 */
export const useUntrackedBridgeCounterpart = createSharedComposable((): UseUntrackedBridgeCounterpartReturn => {
  const { addresses } = useAccountAddresses();

  const trackedAddresses = computed<Set<string>>(() => {
    const tracked = new Set<string>();
    for (const chainAddresses of Object.values(get(addresses))) {
      for (const address of chainAddresses)
        tracked.add(address.toLowerCase());
    }
    return tracked;
  });

  function isCounterpartUntracked(transaction: UnmatchedBridgeTransaction): boolean {
    const address = getBridgeCounterpartAddress(transaction);
    return address !== undefined && !get(trackedAddresses).has(address.toLowerCase());
  }

  return {
    isCounterpartUntracked,
  };
});

interface UseBridgeUnmatchableExplanationReturn {
  unmatchableExplanation: ComputedRef<string | undefined>;
}

/**
 * Explanation for the potential-matches search when a bridge leg cannot be matched
 * because its counterpart address is untracked, pointing the user to the external
 * resolution instead. The explanation is undefined when no transaction is selected or a
 * match is still possible.
 */
export function useBridgeUnmatchableExplanation(
  transaction: MaybeRefOrGetter<UnmatchedBridgeTransaction | undefined>,
): UseBridgeUnmatchableExplanationReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { isCounterpartUntracked } = useUntrackedBridgeCounterpart();

  const unmatchableExplanation = computed<string | undefined>(() => {
    const value = toValue(transaction);
    if (!value || !isCounterpartUntracked(value))
      return undefined;

    const address = getBridgeCounterpartAddress(value) ?? '';
    return value.direction === 'deposit'
      ? t('bridge_matching.dialog.no_match_untracked_destination', { address })
      : t('bridge_matching.dialog.no_match_untracked_source', { address });
  });

  return { unmatchableExplanation };
}
