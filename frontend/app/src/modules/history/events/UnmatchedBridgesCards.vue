<script setup lang="ts">
import type { UnmatchedBridgeRow } from '@/modules/history/events/use-unmatched-bridge-rows';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { UNMATCHED_LAYOUTS, type UnmatchedActionPayload, type UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import UnmatchedActions from '@/modules/history/events/UnmatchedActions.vue';
import UnmatchedCardList from '@/modules/history/events/UnmatchedCardList.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const selected = defineModel<string[]>('selected', { required: true });

const { rows, highlightedGroupIdentifier } = defineProps<{
  rows: UnmatchedBridgeRow[];
  specFor: (row: UnmatchedBridgeRow) => UnmatchedRowActionSpec;
  emptyDescription: string;
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  action: [payload: UnmatchedActionPayload<UnmatchedBridgeTransaction>];
}>();

defineSlots<{
  alert?: () => unknown;
}>();
</script>

<template>
  <UnmatchedCardList
    v-model:selected="selected"
    :items="rows"
    :row-key="(row: UnmatchedBridgeRow) => row.id"
    :highlighted="(row: UnmatchedBridgeRow) => row.groupIdentifier === highlightedGroupIdentifier"
    :accented="(row: UnmatchedBridgeRow) => row.untrackedCounterpart"
    :empty-description="emptyDescription"
    :loading="loading"
  >
    <template
      v-if="$slots.alert"
      #alert
    >
      <slot name="alert" />
    </template>

    <template #header="{ item }">
      <div class="flex flex-wrap items-center gap-x-1.5 gap-y-1">
        <BadgeDisplay class="!normal-case">
          {{ item.directionLabel }}
        </BadgeDisplay>
        <LocationDisplay
          class="[&_div]:!justify-start [&_span]:!text-caption [&_span]:!text-rui-text-secondary"
          size="16px"
          :identifier="item.location"
          horizontal
        />
        <DateDisplay
          class="ml-auto text-caption text-rui-text-disabled"
          :timestamp="item.timestamp"
          milliseconds
        />
      </div>
    </template>

    <template #warning="{ item }">
      <div
        v-if="item.untrackedCounterpart"
        class="flex items-start gap-1.5 rounded px-2 py-1 text-caption bg-rui-warning/10 text-rui-warning"
        data-testid="unmatched-card-untracked-reason"
      >
        <RuiIcon
          size="14"
          name="lu-triangle-alert"
          class="shrink-0 mt-0.5"
        />
        <i18n-t
          scope="global"
          keypath="bridge_matching.dialog.untracked_reason"
          tag="span"
        >
          <template #label>
            <strong>{{ item.untrackedLabel }}</strong>
          </template>
        </i18n-t>
      </div>
    </template>

    <template #asset="{ item }">
      <HistoryEventAsset
        dense
        inline
        disable-options
        :event="item.entry"
      />
    </template>

    <template #actions="{ item }">
      <UnmatchedActions
        :spec="specFor(item)"
        :layout="UNMATCHED_LAYOUTS.CARD"
        :ignore-loading="ignoreLoading"
        @action="emit('action', { action: $event, item: item.original })"
      />
    </template>
  </UnmatchedCardList>
</template>
