import type { Blockchain } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/use-selection-mode';
import { NO_COLLECTION_RESOLVE, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isEventMissingAccountingRule } from '@/modules/history/event-utils';

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
  isBridge: ComputedRef<boolean>;
  spendEvents: ComputedRef<HistoryEventEntry[]>;
  receiveEvents: ComputedRef<HistoryEventEntry[]>;
  spendEvent: ComputedRef<HistoryEventEntry | undefined>;
  receiveEvent: ComputedRef<HistoryEventEntry | undefined>;
  isMultiSpend: ComputedRef<boolean>;
  isMultiReceive: ComputedRef<boolean>;
  isSpendHidden: ComputedRef<boolean>;
  isReceiveHidden: ComputedRef<boolean>;
  counterparty: ComputedRef<string | undefined>;
  compactNotes: ComputedRef<string | undefined>;
}

const ASSET_RESOLUTION_OPTIONS = NO_COLLECTION_RESOLVE;

export function useHistorySwapItem(
  props: UseHistorySwapItemProps,
): UseHistorySwapItemReturn {
  const { events, selection } = props;
  const { t } = useI18n({ useScope: 'global' });
  const { getChain, getChainName } = useSupportedChains();
  const { getAssetField, useAssetInfo } = useAssetInfoRetrieval();
  const { isAssetIgnored } = useAssetsStore();

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

  // A joined matched-bridge subgroup: both legs carry the bridge subtype
  const isBridge = computed<boolean>(() => get(events).some(e => e.eventSubtype === 'bridge'));

  // Separate spend and receive events. For matched bridge groups the source
  // chain deposit is the spend side and the destination chain withdrawal the
  // receive side.
  const spendEvents = computed<HistoryEventEntry[]>(() =>
    get(events).filter(e => e.eventSubtype === 'spend' || (e.eventSubtype === 'bridge' && e.eventType === 'deposit')),
  );

  const receiveEvents = computed<HistoryEventEntry[]>(() =>
    get(events).filter(e => e.eventSubtype === 'receive' || (e.eventSubtype === 'bridge' && e.eventType === 'withdrawal')),
  );

  // First spend/receive for visual display
  const spendEvent = computed<HistoryEventEntry | undefined>(() => get(spendEvents)[0]);
  const receiveEvent = computed<HistoryEventEntry | undefined>(() => get(receiveEvents)[0]);

  // Check if multi-swap (multiple spend or receive events)
  const isMultiSpend = computed<boolean>(() => get(spendEvents).length > 1);
  const isMultiReceive = computed<boolean>(() => get(receiveEvents).length > 1);

  const spendAsset = computed<string>(() => get(spendEvent)?.asset ?? '');
  const receiveAsset = computed<string>(() => get(receiveEvent)?.asset ?? '');
  const spendAssetInfo = useAssetInfo(spendAsset, ASSET_RESOLUTION_OPTIONS);
  const receiveAssetInfo = useAssetInfo(receiveAsset, ASSET_RESOLUTION_OPTIONS);

  const isSpendHidden = computed<boolean>(() => {
    const asset = get(spendAsset);
    return asset !== '' && (isAssetIgnored(asset) || get(spendAssetInfo)?.protocol === 'spam');
  });

  const isReceiveHidden = computed<boolean>(() => {
    const asset = get(receiveAsset);
    return asset !== '' && (isAssetIgnored(asset) || get(receiveAssetInfo)?.protocol === 'spam');
  });

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
          spendAsset: getAssetField(spend[0].asset, 'symbol', ASSET_RESOLUTION_OPTIONS),
        }
      : {
          spendAmount: spend.length,
          spendAsset: 'assets',
        };

    const receiveNotes = receive.length === 1
      ? {
          receiveAmount: receive[0].amount,
          receiveAsset: getAssetField(receive[0].asset, 'symbol', ASSET_RESOLUTION_OPTIONS),
        }
      : {
          receiveAmount: receive.length,
          receiveAsset: 'assets',
        };

    const notes = get(isBridge)
      ? t('history_events_list_swap.bridge_description', {
          ...spendNotes,
          ...receiveNotes,
          fromChain: getChainName(spend[0].location),
          toChain: getChainName(receive[0].location),
        })
      : t('history_events_list_swap.swap_description', {
          ...spendNotes,
          ...receiveNotes,
        });

    // Append fee if exists
    const fee = get(events).filter(item => item.eventSubtype === 'fee');
    if (fee.length === 0)
      return notes;

    const feeText = fee.map(item => `${item.amount.toFixed()} ${getAssetField(item.asset, 'symbol', ASSET_RESOLUTION_OPTIONS)}`).join('; ');
    return t('history_events_list_swap.fee_description', { feeText, notes });
  });

  return {
    chain,
    compactNotes,
    counterparty,
    hasMissingRule,
    isBridge,
    isCheckboxDisabled,
    isMultiReceive,
    isMultiSpend,
    isReceiveHidden,
    isSelected,
    isSpendHidden,
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
