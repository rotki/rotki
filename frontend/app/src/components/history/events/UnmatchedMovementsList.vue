<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import type { UnmatchedAssetMovement } from '@/composables/history/events/use-unmatched-asset-movements';
import type { HistoryEventCollectionRow, HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import TableEmptyState from '@/components/display/TableEmptyState.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';

interface UnmatchedMovementRow {
  groupIdentifier: string;
  asset: string;
  amount: BigNumber;
  eventType: string;
  location: string;
  timestamp: number;
  original: UnmatchedAssetMovement;
}

const props = defineProps<{
  movements: UnmatchedAssetMovement[];
}>();

const emit = defineEmits<{
  select: [movement: UnmatchedAssetMovement];
}>();

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<UnmatchedMovementRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    align: 'center',
    key: 'location',
    label: t('common.exchange'),
  },
  {
    key: 'eventType',
    label: t('common.type'),
  },
  {
    align: 'end',
    key: 'amount',
    label: t('common.amount'),
  },
  {
    key: 'asset',
    label: t('common.asset'),
  },
  {
    key: 'actions',
    label: '',
  },
]);

function getEventEntry(row: HistoryEventCollectionRow): HistoryEventEntryWithMeta {
  const events = Array.isArray(row) ? row : [row];
  return events[0];
}

const rows = computed<UnmatchedMovementRow[]>(() =>
  props.movements.map((movement) => {
    const entry = getEventEntry(movement.events).entry;
    return {
      amount: entry.amount,
      asset: entry.asset,
      eventType: entry.eventType,
      groupIdentifier: movement.groupIdentifier,
      location: entry.location,
      original: movement,
      timestamp: entry.timestamp,
    };
  }),
);
</script>

<template>
  <div>
    <p class="text-body-2 text-rui-text-secondary mb-4">
      {{ t('asset_movement_matching.dialog.description') }}
    </p>

    <TableEmptyState
      v-if="rows.length === 0"
      :text="t('asset_movement_matching.dialog.no_unmatched')"
    />

    <RuiDataTable
      v-else
      :cols="columns"
      :rows="rows"
      row-attr="groupIdentifier"
      outlined
      sticky-header
      class="table-inside-dialog"
    >
      <template #item.asset="{ row }">
        <AssetDetails :asset="row.asset" />
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.eventType="{ row }">
        <BadgeDisplay>
          {{ row.eventType }}
        </BadgeDisplay>
      </template>
      <template #item.location="{ row }">
        <LocationDisplay :identifier="row.location" />
      </template>
      <template #item.timestamp="{ row }">
        <DateDisplay
          :timestamp="row.timestamp"
          milliseconds
        />
      </template>
      <template #item.actions="{ row }">
        <RuiButton
          size="sm"
          color="primary"
          @click="emit('select', row.original)"
        >
          {{ t('asset_movement_matching.dialog.find_match') }}
        </RuiButton>
      </template>
    </RuiDataTable>
  </div>
</template>
