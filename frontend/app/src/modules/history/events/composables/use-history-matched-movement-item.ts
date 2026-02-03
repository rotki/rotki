import type { ComputedRef, Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { type Blockchain, HistoryEventEntryType } from '@rotki/common';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { isEventMissingAccountingRule } from '@/utils/history/events';

export interface UseHistoryMatchedMovementItemProps {
  events: Ref<HistoryEventEntry[]> | ComputedRef<HistoryEventEntry[]>;
  selection?: UseHistoryEventsSelectionModeReturn;
}

export interface UseHistoryMatchedMovementItemReturn {
  // Events
  primaryEvent: ComputedRef<HistoryEventEntry>;
  secondaryEvent: ComputedRef<HistoryEventEntry | undefined>;
  // State
  hasMissingRule: ComputedRef<boolean>;
  chain: ComputedRef<Blockchain>;
  canUnlink: ComputedRef<boolean>;
  // Selection
  showCheckbox: ComputedRef<boolean>;
  isCheckboxDisabled: ComputedRef<boolean>;
  movementEventIds: ComputedRef<number[]>;
  isSelected: ComputedRef<boolean>;
  toggleSelected: () => void;
  // Notes
  compactNotes: ComputedRef<string | undefined>;
  eventTypeLabel: ComputedRef<string>;
}

const ASSET_RESOLUTION_OPTIONS: AssetResolutionOptions = { collectionParent: false };

export function useHistoryMatchedMovementItem(
  props: UseHistoryMatchedMovementItemProps,
): UseHistoryMatchedMovementItemReturn {
  const { events, selection } = props;
  const { t } = useI18n({ useScope: 'global' });
  const { getChain } = useSupportedChains();
  const { getAssetSymbol } = useAssetInfoRetrieval();

  // For asset movements, use the first non-fee asset movement event as primary
  const primaryEvent = computed<HistoryEventEntry>(() => {
    const assetMovementEvent = get(events).find(
      item => item.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT && item.eventSubtype !== 'fee',
    );
    return assetMovementEvent ?? get(events)[0];
  });

  // Secondary event is the one that's NOT an asset movement event (e.g., EVM event, Solana event)
  const secondaryEvent = computed<HistoryEventEntry | undefined>(() => get(events).find(
    item => item.entryType !== HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
  ));

  const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(get(primaryEvent)));

  const chain = computed<Blockchain>(() => {
    const primary = get(primaryEvent);
    const secondary = get(secondaryEvent);
    return getChain(secondary?.location || primary.location);
  });

  const showCheckbox = computed<boolean>(() => {
    if (!selection)
      return false;
    return get(selection.isSelectionMode);
  });

  const isCheckboxDisabled = computed<boolean>(() => {
    if (!selection)
      return false;
    return get(selection.isSelectAllMatching);
  });

  // All event IDs in this movement for selection
  const movementEventIds = computed<number[]>(() => get(events).map(e => e.identifier));

  const isSelected = computed<boolean>(() => {
    if (!selection)
      return false;
    // A movement is selected if all its events are selected
    return get(movementEventIds).every(id => selection.isEventSelected(id));
  });

  function toggleSelected(): void {
    selection?.actions.toggleSwap(get(movementEventIds));
  }

  // Check if this movement can be unlinked
  const canUnlink = computed<boolean>(() => {
    const ev = get(primaryEvent);
    return !!ev.actualGroupIdentifier;
  });

  // Build compact notes for asset movements with fee
  const compactNotes = computed<string | undefined>(() => {
    const primary = get(primaryEvent);
    const secondary = get(secondaryEvent);

    const amount = primary.amount;
    const asset = getAssetSymbol(primary.asset, ASSET_RESOLUTION_OPTIONS);
    const locationLabel = primary.locationLabel ?? '';
    const address = secondary?.locationLabel ?? '';

    const notes = primary.eventType === 'deposit'
      ? t('asset_movement_matching.compact_notes.deposit', { address, amount, asset, locationLabel })
      : t('asset_movement_matching.compact_notes.withdraw', { address, amount, asset, locationLabel });

    // Append fee if exists
    const fee = get(events).filter(item => item.eventSubtype === 'fee');
    if (fee.length === 0)
      return notes;

    const feeText = fee.map(item => `${item.amount.toFixed()} ${getAssetSymbol(item.asset, ASSET_RESOLUTION_OPTIONS)}`).join('; ');
    return t('history_events_list_swap.fee_description', { feeText, notes });
  });

  const eventTypeLabel = computed<string>(() => {
    const primary = get(primaryEvent);
    return primary.eventType === 'deposit'
      ? t('backend_mappings.events.history_event_type.deposit')
      : t('backend_mappings.events.history_event_type.withdrawal');
  });

  return {
    canUnlink,
    chain,
    compactNotes,
    eventTypeLabel,
    hasMissingRule,
    isCheckboxDisabled,
    isSelected,
    movementEventIds,
    primaryEvent,
    secondaryEvent,
    showCheckbox,
    toggleSelected,
  };
}
