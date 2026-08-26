import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { HistoryEventEntryType } from '@rotki/common';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { useTrackedAddresses } from '@/modules/history/events/use-tracked-addresses';

interface UseUntrackedMovementDestinationReturn {
  isDestinationUntracked: (entry: HistoryEventEntry) => boolean;
}

/**
 * The address an exchange withdrawal was sent to, as reported by the exchange.
 *
 * @remarks
 * Deposits are deliberately not covered. A deposit's recorded address is the address the funds
 * arrived at, which for most exchanges is the exchange's own deposit address rather than the
 * sender - so checking it against the tracked accounts would call nearly every deposit untracked.
 * A deposit is still resolvable as income, it just gets no such hint.
 *
 * @param entry - the movement's own event
 * @returns the destination address, or `undefined` for anything but a withdrawal that recorded one
 */
export function getMovementDestinationAddress(entry: HistoryEventEntry): string | undefined {
  if (entry.entryType !== HistoryEventEntryType.ASSET_MOVEMENT_EVENT || entry.eventSubtype !== 'spend')
    return undefined;

  return entry.extraData?.address ?? undefined;
}

/**
 * Detects exchange withdrawals sent to an address rotki does not track. Such a movement can
 * never be matched -- rotki only decodes transactions of tracked addresses, so no counterpart
 * event can exist -- and the funds left for good, which makes resolving it as a payment the
 * correct action. `use-untracked-bridge-counterpart.ts` answers the same question for a bridge leg.
 */
export const useUntrackedMovementDestination = createSharedComposable((): UseUntrackedMovementDestinationReturn => {
  const { accountsRead, isAddressTracked } = useTrackedAddresses();

  function isDestinationUntracked(entry: HistoryEventEntry): boolean {
    if (!get(accountsRead))
      return false;

    const address = getMovementDestinationAddress(entry);
    return address !== undefined && !isAddressTracked(address);
  }

  return {
    isDestinationUntracked,
  };
});

interface UseMovementUnmatchableExplanationReturn {
  /** Undefined when no movement is selected, or when a match is still possible. */
  unmatchableExplanation: ComputedRef<string | undefined>;
}

/**
 * Explanation for the potential-matches search when a withdrawal cannot be matched because its
 * destination address is untracked, pointing the user to the external resolution instead.
 *
 * @param movement - the movement the search is running for, if any
 */
export function useMovementUnmatchableExplanation(
  movement: MaybeRefOrGetter<UnmatchedAssetMovement | undefined>,
): UseMovementUnmatchableExplanationReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { isDestinationUntracked } = useUntrackedMovementDestination();

  const unmatchableExplanation = computed<string | undefined>(() => {
    const value = toValue(movement);
    if (!value)
      return undefined;

    const { entry, ...meta } = getEventEntryFromCollection(value.events);
    const eventEntry = { ...entry, ...meta };
    if (!isDestinationUntracked(eventEntry))
      return undefined;

    return t('asset_movement_matching.dialog.no_match_untracked_destination', {
      address: getMovementDestinationAddress(eventEntry) ?? '',
    });
  });

  return { unmatchableExplanation };
}
