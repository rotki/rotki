import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useTrackedAddresses } from '@/modules/history/events/use-tracked-addresses';

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
 * Whether a leg's counterpart chain cannot be queried, so its counterpart event can never be
 * pulled.
 *
 * @remarks
 * Decoders record EVM chains as numeric ids, so a string chain is non-EVM, which today means
 * ZKsync Lite and its shut-down API.
 */
export function isCounterpartUnqueryable(transaction: UnmatchedBridgeTransaction): boolean {
  return typeof getBridgeCounterpartChain(transaction) === 'string';
}

/**
 * Whether offering to create a synthetic counterpart event makes sense for a leg.
 *
 * @remarks
 * Only the unqueryable case qualifies. A leg whose counterpart address is untracked belongs to
 * someone else, so no counterpart event should exist and the resolution is to mark it external;
 * offering both at once invites fabricating an event for a payment out.
 */
export function canCreateBridgeCounterpart(transaction: UnmatchedBridgeTransaction, counterpartUntracked: boolean): boolean {
  return !counterpartUntracked && isCounterpartUnqueryable(transaction);
}

/**
 * Detects bridge legs whose counterpart address is not tracked by rotki. Such a leg can
 * never be matched -- rotki only decodes transactions of tracked addresses, so the
 * counterpart event cannot exist in the database -- and resolving it as external is the
 * correct action. The check is across all chains: an address tracked anywhere is
 * considered tracked, so the guidance only appears when a match is truly impossible.
 */
export const useUntrackedBridgeCounterpart = createSharedComposable((): UseUntrackedBridgeCounterpartReturn => {
  const { accountsRead, isAddressTracked } = useTrackedAddresses();

  function isCounterpartUntracked(transaction: UnmatchedBridgeTransaction): boolean {
    if (!get(accountsRead))
      return false;

    const address = getBridgeCounterpartAddress(transaction);
    return address !== undefined && !isAddressTracked(address);
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
