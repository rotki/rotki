import type { Blockchain } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { isEventMissingAccountingRule } from '@/utils/history/events';

export interface UseHistorySwapItemProps {
  events: Ref<HistoryEventEntry[]> | ComputedRef<HistoryEventEntry[]>;
  selection?: UseHistoryEventsSelectionModeReturn;
}

export interface UseHistorySwapItemReturn {
  // Primary event
  primaryEvent: ComputedRef<HistoryEventEntry>;
  // State
  hasMissingRule: ComputedRef<boolean>;
  chain: ComputedRef<Blockchain>;
  // Selection
  showCheckbox: ComputedRef<boolean>;
  isCheckboxDisabled: ComputedRef<boolean>;
  swapEventIds: ComputedRef<number[]>;
  isSelected: ComputedRef<boolean>;
  toggleSelected: () => void;
  // Swap-specific
  spendEvents: ComputedRef<HistoryEventEntry[]>;
  receiveEvents: ComputedRef<HistoryEventEntry[]>;
  spendEvent: ComputedRef<HistoryEventEntry | undefined>;
  receiveEvent: ComputedRef<HistoryEventEntry | undefined>;
  isMultiSpend: ComputedRef<boolean>;
  isMultiReceive: ComputedRef<boolean>;
  counterparty: ComputedRef<string | undefined>;
  compactNotes: ComputedRef<string | undefined>;
}

const ASSET_RESOLUTION_OPTIONS: AssetResolutionOptions = { collectionParent: false };

export function useHistorySwapItem(
  props: UseHistorySwapItemProps,
): UseHistorySwapItemReturn {
  const { events, selection } = props;
  const { t } = useI18n({ useScope: 'global' });
  const { getChain } = useSupportedChains();
  const { getAssetSymbol } = useAssetInfoRetrieval();

  const primaryEvent = computed<HistoryEventEntry>(() => get(events)[0]);

  const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(get(primaryEvent)));

  const chain = computed<Blockchain>(() => getChain(get(primaryEvent).location));

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

  // All event IDs in this swap for selection
  const swapEventIds = computed<number[]>(() => get(events).map(e => e.identifier));

  const isSelected = computed<boolean>(() => {
    if (!selection)
      return false;
    // A swap is selected if all its events are selected
    return get(swapEventIds).every(id => selection.isEventSelected(id));
  });

  function toggleSelected(): void {
    selection?.actions.toggleSwap(get(swapEventIds));
  }

  // Separate spend and receive events
  const spendEvents = computed<HistoryEventEntry[]>(() =>
    get(events).filter(e => e.eventSubtype === 'spend'),
  );

  const receiveEvents = computed<HistoryEventEntry[]>(() =>
    get(events).filter(e => e.eventSubtype === 'receive'),
  );

  // First spend/receive for visual display
  const spendEvent = computed<HistoryEventEntry | undefined>(() => get(spendEvents)[0]);
  const receiveEvent = computed<HistoryEventEntry | undefined>(() => get(receiveEvents)[0]);

  // Check if multi-swap (multiple spend or receive events)
  const isMultiSpend = computed<boolean>(() => get(spendEvents).length > 1);
  const isMultiReceive = computed<boolean>(() => get(receiveEvents).length > 1);

  const counterparty = computed<string | undefined>(() => {
    const ev = get(primaryEvent);
    return 'counterparty' in ev ? (ev.counterparty ?? undefined) : undefined;
  });

  // Build compact swap notes (handles multi-swap)
  const compactNotes = computed<string | undefined>(() => {
    const spend = get(spendEvents);
    const receive = get(receiveEvents);

    if (spend.length === 0 || receive.length === 0)
      return undefined;

    // For multi-swap, show "X asset" instead of specific amount
    const spendNotes = spend.length === 1
      ? {
          spendAmount: spend[0].amount,
          spendAsset: getAssetSymbol(spend[0].asset, ASSET_RESOLUTION_OPTIONS),
        }
      : {
          spendAmount: spend.length,
          spendAsset: 'assets',
        };

    const receiveNotes = receive.length === 1
      ? {
          receiveAmount: receive[0].amount,
          receiveAsset: getAssetSymbol(receive[0].asset, ASSET_RESOLUTION_OPTIONS),
        }
      : {
          receiveAmount: receive.length,
          receiveAsset: 'assets',
        };

    const notes = t('history_events_list_swap.swap_description', {
      ...spendNotes,
      ...receiveNotes,
    });

    // Append fee if exists
    const fee = get(events).filter(item => item.eventSubtype === 'fee');
    if (fee.length === 0)
      return notes;

    const feeText = fee.map(item => `${item.amount.toFixed()} ${getAssetSymbol(item.asset, ASSET_RESOLUTION_OPTIONS)}`).join('; ');
    return t('history_events_list_swap.fee_description', { feeText, notes });
  });

  return {
    chain,
    compactNotes,
    counterparty,
    hasMissingRule,
    isCheckboxDisabled,
    isMultiReceive,
    isMultiSpend,
    isSelected,
    primaryEvent,
    receiveEvent,
    receiveEvents,
    showCheckbox,
    spendEvent,
    spendEvents,
    swapEventIds,
    toggleSelected,
  };
}
