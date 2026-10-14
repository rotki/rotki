<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import SnapshotDeltaDisplay from '@/modules/dashboard/snapshots/components/SnapshotDeltaDisplay.vue';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const sort = defineModel<DataTableSortData<SnapshotListRow>>('sort', {
  default: () => ({ column: 'timestamp', direction: 'desc' as const }),
});

/** Two-way bound so the caller can persist the page across navigation. */
const pagination = defineModel<TablePaginationData | undefined>('pagination', { default: undefined });

const { emptyDescription, exporting, loading = false, rows } = defineProps<{
  rows: SnapshotListRow[];
  loading?: boolean;
  /** Empty-state message; lets the caller distinguish "no snapshots" from "none in range". */
  emptyDescription?: string;
  /** The snapshot being exported, whose download button spins meanwhile. */
  exporting?: number;
}>();

const emit = defineEmits<{
  open: [timestamp: number];
  export: [timestamp: number];
  delete: [timestamp: number];
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * Builds the snapshot table columns.
 *
 * @remarks
 * The value column sorts on the stored USD value, not on what it displays: the fiat value is
 * resolved lazily per visible cell, so it is never available for the full set. Any column added
 * here that renders a lazily resolved value has the same limit.
 */
const cols = computed<DataTableColumn<SnapshotListRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'usdValue',
    label: t('common.value'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'delta',
    label: t('dashboard.snapshot.list.headers.delta'),
  },
  {
    align: 'center',
    cellClass: 'py-2',
    class: 'w-px',
    key: 'actions',
    label: '',
  },
]);
</script>

<template>
  <RuiDataTable
    v-model:sort="sort"
    v-model:pagination="pagination"
    :cols="cols"
    :rows="rows"
    :loading="loading"
    :empty="{ description: emptyDescription ?? t('dashboard.snapshot.list.empty') }"
    row-attr="timestamp"
    outlined
    data-testid="snapshot-list-table"
  >
    <template #item.timestamp="{ row }">
      <span
        data-testid="snapshot-list-row"
        :data-key="row.timestamp"
      >
        <DateDisplay :timestamp="row.timestamp" />
      </span>
    </template>

    <template #item.usdValue="{ row }">
      <SnapshotFiatDisplay
        :value="row.usdValue"
        :timestamp="row.timestamp"
        data-testid="snapshot-list-value"
      />
    </template>

    <template #item.delta="{ row }">
      <SnapshotDeltaDisplay
        :value="row.usdValue"
        :timestamp="row.timestamp"
        :previous-usd-value="row.previousUsdValue"
        :previous-timestamp="row.previousTimestamp"
      />
    </template>

    <template #item.actions="{ row }">
      <div class="flex items-center justify-center gap-1">
        <RuiTooltip
          :open-delay="400"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <RuiButton
              variant="text"
              icon
              data-testid="snapshot-open"
              @click="emit('open', row.timestamp)"
            >
              <RuiIcon
                name="lu-pencil"
                size="16"
              />
            </RuiButton>
          </template>
          {{ t('dashboard.snapshot.list.actions.open') }}
        </RuiTooltip>

        <RuiTooltip
          :open-delay="400"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <RuiButton
              variant="text"
              icon
              :loading="exporting === row.timestamp"
              :disabled="exporting !== undefined && exporting !== row.timestamp"
              data-testid="snapshot-export"
              @click="emit('export', row.timestamp)"
            >
              <RuiIcon
                name="lu-download"
                size="16"
              />
            </RuiButton>
          </template>
          {{ t('dashboard.snapshot.list.actions.export') }}
        </RuiTooltip>

        <RuiTooltip
          :open-delay="400"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <RuiButton
              variant="text"
              icon
              data-testid="snapshot-delete"
              @click="emit('delete', row.timestamp)"
            >
              <RuiIcon
                name="lu-trash-2"
                size="16"
              />
            </RuiButton>
          </template>
          {{ t('dashboard.snapshot.list.actions.delete') }}
        </RuiTooltip>
      </div>
    </template>
  </RuiDataTable>
</template>
