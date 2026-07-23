import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';

interface UseUntrackedBridgeCounterpartReturn {
  getCounterpartAddress: (transaction: UnmatchedBridgeTransaction) => string | undefined;
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
 * Detects bridge legs whose counterpart address is not tracked by rotki. Such a leg can
 * never be matched -- rotki only decodes transactions of tracked addresses, so the
 * counterpart event cannot exist in the database -- and resolving it as external is the
 * correct action. The check is across all chains: an address tracked anywhere is
 * considered tracked, so the guidance only appears when a match is truly impossible.
 */
export function useUntrackedBridgeCounterpart(): UseUntrackedBridgeCounterpartReturn {
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
    getCounterpartAddress: getBridgeCounterpartAddress,
    isCounterpartUntracked,
  };
}

interface UseBridgeUnmatchableExplanationReturn {
  getUnmatchableExplanation: (transaction: UnmatchedBridgeTransaction) => string | undefined;
}

/**
 * Explanation for the potential-matches search when a bridge leg cannot be matched
 * because its counterpart address is untracked, pointing the user to the external
 * resolution instead. Returns undefined when a match is still possible.
 */
export function useBridgeUnmatchableExplanation(): UseBridgeUnmatchableExplanationReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getCounterpartAddress, isCounterpartUntracked } = useUntrackedBridgeCounterpart();

  function getUnmatchableExplanation(transaction: UnmatchedBridgeTransaction): string | undefined {
    if (!isCounterpartUntracked(transaction))
      return undefined;

    const address = getCounterpartAddress(transaction) ?? '';
    return transaction.direction === 'deposit'
      ? t('bridge_matching.dialog.no_match_untracked_destination', { address })
      : t('bridge_matching.dialog.no_match_untracked_source', { address });
  }

  return { getUnmatchableExplanation };
}
