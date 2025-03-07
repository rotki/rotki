<script setup lang="ts">
import type { MissingAcquisition, SelectedReport } from '@/types/reports';
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import { Routes } from '@/router/routes';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { bigNumberSum } from '@/utils/calculation';

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

const emit = defineEmits<{
  pin: [];
}>();

defineSlots<{
  actions: () => any;
}>();

const { isPinned, items } = toRefs(props);

const router = useRouter();
const { ignoreAsset, isAssetIgnored } = useIgnoredAssetsStore();

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
      acquisitions: sortedAcquisitions,
      asset: key,
      endDate,
      startDate,
      totalAmountMissing,
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

const headers = computed<DataTableColumn<MappedGroupedItems>[]>(() => [{
  cellClass: '!py-0 !pr-0 !pl-3',
  class: '!py-0 !pr-0 !pl-3',
  key: 'expand',
  label: '',
  sortable: false,
}, {
  cellClass: 'py-0',
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, ...(get(isPinned)
  ? []
  : [
    {
      cellClass: 'py-2',
      key: 'startDate',
      label: t('common.datetime'),
      sortable: true,
    },
    {
      align: 'end',
      key: 'total_missing_acquisition',
      label: t('profit_loss_report.actionable.missing_acquisitions.headers.missing_acquisitions'),
      sortable: true,
    },
  ] satisfies DataTableColumn<MappedGroupedItems>[]), {
  align: 'end',
  key: 'total_amount_missing',
  label: t('profit_loss_report.actionable.missing_acquisitions.headers.total_missing'),
}, {
  cellClass: 'py-0',
  key: 'action',
  label: t('profit_loss_report.actionable.missing_acquisitions.headers.quick_action'),
}]);

const childHeaders = computed<DataTableColumn<MissingAcquisition>[]>(() => [{
  key: 'time',
  label: t('common.datetime'),
  sortable: true,
}, {
  align: 'end',
  key: 'foundAmount',
  label: t('profit_loss_report.actionable.missing_acquisitions.headers.found_amount'),
  sortable: true,
}, {
  align: 'end',
  key: 'missingAmount',
  label: t('profit_loss_report.actionable.missing_acquisitions.headers.missing_amount'),
  sortable: true,
}, {
  key: 'actions',
  label: t('common.actions_text'),
  sortable: true,
}]);

const isIgnored = (asset: string) => get(isAssetIgnored(asset));

const [CreateDate, ReuseDate] = createReusableTemplate<{ row: MappedGroupedItems }>();

async function showInHistoryEvent(identifier: number) {
  emit('pin');

  await router.push({
    path: Routes.HISTORY_EVENTS.toString(),
    query: {
      identifiers: identifier.toString(),
    },
  });
}
</script>

<template>
  <CreateDate #default="{ row }">
    <DateDisplay :timestamp="row.startDate" />
    <template v-if="row.startDate !== row.endDate">
      <span class="ml-0.5">
        {{ t('profit_loss_report.actionable.missing_acquisitions.to') }}
        <br />
      </span>
      <DateDisplay :timestamp="row.endDate" />
    </template>
  </CreateDate>
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
        <ReuseDate
          v-if="isPinned"
          :row="row"
        />
      </template>
      <template #item.startDate="{ row }">
        <ReuseDate :row="row" />
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
                  name="lu-ellipsis-vertical"
                />
              </RuiButton>
            </template>
            <div class="py-2">
              <RuiButton
                variant="list"
                @click="ignoreAsset(row.asset)"
              >
                <template #prepend>
                  <RuiIcon name="lu-eye-off" />
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
                  name="lu-eye-off"
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
          class="bg-white dark:bg-rui-grey-900"
          :class="{ 'my-2': isPinned }"
          outlined
          hide-default-footer
          hide-default-header
          row-attr="asset"
          single-expand
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
          <template #item.actions="{ row: childItem }">
            <RuiButton
              v-if="childItem.originatingEventId"
              variant="text"
              color="primary"
              @click="showInHistoryEvent(childItem.originatingEventId)"
            >
              {{ t('profit_loss_report.actionable.missing_acquisitions.show_in_history_event') }}
              <template #append>
                <RuiIcon name="lu-chevron-right" />
              </template>
            </RuiButton>
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
    height: calc(100vh - 245px);
  }
}
</style>
