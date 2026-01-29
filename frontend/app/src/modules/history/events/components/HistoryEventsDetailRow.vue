<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import HistoryEventAsset from '@/components/history/events/HistoryEventAsset.vue';
import HistoryEventNote from '@/components/history/events/HistoryEventNote.vue';
import HistoryEventsListItemAction from '@/components/history/events/HistoryEventsListItemAction.vue';
import HistoryEventType from '@/components/history/events/HistoryEventType.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { isEventMissingAccountingRule } from '@/utils/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
  index: number;
  allEvents: HistoryEventEntry[];
  groupLocationLabel?: string;
  hideActions?: boolean;
  highlight?: boolean;
  selection?: UseHistoryEventsSelectionModeReturn;
}>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'refresh': [];
}>();

const { event } = toRefs(props);
const { getChain } = useSupportedChains();
const { assetInfo } = useAssetInfoRetrieval();
const { useIsAssetIgnored } = useIgnoredAssetsStore();

const eventAsset = computed<string>(() => get(event).asset);
const isIgnoredAsset = useIsAssetIgnored(eventAsset);
const asset = assetInfo(eventAsset, { collectionParent: false });
const isSpam = computed<boolean>(() => get(asset)?.protocol === 'spam');
const hiddenEvent = logicOr(isIgnoredAsset, isSpam);

const showCheckbox = computed<boolean>(() => {
  if (!props.selection)
    return false;
  return get(props.selection.isSelectionMode);
});

const isCheckboxDisabled = computed<boolean>(() => {
  if (!props.selection)
    return false;
  return get(props.selection.isSelectAllMatching);
});

const isSelected = computed<boolean>({
  get() {
    if (!props.selection)
      return false;
    return props.selection.isEventSelected(props.event.identifier);
  },
  set(value: boolean) {
    if (value !== get(isSelected))
      props.selection?.actions.toggleEvent(props.event.identifier);
  },
});

const hasMissingRule = computed<boolean>(() => isEventMissingAccountingRule(get(event)));

const chain = computed(() => getChain(get(event).location));

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
</script>

<template>
  <div
    class="h-20 flex items-center gap-4 border-b border-default px-4 pl-8 group/row contain-content"
    :class="{ 'opacity-50': hiddenEvent }"
  >
    <!-- Checkbox for selection mode -->
    <RuiCheckbox
      v-if="showCheckbox"
      v-model="isSelected"
      color="primary"
      hide-details
      :disabled="isCheckboxDisabled"
      class="shrink-0 -ml-2"
    />

    <!-- Event type -->
    <HistoryEventType
      :event="event"
      :chain="chain"
      :group-location-label="groupLocationLabel"
      :highlight="highlight"
      class="w-44 shrink-0"
    />

    <!-- Asset & Amount -->
    <HistoryEventAsset
      :event="event"
      class="w-60 shrink-0"
      @refresh="emit('refresh')"
    />

    <!-- Notes - flex-1 with overflow handling, max 2 lines -->
    <HistoryEventNote
      :notes="notes"
      :amount="event.amount"
      :asset="event.asset"
      :chain="chain"
      :counterparty="counterparty"
      :validator-index="validatorIndex"
      :block-number="blockNumber"
      :extra-data="extraData"
      class="flex-1 min-w-0 overflow-hidden line-clamp-2"
    />

    <!-- Actions - visible on hover, always visible if missing rule -->
    <HistoryEventsListItemAction
      v-if="!hideActions"
      :item="event"
      :index="index"
      :events="allEvents"
      class="w-24 shrink-0 transition-opacity"
      :class="{
        'opacity-0 group-hover/row:opacity-100 focus-within:opacity-100': !hasMissingRule,
      }"
      @edit-event="emit('edit-event', $event)"
      @delete-event="emit('delete-event', $event)"
      @show:missing-rule-action="emit('show:missing-rule-action', $event)"
    />
  </div>
</template>
