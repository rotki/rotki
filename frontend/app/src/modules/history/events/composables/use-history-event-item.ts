import type { Blockchain } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { isEventMissingAccountingRule } from '@/utils/history/events';

export interface UseHistoryEventItemProps {
  event: MaybeRefOrGetter<HistoryEventEntry>;
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
  const { useAssetInfo } = useAssetInfoRetrieval();
  const { useIsAssetIgnored } = useAssetsStore();

  const eventAsset = computed<string>(() => toValue(event).asset);
  const isIgnoredAsset = useIsAssetIgnored(eventAsset);
  const asset = useAssetInfo(eventAsset, { collectionParent: false });
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
    return selection.isEventSelected(toValue(event).identifier);
  });

  function toggleSelected(): void {
    selection?.actions.toggleEvent(toValue(event).identifier);
  }

  const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(toValue(event)));

  const chain = computed<Blockchain>(() => getChain(toValue(event).location));

  const notes = computed<string | undefined>(() => {
    const ev = toValue(event);
    const autoNotes = 'autoNotes' in ev ? ev.autoNotes : undefined;
    const userNotes = 'userNotes' in ev ? ev.userNotes : undefined;
    return userNotes || autoNotes || undefined;
  });

  const counterparty = computed<string | undefined>(() => {
    const ev = toValue(event);
    return 'counterparty' in ev ? (ev.counterparty ?? undefined) : undefined;
  });

  const validatorIndex = computed<number | undefined>(() => {
    const ev = toValue(event);
    return 'validatorIndex' in ev ? ev.validatorIndex : undefined;
  });

  const blockNumber = computed<number | undefined>(() => {
    const ev = toValue(event);
    return 'blockNumber' in ev ? ev.blockNumber : undefined;
  });

  const extraData = computed<Record<string, any> | undefined>(() => {
    const ev = toValue(event);
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
