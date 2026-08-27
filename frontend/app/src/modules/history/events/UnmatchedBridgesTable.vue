<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { UnmatchedBridgeRow } from '@/modules/history/events/use-unmatched-bridge-rows';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import { UNMATCHED_LAYOUTS, type UnmatchedActionPayload, type UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import UnmatchedActions from '@/modules/history/events/UnmatchedActions.vue';
import UnmatchedUntrackedBadge from '@/modules/history/events/UnmatchedUntrackedBadge.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const selected = defineModel<string[]>('selected', { required: true });

const { highlightedGroupIdentifier } = defineProps<{
  rows: UnmatchedBridgeRow[];
  specFor: (row: UnmatchedBridgeRow) => UnmatchedRowActionSpec;
  emptyDescription: string;
  maxHeight: string;
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

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<UnmatchedBridgeRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    key: 'direction',
    label: t('common.type'),
  },
  {
    align: 'center',
    key: 'location',
    label: t('common.location'),
  },
  {
    key: 'asset',
    label: t('common.asset'),
  },
  {
    key: 'actions',
    label: t('bridge_matching.dialog.manual_action'),
  },
]);

function getRowClass(row: UnmatchedBridgeRow): string {
  const classes = ['transition-all'];
  if (row.groupIdentifier === highlightedGroupIdentifier) {
    classes.push('!bg-rui-warning/15');
  }
  return classes.join(' ');
}
</script>

<template>
  <ScrollableDialogContent :max-height="maxHeight">
    <RuiDataTable
      v-model="selected"
      :cols="columns"
      :rows="rows"
      row-attr="id"
      :item-class="getRowClass"
      outlined
      dense
      multi-page-select
      :loading="loading"
      :empty="{ description: emptyDescription }"
    >
      <template
        v-if="$slots.alert"
        #body.prepend
      >
        <tr>
          <td :colspan="columns.length + 1">
            <slot name="alert" />
          </td>
        </tr>
      </template>
      <template #item.asset="{ row }">
        <HistoryEventAsset
          disable-options
          :event="row.entry"
        />
      </template>
      <template #item.direction="{ row }">
        <div class="flex flex-col items-start gap-1">
          <BadgeDisplay class="!normal-case">
            {{ row.directionLabel }}
          </BadgeDisplay>
          <UnmatchedUntrackedBadge
            v-if="row.untrackedCounterpart"
            :label="row.untrackedLabel"
            :tooltip="row.untrackedTooltip"
          />
        </div>
      </template>
      <template #item.location="{ row }">
        <LocationDisplay
          size="24px"
          :identifier="row.location"
        />
      </template>
      <template #item.timestamp="{ row }">
        <DateDisplay
          :timestamp="row.timestamp"
          milliseconds
        />
      </template>
      <template #item.actions="{ row }">
        <UnmatchedActions
          :spec="specFor(row)"
          :layout="UNMATCHED_LAYOUTS.ROW"
          :ignore-loading="ignoreLoading"
          @action="emit('action', { action: $event, item: row.original })"
        />
      </template>
    </RuiDataTable>
  </ScrollableDialogContent>
</template>
