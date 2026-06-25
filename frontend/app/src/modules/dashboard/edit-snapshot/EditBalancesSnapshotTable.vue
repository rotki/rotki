<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { BalanceSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, toSentenceCase } from '@rotki/common';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { isNft } from '@/modules/assets/nft-utils';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import EditBalancesSnapshotDeleteDialog from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotDeleteDialog.vue';
import EditBalancesSnapshotEntryDialog from '@/modules/dashboard/edit-snapshot/EditBalancesSnapshotEntryDialog.vue';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import { getTotalValue, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/lib/snapshot-totals';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const modelValue = defineModel<Snapshot>({ required: true });

const { timestamp } = defineProps<{
  timestamp: number;
}>();

const emit = defineEmits<{
  'update:step': [step: number];
}>();

const { t } = useI18n({ useScope: 'global' });

type IndexedBalanceSnapshot = BalanceSnapshot & { index: number; categoryLabel: string };

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const indexToDelete = ref<number | null>(null);
const sort = ref<DataTableSortData<BalanceSnapshot>>({
  column: 'usdValue',
  direction: 'desc',
});
const assetSearch = ref<string>('');
const entryDialog = useTemplateRef<InstanceType<typeof EditBalancesSnapshotEntryDialog>>('entryDialog');

const data = computed<IndexedBalanceSnapshot[]>(() =>
  get(modelValue).balancesSnapshot.map((item: BalanceSnapshot, index: number) => ({
    ...item,
    categoryLabel: isNft(item.assetIdentifier)
      ? `${item.category} (${t('dashboard.snapshot.edit.dialog.balances.nft')})`
      : item.category,
    index,
  })),
);

const filteredData = computed<IndexedBalanceSnapshot[]>(() => {
  const allData = get(data);
  const search = get(assetSearch);
  if (!search)
    return allData;

  return allData.filter(({ assetIdentifier }) => assetIdentifier === search);
});

const total = computed<BigNumber>(() => getTotalValue(get(modelValue).locationDataSnapshot));

const tableHeaders = computed<DataTableColumn<IndexedBalanceSnapshot>[]>(() => [
  {
    cellClass: 'py-2',
    class: 'w-[10rem]',
    key: 'categoryLabel',
    label: t('common.category'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
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
    cellClass: 'py-2',
    class: 'w-[6.25rem]',
    key: 'action',
    label: '',
  },
]);

useRememberTableSorting<BalanceSnapshot>(TableId.EDIT_BALANCE_SNAPSHOT, sort, tableHeaders);

function updateStep(step: number): void {
  emit('update:step', step);
}

const existingLocations = computed<string[]>(() =>
  get(modelValue).locationDataSnapshot.filter(item => item.location !== TOTAL_LOCATION).map(item => item.location),
);

function editClick(item: IndexedBalanceSnapshot): void {
  get(entryDialog)?.openEdit(item);
}

function deleteClick(item: IndexedBalanceSnapshot): void {
  set(indexToDelete, item.index);
}

function add(): void {
  get(entryDialog)?.openAdd();
}
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 p-4 border-b border-default">
      <AssetSelect
        v-model="assetSearch"
        outlined
        hide-details
        clearable
        :label="t('dashboard.snapshot.search_asset')"
      />
    </div>
    <ScrollableDialogContent max-height="calc(100vh - 26.25rem)">
      <RuiDataTable
        v-model:sort="sort"
        :cols="tableHeaders"
        :rows="filteredData"
        row-attr="assetIdentifier"
        dense
      >
        <template #item.categoryLabel="{ row }">
          <span>{{ toSentenceCase(row.categoryLabel) }}</span>
        </template>

        <template #item.assetIdentifier="{ row }">
          <AssetDetails
            v-if="!isNft(row.assetIdentifier)"
            class="[&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
            :asset="row.assetIdentifier"
            :enable-association="false"
          />
          <NftDetails
            v-else
            :identifier="row.assetIdentifier"
          />
        </template>

        <template #item.amount="{ row }">
          <ValueDisplay :value="row.amount" />
        </template>

        <template #item.usdValue="{ row }">
          <SnapshotFiatDisplay
            :value="row.usdValue"
            :timestamp="timestamp"
          />
        </template>

        <template #item.action="{ row }">
          <RowActions
            :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
            :delete-tooltip="t('dashboard.snapshot.edit.dialog.actions.delete_item')"
            @edit-click="editClick(row)"
            @delete-click="deleteClick(row)"
          />
        </template>
      </RuiDataTable>
    </ScrollableDialogContent>
    <div
      class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex items-center justify-between gap-4 p-2"
    >
      <div>
        <div class="text-caption">
          {{ t('common.total') }}:
        </div>
        <div class="font-bold text-h6 -mt-1">
          <SnapshotFiatDisplay
            :value="total"
            :timestamp="timestamp"
          />
        </div>
      </div>

      <div class="flex gap-2">
        <RuiButton
          variant="text"
          color="primary"
          @click="add()"
        >
          <template #prepend>
            <RuiIcon name="lu-circle-plus" />
          </template>
          {{ t('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </RuiButton>
        <RuiButton
          color="primary"
          data-testid="edit-snapshot-next"
          @click="updateStep(2)"
        >
          {{ t('common.actions.next') }}
          <template #append>
            <RuiIcon name="lu-arrow-right" />
          </template>
        </RuiButton>
      </div>
    </div>

    <EditBalancesSnapshotEntryDialog
      ref="entryDialog"
      v-model="modelValue"
      :timestamp="timestamp"
    />

    <EditBalancesSnapshotDeleteDialog
      v-model="modelValue"
      :index="indexToDelete"
      :locations="existingLocations"
      :timestamp="timestamp"
      @close="indexToDelete = null"
    />
  </div>
</template>
