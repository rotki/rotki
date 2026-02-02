import type { Blockchain } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { isEventMissingAccountingRule } from '@/utils/history/events';

export interface UseHistoryEventItemProps {
  event: Ref<HistoryEventEntry> | ComputedRef<HistoryEventEntry>;
  selection?: UseHistoryEventsSelectionModeReturn;
}

export interface UseHistoryEventItemReturn {
  // Asset state
  isIgnoredAsset: ComputedRef<boolean>;
  isSpam: ComputedRef<boolean>;
  hiddenEvent: ComputedRef<boolean>;
  // Selection state
  showCheckbox: ComputedRef<boolean>;
  isCheckboxDisabled: ComputedRef<boolean>;
  isSelected: ComputedRef<boolean>;
  toggleSelected: () => void;
  // Event state
  hasMissingRule: ComputedRef<boolean>;
  chain: ComputedRef<Blockchain>;
  // Event data
  notes: ComputedRef<string | undefined>;
  counterparty: ComputedRef<string | undefined>;
  validatorIndex: ComputedRef<number | undefined>;
  blockNumber: ComputedRef<number | undefined>;
  extraData: ComputedRef<Record<string, any> | undefined>;
}

export function useHistoryEventItem(
  props: UseHistoryEventItemProps,
): UseHistoryEventItemReturn {
  const { event, selection } = props;
  const { getChain } = useSupportedChains();
  const { assetInfo } = useAssetInfoRetrieval();
  const { useIsAssetIgnored } = useIgnoredAssetsStore();

  const eventAsset = computed<string>(() => get(event).asset);
  const isIgnoredAsset = useIsAssetIgnored(eventAsset);
  const asset = assetInfo(eventAsset, { collectionParent: false });
  const isSpam = computed<boolean>(() => get(asset)?.protocol === 'spam');
  const hiddenEvent = logicOr(isIgnoredAsset, isSpam);

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

  const isSelected = computed<boolean>(() => {
    if (!selection)
      return false;
    return selection.isEventSelected(get(event).identifier);
  });

  function toggleSelected(): void {
    selection?.actions.toggleEvent(get(event).identifier);
  }

  const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(get(event)));

  const chain = computed<Blockchain>(() => getChain(get(event).location));

  const notes = computed<string | undefined>(() => {
    const ev = get(event);
    const autoNotes = 'autoNotes' in ev ? ev.autoNotes : undefined;
    const userNotes = 'userNotes' in ev ? ev.userNotes : undefined;
    return userNotes || autoNotes || undefined;
  });

  const counterparty = computed<string | undefined>(() => {
    const ev = get(event);
    return 'counterparty' in ev ? (ev.counterparty ?? undefined) : undefined;
  });

  const validatorIndex = computed<number | undefined>(() => {
    const ev = get(event);
    return 'validatorIndex' in ev ? ev.validatorIndex : undefined;
  });

  const blockNumber = computed<number | undefined>(() => {
    const ev = get(event);
    return 'blockNumber' in ev ? ev.blockNumber : undefined;
  });

  const extraData = computed<Record<string, any> | undefined>(() => {
    const ev = get(event);
    return 'extraData' in ev ? (ev.extraData as Record<string, any> | undefined) : undefined;
  });

  return {
    blockNumber,
    chain,
    counterparty,
    extraData,
    hasMissingRule,
    hiddenEvent,
    isCheckboxDisabled,
    isIgnoredAsset,
    isSelected,
    isSpam,
    notes,
    showCheckbox,
    toggleSelected,
    validatorIndex,
  };
}
