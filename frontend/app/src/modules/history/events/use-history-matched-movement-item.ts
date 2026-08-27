import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/use-selection-mode';
import { type Blockchain, HistoryEventEntryType } from '@rotki/common';
import { NO_COLLECTION_RESOLVE, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isEventMissingAccountingRule } from '@/modules/history/event-utils';

export interface UseHistoryMatchedMovementItemProps {
  events: Ref<HistoryEventEntry[]> | ComputedRef<HistoryEventEntry[]>;
  selection?: UseHistoryEventsSelectionModeReturn;
}

export interface UseHistoryMatchedMovementItemReturn {
  primaryEvent: ComputedRef<HistoryEventEntry>;
  /**
   * The matching counterpart of `primaryEvent`: the largest non-fee event, preferring one whose
   * entry type differs from the primary's.
   */
  secondaryEvent: ComputedRef<HistoryEventEntry | undefined>;
  hasMissingRule: ComputedRef<boolean>;
  chain: ComputedRef<Blockchain>;
  canUnlink: ComputedRef<boolean>;
  showCheckbox: ComputedRef<boolean>;
  isCheckboxDisabled: ComputedRef<boolean>;
  movementEventIds: ComputedRef<number[]>;
  isSelected: ComputedRef<boolean>;
  toggleSelected: () => void;
  compactNotes: ComputedRef<string | undefined>;
  eventTypeLabel: ComputedRef<string>;
}

const ASSET_RESOLUTION_OPTIONS = NO_COLLECTION_RESOLVE;

export function useHistoryMatchedMovementItem(
  props: UseHistoryMatchedMovementItemProps,
): UseHistoryMatchedMovementItemReturn {
  const { events, selection } = props;
  const { t } = useI18n({ useScope: 'global' });
  const { getChain } = useSupportedChains();
  const { getAssetField } = useAssetInfoRetrieval();

  const { getLocationData } = useLocations();

  const primaryEvent = computed<HistoryEventEntry>(() => {
    const assetMovementEvent = get(events).find(
      item => item.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT && item.eventSubtype !== 'fee',
    );
    return assetMovementEvent ?? get(events)[0];
  });

  const secondaryEvent = computed<HistoryEventEntry | undefined>(() => {
    const primary = get(primaryEvent);
    const candidates = get(events).filter(
      item => item.eventSubtype !== 'fee' && item.identifier !== primary.identifier,
    );
    if (candidates.length === 0)
      return undefined;

    const differentType = candidates.filter(item => item.entryType !== primary.entryType);
    const pool = differentType.length > 0 ? differentType : candidates;

    return pool.reduce((best, item) => (item.amount.gt(best.amount) ? item : best));
  });

  const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(get(primaryEvent)));

  const chain = computed<Blockchain>(() => {
    const primary = get(primaryEvent);
    const secondary = get(secondaryEvent);
    return getChain(secondary?.location ?? primary.location);
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

  const movementEventIds = computed<number[]>(() => get(events).map(e => e.identifier));

  const isSelected = computed<boolean>(() => {
    if (!selection)
      return false;
    return get(movementEventIds).every(id => selection.isEventSelected(id));
  });

  function toggleSelected(): void {
    selection?.actions.toggleSwap(get(movementEventIds));
  }

  const canUnlink = computed<boolean>(() => {
    const ev = get(primaryEvent);
    return !!ev.actualGroupIdentifier;
  });

  function resolveEventLabel(event?: HistoryEventEntry): string {
    if (!event)
      return '';
    return (event.locationLabel ?? getLocationData(event.location)?.name) ?? '';
  }

  function appendFeeNotes(notes: string): string {
    const fee = get(events).filter(item => item.eventSubtype === 'fee');
    if (fee.length === 0)
      return notes;

    const feeText = fee.map(item => `${item.amount.toFixed()} ${getAssetField(item.asset, 'symbol', ASSET_RESOLUTION_OPTIONS)}`).join('; ');
    return t('history_events_list_swap.fee_description', { feeText, notes });
  }

  // Build compact notes for asset movements with fee
  const compactNotes = computed<string | undefined>(() => {
    const primary = get(primaryEvent);
    const secondary = get(secondaryEvent);

    const amount = primary.amount;
    const asset = getAssetField(primary.asset, 'symbol', ASSET_RESOLUTION_OPTIONS);
    const exchangeLabel = resolveEventLabel(primary);
    const addressLabel = resolveEventLabel(secondary);

    const isDeposit = primary.eventSubtype === 'receive';
    const toLabel = isDeposit ? exchangeLabel : addressLabel;
    const fromLabel = isDeposit ? addressLabel : exchangeLabel;

    const to = toLabel ? t('asset_movement_matching.compact_notes.to_part', { locationLabel: toLabel }) : '';
    const from = fromLabel ? t('asset_movement_matching.compact_notes.from_part', { address: fromLabel }) : '';

    const notes = isDeposit
      ? t('asset_movement_matching.compact_notes.deposit', { amount, asset, to, from })
      : t('asset_movement_matching.compact_notes.withdraw', { amount, asset, from, to });

    return appendFeeNotes(notes);
  });

  const eventTypeLabel = computed<string>(() => {
    const primary = get(primaryEvent);
    return primary.eventSubtype === 'receive'
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
