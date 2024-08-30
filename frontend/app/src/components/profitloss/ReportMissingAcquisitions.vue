<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { MissingAcquisition, SelectedReport } from '@/types/reports';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';

type GroupedItems = Record<string, MissingAcquisition[]>;

interface MappedGroupedItems {
  asset: string;
  startDate: number;
  endDate: number;
  totalAmountMissing: BigNumber;
  acquisitions: MissingAcquisition[];
}

const props = defineProps<{
  report: SelectedReport;
  items: MissingAcquisition[];
  isPinned: boolean;
}>();

const { items, isPinned } = toRefs(props);

const { isAssetIgnored, ignoreAsset } = useIgnoredAssetsStore();

const groupedMissingAcquisitions = computed<MappedGroupedItems[]>(() => {
  const grouped: GroupedItems = {};

  get(items).forEach((item: MissingAcquisition) => {
    if (grouped[item.asset])
      grouped[item.asset].push(item);
    else grouped[item.asset] = [item];
  });

  return Object.keys(grouped).map((key) => {
    const sortedAcquisitions = grouped[key].sort((a, b) => a.time - b.time);
    const startDate = sortedAcquisitions[0].time;
    const endDate = sortedAcquisitions.at(-1)?.time;
    assert(endDate, 'end date is missing');

    const totalAmountMissing = bigNumberSum(sortedAcquisitions.map(({ missingAmount }) => missingAmount));

    return {
      asset: key,
      startDate,
      endDate,
      totalAmountMissing,
      acquisitions: sortedAcquisitions,
    };
  });
});

const expanded = ref<MappedGroupedItems[]>([]);

const tableRef = ref<any>(null);

const sort = ref<DataTableSortData<MappedGroupedItems>>([]);
const childSort = ref<DataTableSortData<MissingAcquisition>>({
  column: 'time',
  direction: 'asc' as const,
});

const tableContainer = computed(() => get(tableRef)?.$el);

const { t } = useI18n();

const headers = computed<DataTableColumn<MappedGroupedItems>[]>(() => [
  {
    label: t('common.asset'),
    key: 'asset',
    cellClass: 'py-0',
    sortable: true,
  },
  {
    label: t('common.datetime'),
    key: 'startDate',
    cellClass: 'py-2',
    sortable: true,
  },
  {
    label: t('profit_loss_report.actionable.missing_acquisitions.headers.missing_acquisitions'),
    key: 'total_missing_acquisition',
    align: 'end',
    sortable: true,
  },
  {
    label: t('profit_loss_report.actionable.missing_acquisitions.headers.total_missing'),
    key: 'total_amount_missing',
    align: 'end',
  },
  {
    label: t('profit_loss_report.actionable.missing_acquisitions.headers.quick_action'),
    key: 'action',
    cellClass: 'py-0',
  },
]);

const childHeaders = computed<DataTableColumn<MissingAcquisition>[]>(() => [
  {
    label: t('common.datetime'),
    key: 'time',
    sortable: true,
  },
  {
    label: t('profit_loss_report.actionable.missing_acquisitions.headers.found_amount'),
    key: 'foundAmount',
    align: 'end',
    sortable: true,
  },
  {
    label: t('profit_loss_report.actionable.missing_acquisitions.headers.missing_amount'),
    key: 'missingAmount',
    align: 'end',
    sortable: true,
  },
]);

const isIgnored = (asset: string) => get(isAssetIgnored(asset));
</script>

<template>
  <div>
    <RuiDataTable
      ref="tableRef"
      v-model:sort="sort"
      v-model:expanded="expanded"
      class="table-inside-dialog"
      :class="{
        [$style['table--pinned']]: isPinned,
      }"
      :cols="headers"
      :rows="groupedMissingAcquisitions"
      row-attr="asset"
      single-expand
      :scroller="tableContainer"
      :dense="isPinned"
    >
      <template #item.asset="{ row }">
        <AssetDetails
          :asset="row.asset"
          link
        />
      </template>
      <template #item.startDate="{ row }">
        <DateDisplay :timestamp="row.startDate" />
        <template v-if="row.startDate !== row.endDate">
          <span>
            {{ t('profit_loss_report.actionable.missing_acquisitions.to') }}
            <br />
          </span>
          <DateDisplay :timestamp="row.endDate" />
        </template>
      </template>
      <template #item.total_missing_acquisition="{ row }">
        {{ row.acquisitions.length }}
      </template>
      <template #item.total_amount_missing="{ row }">
        <AmountDisplay
          class="text-rui-error"
          :value="row.totalAmountMissing"
        />
      </template>
      <template #item.action="{ row }">
        <div class="flex items-center gap-1">
          <RuiMenu
            :popper="{ placement: 'bottom-end' }"
            close-on-content-click
          >
            <template #activator="{ attrs }">
              <RuiButton
                variant="text"
                icon
                v-bind="attrs"
              >
                <RuiIcon
                  size="20"
                  name="more-2-fill"
                />
              </RuiButton>
            </template>
            <div class="py-2">
              <RuiButton
                variant="list"
                @click="ignoreAsset(row.asset)"
              >
                <template #prepend>
                  <RuiIcon name="eye-off-line" />
                  {{ t('assets.ignore') }}
                </template>
              </RuiButton>
            </div>
          </RuiMenu>

          <RuiTooltip
            v-if="isIgnored(row.asset)"
            :open-delay="400"
          >
            <template #activator>
              <BadgeDisplay
                color="grey"
                class="py-1"
              >
                <RuiIcon
                  size="18"
                  name="eye-off-line"
                />
              </BadgeDisplay>
            </template>
            {{ t('profit_loss_report.actionable.missing_acquisitions.asset_is_ignored') }}
          </RuiTooltip>
        </div>
      </template>
      <template #expanded-item="{ row }">
        <RuiDataTable
          v-model:sort="childSort"
          :cols="childHeaders"
          :rows="row.acquisitions"
          :scroller="tableContainer"
          outlined
          row-attr="asset"
        >
          <template #item.time="{ row: childItem }">
            <DateDisplay :timestamp="childItem.time" />
          </template>
          <template #item.foundAmount="{ row: childItem }">
            <AmountDisplay
              pnl
              :value="childItem.foundAmount"
            />
          </template>
          <template #item.missingAmount="{ row: childItem }">
            <AmountDisplay
              class="text-rui-error"
              :value="childItem.missingAmount"
            />
          </template>
        </RuiDataTable>
      </template>
    </RuiDataTable>
    <slot name="actions" />
  </div>
</template>

<style module lang="scss">
.table {
  &--pinned {
    max-height: 100%;
    height: calc(100vh - 226px);
  }
}
</style>
