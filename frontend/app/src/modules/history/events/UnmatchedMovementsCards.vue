<script setup lang="ts">
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { UnmatchedMovementRow } from '@/modules/history/events/use-unmatched-movement-rows';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { UNMATCHED_LAYOUTS, type UnmatchedActionPayload, type UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import UnmatchedActions from '@/modules/history/events/UnmatchedActions.vue';
import UnmatchedCardList from '@/modules/history/events/UnmatchedCardList.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

// The pinned presentation of unmatched movements. Layout only - see UnmatchedMovementsList.
const selected = defineModel<string[]>('selected', { required: true });

const { rows, highlightedGroupIdentifier } = defineProps<{
  rows: UnmatchedMovementRow[];
  specFor: (row: UnmatchedMovementRow) => UnmatchedRowActionSpec;
  emptyDescription: string;
  maxHeight: string;
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  action: [payload: UnmatchedActionPayload<UnmatchedAssetMovement>];
}>();

defineSlots<{
  alert?: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <UnmatchedCardList
    v-model:selected="selected"
    :items="rows"
    :row-key="(row: UnmatchedMovementRow) => row.groupIdentifier"
    :highlighted="(row: UnmatchedMovementRow) => row.groupIdentifier === highlightedGroupIdentifier"
    :empty-description="emptyDescription"
    :loading="loading"
    :max-height="maxHeight"
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
          {{ item.typeLabel }}
        </BadgeDisplay>
        <LocationDisplay
          class="[&_div]:!justify-start [&_span]:!text-caption [&_span]:!text-rui-text-secondary"
          size="16px"
          :identifier="item.location"
          horizontal
        />
        <RuiTooltip
          v-if="item.isFiat"
          :open-delay="400"
          :popper="{ placement: 'top' }"
          tooltip-class="max-w-80"
        >
          <template #activator>
            <RuiChip
              size="sm"
              color="warning"
              class="!py-0"
            >
              {{ t('asset_movement_matching.fiat_hint.label') }}
            </RuiChip>
          </template>
          {{ t('asset_movement_matching.fiat_hint.tooltip') }}
        </RuiTooltip>
        <DateDisplay
          class="ml-auto text-caption text-rui-text-disabled"
          :timestamp="item.timestamp"
          milliseconds
        />
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
