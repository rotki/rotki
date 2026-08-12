<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { BalanceSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import type { Filters } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-filter';
import type { BalanceMutation, LocationAttribution } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { toSentenceCase } from '@rotki/common';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import SnapshotBalanceDeleteDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceDeleteDialog.vue';
import SnapshotBalanceEntryDialog from '@/modules/dashboard/snapshots/components/SnapshotBalanceEntryDialog.vue';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import { useSnapshotBalanceDisplay } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-display';
import {
  type IndexedBalanceSnapshot,
  useSnapshotBalanceRows,
} from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-rows';
import { useSetting } from '@/modules/settings/use-setting';
import RowActions from '@/modules/shell/components/RowActions.vue';

/**
 * Every filter the bar holds, zero-value visibility included. Owned by the page so the summary's
 * zero-value warning can isolate the rows it is complaining about.
 */
const filters = defineModel<Filters>('filters', { default: () => ({}) });

const { locked = false, snapshot, timestamp } = defineProps<{
  snapshot: Snapshot;
  timestamp: number;
  /** Disables every edit action while the snapshot's totals don't reconcile. */
  locked?: boolean;
}>();

const emit = defineEmits<{
  'add': [mutation: BalanceMutation];
  'edit': [payload: { index: number; mutation: BalanceMutation }];
  'delete': [payload: { index: number; location: LocationAttribution }];
  'bulk-delete': [indices: number[]];
}>();

const { t } = useI18n({ useScope: 'global' });
const pillLabels = usePillBarLabels();

const currencySymbol = useSetting('currencySymbol');

const sort = ref<DataTableSortData<BalanceSnapshot>>({
  column: 'usdValue',
  direction: 'desc',
});
const entryDialog = useTemplateRef<InstanceType<typeof SnapshotBalanceEntryDialog>>('entryDialog');
const deleteDialog = useTemplateRef<InstanceType<typeof SnapshotBalanceDeleteDialog>>('deleteDialog');

const {
  categoryChipColor,
  data,
  describeWarning,
  isLiability,
  isNftRow,
  sharePercent,
  total,
  warningsByIndex,
} = useSnapshotBalanceDisplay(() => snapshot);

const { fields, filteredData, hiddenCount, zeroValueCount } = useSnapshotBalanceRows(data, filters);

const emptyDescription = computed<string>(() =>
  get(data).length > 0 && get(filteredData).length === 0
    ? t('dashboard.snapshot.detail.balances.empty_filtered')
    : t('dashboard.snapshot.detail.balances.empty'),
);

const tableHeaders = computed<DataTableColumn<IndexedBalanceSnapshot>[]>(() => [
  {
    cellClass: 'py-2',
    class: 'w-[10rem]',
    key: 'categoryLabel',
    label: t('common.category'),
    sortable: true,
  },
  {
    cellClass: 'py-0 max-w-[20rem]',
    class: 'max-w-[20rem]',
    key: 'assetIdentifier',
    label: t('common.asset'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'usdValue',
    label: t('common.value_in_symbol', { symbol: get(currencySymbol) }),
    sortable: true,
  },
  {
    align: 'end',
    class: 'w-[6rem]',
    key: 'share',
    label: t('dashboard.snapshot.detail.balances.share'),
  },
  {
    cellClass: 'py-2',
    class: 'w-[6.25rem]',
    key: 'action',
    label: '',
  },
]);

useRememberTableSorting<BalanceSnapshot>(TableId.EDIT_BALANCE_SNAPSHOT, sort, tableHeaders);

function add(): void {
  get(entryDialog)?.openAdd();
}

function editClick(item: IndexedBalanceSnapshot): void {
  get(entryDialog)?.openEdit(item);
}

function onSubmit(payload: { index: number | null; mutation: BalanceMutation }): void {
  if (payload.index === null)
    emit('add', payload.mutation);
  else
    emit('edit', { index: payload.index, mutation: payload.mutation });
}

function deleteClick(item: IndexedBalanceSnapshot): void {
  get(deleteDialog)?.open(item.index);
}

/**
 * Sweep away the valueless rows in one step. Only zero-value balances are
 * eligible: removing them never debits a location subtotal (their value is 0),
 * so the sweep stays correct without asking for a per-row location like the
 * single delete does. The page owns the confirmation.
 */
function bulkDeleteZeroValue(): void {
  const indices = get(data).filter(item => item.usdValue.isZero()).map(item => item.index);
  if (indices.length > 0)
    emit('bulk-delete', indices);
}

function onDelete(payload: { index: number; location: LocationAttribution }): void {
  emit('delete', payload);
}
</script>

<template>
  <RuiCard
    no-padding
    data-testid="snapshot-balances-table"
  >
    <template #custom-header>
      <!-- Title and actions on one row, the bar on its own below it: a pill added to the bar must
           not squeeze the actions, and every other migrated table reads the same way. -->
      <div class="border-b border-default">
        <div class="flex flex-wrap items-center justify-between gap-4 p-4">
          <h5 class="text-h6">
            {{ t('dashboard.snapshot.detail.balances.title') }}
          </h5>
          <div class="flex flex-wrap items-center gap-3">
            <RuiChip
              v-if="hiddenCount > 0"
              size="sm"
              class="whitespace-nowrap"
              data-testid="snapshot-balances-hidden-count"
            >
              {{ t('dashboard.snapshot.detail.balances.hidden', { count: hiddenCount }, hiddenCount) }}
            </RuiChip>
            <!-- An action, not a filter: it used to sit inside the filter menu, where a destructive
                 sweep is not what a user opens a filter list expecting to find. -->
            <RuiButton
              v-if="zeroValueCount > 0"
              variant="text"
              color="error"
              size="sm"
              class="whitespace-nowrap"
              :disabled="locked"
              data-testid="snapshot-balances-bulk-delete"
              @click="bulkDeleteZeroValue()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-trash-2"
                  size="18"
                />
              </template>
              {{ t('dashboard.snapshot.detail.balances.bulk_delete.action', { count: zeroValueCount }, zeroValueCount) }}
            </RuiButton>
            <RuiButton
              color="primary"
              size="sm"
              class="!py-2"
              :disabled="locked"
              data-testid="snapshot-balances-add"
              @click="add()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-circle-plus"
                  size="18"
                />
              </template>
              {{ t('dashboard.snapshot.detail.balances.add') }}
            </RuiButton>
          </div>
        </div>
        <!-- The bar's own root is the bordered input box, so the spacing around it goes on a
             wrapper: passed to the component it would land inside the border and grow it. -->
        <div class="px-4 pb-4">
          <PillFilterBar
            v-model:matches="filters"
            :fields="fields"
            :labels="pillLabels"
          />
        </div>
      </div>
    </template>

    <RuiAlert
      v-if="locked"
      type="warning"
      class="mx-4 mt-4"
      data-testid="snapshot-balances-locked"
    >
      {{ t('dashboard.snapshot.detail.balances.locked') }}
    </RuiAlert>

    <RuiDataTable
      v-model:sort="sort"
      :cols="tableHeaders"
      :rows="filteredData"
      :empty="{ description: emptyDescription }"
      row-attr="assetIdentifier"
      dense
    >
      <template #item.categoryLabel="{ row }">
        <RuiChip
          size="sm"
          :color="categoryChipColor(row)"
        >
          {{ toSentenceCase(row.categoryLabel) }}
        </RuiChip>
      </template>

      <template #item.assetIdentifier="{ row }">
        <div class="flex items-center gap-2 min-w-0">
          <RuiTooltip
            v-if="warningsByIndex.has(row.index)"
            :open-delay="200"
          >
            <template #activator>
              <RuiIcon
                name="lu-triangle-alert"
                size="18"
                class="text-rui-warning shrink-0"
                data-testid="snapshot-balances-flag"
              />
            </template>
            <ul class="list-disc pl-4">
              <li
                v-for="warning in warningsByIndex.get(row.index)"
                :key="warning.code"
              >
                {{ describeWarning(warning) }}
              </li>
            </ul>
          </RuiTooltip>
          <AssetDetails
            v-if="!isNftRow(row)"
            class="min-w-0 [&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
            :asset="row.assetIdentifier"
            :enable-association="false"
            hide-menu
          />
          <NftDetails
            v-else
            class="min-w-0"
            :identifier="row.assetIdentifier"
          />
        </div>
      </template>

      <template #item.amount="{ row }">
        <ValueDisplay :value="row.amount" />
      </template>

      <template #item.usdValue="{ row }">
        <SnapshotFiatDisplay
          :value="row.usdValue"
          :timestamp="timestamp"
          :class="{ 'text-rui-error': isLiability(row) }"
        />
      </template>

      <template #item.share="{ row }">
        <span
          v-if="sharePercent(row)"
          class="text-body-2"
          :class="isLiability(row) ? 'text-rui-error' : 'text-rui-text-secondary'"
        >
          {{ t('dashboard.snapshot.detail.balances.share_percent', { percent: sharePercent(row) }) }}
        </span>
      </template>

      <template #item.action="{ row }">
        <RowActions
          :disabled="locked"
          :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
          :delete-tooltip="t('dashboard.snapshot.edit.dialog.actions.delete_item')"
          @edit-click="editClick(row)"
          @delete-click="deleteClick(row)"
        />
      </template>

      <template #tfoot>
        <tr>
          <td
            colspan="3"
            class="font-medium p-4"
          >
            {{ t('common.total') }}
          </td>
          <td class="text-right font-bold p-4">
            <SnapshotFiatDisplay
              :value="total"
              :timestamp="timestamp"
            />
          </td>
          <td />
          <td />
        </tr>
      </template>
    </RuiDataTable>

    <SnapshotBalanceEntryDialog
      ref="entryDialog"
      :snapshot="snapshot"
      :timestamp="timestamp"
      @submit="onSubmit($event)"
    />

    <SnapshotBalanceDeleteDialog
      ref="deleteDialog"
      :snapshot="snapshot"
      :timestamp="timestamp"
      @confirm="onDelete($event)"
    />
  </RuiCard>
</template>
