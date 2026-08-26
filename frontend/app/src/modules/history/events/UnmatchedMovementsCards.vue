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
import HashLink from '@/modules/shell/components/HashLink.vue';

// The pinned presentation of unmatched movements. Layout only - see UnmatchedMovementsList.
const selected = defineModel<string[]>('selected', { required: true });

const { rows, highlightedGroupIdentifier } = defineProps<{
  rows: UnmatchedMovementRow[];
  specFor: (row: UnmatchedMovementRow) => UnmatchedRowActionSpec;
  emptyDescription: string;
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
    :accented="(row: UnmatchedMovementRow) => row.untrackedDestination"
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
          {{ item.typeLabel }}
        </BadgeDisplay>
        <RuiChip
          v-if="item.resolvedAsExternal"
          size="sm"
          color="info"
          class="!py-0"
          data-testid="unmatched-row-resolved"
        >
          {{ item.resolvedLabel }}
        </RuiChip>
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

    <template #warning="{ item }">
      <div
        v-if="item.untrackedDestination"
        class="flex items-start gap-1.5 rounded px-2 py-1 text-caption bg-rui-warning/10 text-rui-warning"
        data-testid="unmatched-card-untracked-reason"
      >
        <RuiIcon
          size="14"
          name="lu-triangle-alert"
          class="shrink-0 mt-0.5"
        />
        <div class="flex flex-col items-start gap-0.5 min-w-0">
          <i18n-t
            scope="global"
            keypath="asset_movement_matching.dialog.untracked_reason"
            tag="span"
          >
            <template #label>
              <strong>{{ item.untrackedLabel }}</strong>
            </template>
          </i18n-t>
          <HashLink
            v-if="item.destinationAddress"
            class="[&_span]:!text-caption"
            :text="item.destinationAddress"
          />
        </div>
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
